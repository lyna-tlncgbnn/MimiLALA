from __future__ import annotations

import shutil
import threading
import time
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

from agentbot.browser.runtime.events import DownloadCompletedEvent, DownloadProgressEvent, DownloadStartedEvent
from agentbot.browser.runtime.watchdog_base import BrowserRuntimeWatchdog

DownloadCallback = Callable[[dict[str, Any]], None]


class DownloadsWatchdog(BrowserRuntimeWatchdog):
    def __init__(self, runtime) -> None:
        super().__init__(runtime)
        self._start_callbacks: list[DownloadCallback] = []
        self._progress_callbacks: list[DownloadCallback] = []
        self._complete_callbacks: list[DownloadCallback] = []
        self._monitor_threads: dict[str, threading.Thread] = {}

    def register(self) -> None:
        self.event_bus.register(DownloadStartedEvent, self._on_download_started)
        self.event_bus.register(DownloadCompletedEvent, self._on_download_completed)

    def register_download_callbacks(
        self,
        *,
        on_start: DownloadCallback | None = None,
        on_progress: DownloadCallback | None = None,
        on_complete: DownloadCallback | None = None,
    ) -> None:
        if on_start is not None:
            self._start_callbacks.append(on_start)
        if on_progress is not None:
            self._progress_callbacks.append(on_progress)
        if on_complete is not None:
            self._complete_callbacks.append(on_complete)

    def unregister_download_callbacks(
        self,
        *,
        on_start: DownloadCallback | None = None,
        on_progress: DownloadCallback | None = None,
        on_complete: DownloadCallback | None = None,
    ) -> None:
        if on_start in self._start_callbacks:
            self._start_callbacks.remove(on_start)
        if on_progress in self._progress_callbacks:
            self._progress_callbacks.remove(on_progress)
        if on_complete in self._complete_callbacks:
            self._complete_callbacks.remove(on_complete)

    def prepare_download_event(self, *, download, page=None) -> DownloadStartedEvent:
        suggested_filename = download.suggested_filename or "download"
        source_url = ""
        try:
            source_url = download.url or ""
        except Exception:
            source_url = ""
        return DownloadStartedEvent(
            created_at=time.time(),
            download_id=f"download_{uuid4().hex}",
            suggested_filename=suggested_filename,
            source_url=source_url,
            download=download,
            page=page,
            metadata={},
        )

    def _on_download_started(self, event: DownloadStartedEvent) -> None:
        from agentbot.browser.session import record_runtime_event

        existing_files = {
            path.name
            for path in self.runtime.downloads_dir.iterdir()
            if path.is_file() and not path.name.startswith(".")
        }
        info = {
            "guid": event.download_id,
            "url": event.source_url,
            "suggested_filename": event.suggested_filename,
            "auto_download": False,
        }
        self.runtime.active_downloads[event.download_id] = {
            "state": "started",
            "suggested_filename": event.suggested_filename,
            "url": event.source_url,
            "started_at": str(event.created_at),
            "download": event.download,
            "existing_files": sorted(existing_files),
        }
        self.runtime.latest_download_id = event.download_id
        record_runtime_event(
            self.runtime,
            "download_started",
            f"Download started: {event.suggested_filename}",
            dedupe_recent=True,
        )
        self._ensure_download_monitor(event.download_id)
        for callback in list(self._start_callbacks):
            callback(info)

    def finalize_download(self, download_id: str) -> dict[str, Any]:
        from agentbot.browser.session import record_runtime_event

        active = self.runtime.active_downloads.get(download_id)
        if not active:
            raise ValueError(f"Download {download_id} is not active.")

        if str(active.get("state") or "") == "completed":
            return {
                "guid": download_id,
                "path": str(active.get("path") or ""),
                "file_name": str(active.get("suggested_filename") or ""),
                "file_size": int(active.get("file_size") or 0),
                "file_type": Path(str(active.get("path") or "")).suffix.lstrip(".") or None,
                "mime_type": None,
                "auto_download": False,
            }

        if str(active.get("state") or "") == "error":
            raise RuntimeError(str(active.get("error") or "Download handling failed."))

        download = active.get("download")
        if download is None:
            raise RuntimeError("Download object is not available for persistence.")

        suggested_filename = str(active.get("suggested_filename") or "download")
        source_url = str(active.get("url") or "")
        received_bytes = 0
        try:
            try:
                native_path_value = download.path()
            except Exception:
                native_path_value = None

            if native_path_value:
                native_path = Path(native_path_value)
                if native_path.exists():
                    return self._complete_download_from_path(
                        download_id=download_id,
                        suggested_filename=suggested_filename,
                        source_path=native_path,
                    )

            destination = self._unique_download_destination(suggested_filename)
            download.save_as(str(destination))
            return self._emit_completed_download(
                download_id=download_id,
                suggested_filename=suggested_filename,
                destination=destination,
            )
        except Exception as exc:
            self.runtime.active_downloads[download_id] = {
                "state": "error",
                "suggested_filename": suggested_filename,
                "url": source_url,
                "error": str(exc),
            }
            record_runtime_event(
                self.runtime,
                "download_error",
                f"Download handling failed: {exc}",
                dedupe_recent=True,
            )
            raise

    def reconcile_active_downloads(self) -> list[dict[str, Any]]:
        completed: list[dict[str, Any]] = []
        for download_id, active in list(self.runtime.active_downloads.items()):
            if str(active.get("state") or "") != "started":
                continue
            suggested_filename = str(active.get("suggested_filename") or "download")
            candidate = self._find_native_download_candidate(active, suggested_filename)
            if candidate is None:
                continue
            completed.append(
                self._complete_download_from_path(
                    download_id=download_id,
                    suggested_filename=suggested_filename,
                    source_path=candidate,
                )
            )
        return completed

    def _on_download_completed(self, event: DownloadCompletedEvent) -> None:
        from agentbot.browser.session import record_runtime_event

        destination_str = str(event.destination)
        if destination_str not in self.runtime.downloaded_files:
            self.runtime.downloaded_files.append(destination_str)
        self.runtime.active_downloads[event.download_id] = {
            "state": "completed",
            "suggested_filename": event.suggested_filename,
            "path": destination_str,
            "file_size": int(event.metadata.get("file_size") or 0),
        }
        info = {
            "guid": event.download_id,
            "path": destination_str,
            "file_name": event.destination.name,
            "file_size": int(event.metadata.get("file_size") or 0),
            "file_type": event.destination.suffix.lstrip(".") or None,
            "mime_type": None,
            "auto_download": False,
        }
        record_runtime_event(
            self.runtime,
            "download",
            f"Downloaded file: {event.destination.name} -> {destination_str}",
            dedupe_recent=True,
        )
        for callback in list(self._complete_callbacks):
            callback(info)

    def _complete_download_from_path(
        self,
        *,
        download_id: str,
        suggested_filename: str,
        source_path: Path,
    ) -> dict[str, Any]:
        destination = self._unique_download_destination(suggested_filename)
        try:
            if source_path.resolve() != destination.resolve():
                shutil.move(str(source_path), str(destination))
            else:
                destination = source_path
        except Exception as exc:
            if source_path.name != suggested_filename:
                raise RuntimeError(
                    f"Native download file {source_path.name} is not ready to be renamed to {suggested_filename}: {exc}"
                ) from exc
            destination = source_path
        return self._emit_completed_download(
            download_id=download_id,
            suggested_filename=suggested_filename,
            destination=destination,
        )

    def _emit_completed_download(
        self,
        *,
        download_id: str,
        suggested_filename: str,
        destination: Path,
    ) -> dict[str, Any]:
        try:
            received_bytes = destination.stat().st_size
        except OSError:
            received_bytes = 0

        progress_info = {
            "guid": download_id,
            "received_bytes": received_bytes,
            "total_bytes": received_bytes,
            "state": "completed",
        }
        for callback in list(self._progress_callbacks):
            callback(progress_info)

        self.event_bus.emit(
            DownloadProgressEvent(
                created_at=time.time(),
                download_id=download_id,
                suggested_filename=suggested_filename,
                received_bytes=received_bytes,
                total_bytes=received_bytes,
                state="completed",
                metadata={},
            )
        )
        self.event_bus.emit(
            DownloadCompletedEvent(
                created_at=time.time(),
                download_id=download_id,
                suggested_filename=suggested_filename,
                destination=destination,
                metadata={"file_size": received_bytes},
            )
        )
        return {
            "guid": download_id,
            "path": str(destination),
            "file_name": destination.name,
            "file_size": received_bytes,
            "file_type": destination.suffix.lstrip(".") or None,
            "mime_type": None,
            "auto_download": False,
        }

    def _find_native_download_candidate(self, active: dict[str, Any], suggested_filename: str) -> Path | None:
        existing_files = {str(name) for name in active.get("existing_files", [])}
        candidates = [
            path
            for path in self.runtime.downloads_dir.iterdir()
            if path.is_file() and not path.name.startswith(".") and path.name not in existing_files
        ]
        if not candidates:
            return None
        exact_match = next((path for path in candidates if path.name == suggested_filename), None)
        if exact_match is not None:
            return exact_match
        if len(candidates) == 1:
            return candidates[0]
        candidates.sort(key=lambda item: item.stat().st_mtime, reverse=True)
        return candidates[0]

    def _ensure_download_monitor(self, download_id: str) -> None:
        existing = self._monitor_threads.get(download_id)
        if existing is not None and existing.is_alive():
            return
        thread = threading.Thread(
            target=self._monitor_download_completion,
            args=(download_id,),
            name=f"agentbot-download-monitor-{download_id[-8:]}",
            daemon=True,
        )
        self._monitor_threads[download_id] = thread
        thread.start()

    def _monitor_download_completion(self, download_id: str) -> None:
        deadline = time.time() + max(float(self.runtime.download_complete_timeout_seconds or 30.0), 5.0)
        while time.time() < deadline:
            active = self.runtime.active_downloads.get(download_id)
            if not active:
                return
            state = str(active.get("state") or "")
            if state in {"completed", "error"}:
                return
            suggested_filename = str(active.get("suggested_filename") or "download")
            candidate = self._find_native_download_candidate(active, suggested_filename)
            if candidate is not None:
                try:
                    self._complete_download_from_path(
                        download_id=download_id,
                        suggested_filename=suggested_filename,
                        source_path=candidate,
                    )
                    return
                except Exception:
                    pass
            time.sleep(1.0)

    def _unique_download_destination(self, filename: str) -> Path:
        target = self.runtime.downloads_dir / filename
        if not target.exists():
            return target
        stem = target.stem
        suffix = target.suffix
        counter = 1
        while True:
            candidate = self.runtime.downloads_dir / f"{stem} ({counter}){suffix}"
            if not candidate.exists():
                return candidate
            counter += 1
