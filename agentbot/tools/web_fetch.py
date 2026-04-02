"""Web page fetching tools for direct URL reading."""

from __future__ import annotations

import json
import re
from html import unescape
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from langchain_core.tools import tool

from agentbot.tools.common import truncate_content

MAX_FETCH_CHARS = 16000
DEFAULT_TIMEOUT_SECONDS = 12.0
USER_AGENT = "AgentBot/0.1 (+https://local.app)"


def _validate_url(url: str) -> str:
    normalized_url = url.strip()
    if not normalized_url:
        raise ValueError("url must not be empty.")

    parsed = urlparse(normalized_url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("url must start with http:// or https://.")
    if not parsed.netloc:
        raise ValueError("url must include a valid host.")
    return normalized_url


def _strip_html(html: str) -> str:
    without_scripts = re.sub(
        r"<(script|style)\b[^>]*>.*?</\1>",
        " ",
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    without_tags = re.sub(r"<[^>]+>", " ", without_scripts)
    normalized = re.sub(r"\s+", " ", unescape(without_tags)).strip()
    return normalized


@tool
def fetch_url(url: str, timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS) -> str:
    """Fetch a public HTTP or HTTPS URL and extract readable text content."""
    normalized_url = _validate_url(url)
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be greater than 0.")

    request = Request(
        normalized_url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/json,text/plain;q=0.9,*/*;q=0.8",
        },
        method="GET",
    )

    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            response_body = response.read()
            content_type = response.headers.get("Content-Type", "")
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore").strip()
        raise RuntimeError(
            f"URL fetch failed with HTTP {exc.code}" + (f": {detail}" if detail else "")
        ) from exc
    except URLError as exc:
        raise RuntimeError(f"URL fetch failed: {exc.reason}") from exc

    decoded = response_body.decode("utf-8", errors="ignore")
    lowered_content_type = content_type.lower()
    if "application/json" in lowered_content_type:
        try:
            pretty_json = json.dumps(json.loads(decoded), ensure_ascii=False, indent=2)
        except json.JSONDecodeError:
            pretty_json = decoded
        body_text = pretty_json
    elif "text/html" in lowered_content_type or "<html" in decoded.lower():
        body_text = _strip_html(decoded)
    else:
        body_text = decoded.strip()

    return truncate_content(
        "\n".join(
            [
                f"URL: {normalized_url}",
                f"Content-Type: {content_type or 'unknown'}",
                "",
                body_text,
            ]
        ),
        max_chars=MAX_FETCH_CHARS,
    )


TOOLS = [fetch_url]
