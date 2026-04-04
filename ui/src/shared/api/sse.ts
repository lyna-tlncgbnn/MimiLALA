import { API_BASE_URL } from "@/app/config/env";

export async function streamJsonEvents<TEvent>(
  path: string,
  init: RequestInit,
  parseEvent: (rawEvent: string) => TEvent | null,
  onEvent: (event: TEvent) => void | Promise<void>,
) {
  const response = await fetch(`${API_BASE_URL}${path}`, init);

  if (!response.ok) {
    let message = `Request failed with status ${response.status}`;
    try {
      const body = await response.json();
      if (body?.detail) {
        message = String(body.detail);
      }
    } catch {
      // ignore non-json errors
    }
    throw new Error(message);
  }

  if (!response.body) {
    throw new Error("Streaming response body was empty.");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    buffer += decoder.decode(value ?? new Uint8Array(), { stream: !done });

    let boundaryIndex = buffer.indexOf("\n\n");
    while (boundaryIndex !== -1) {
      const rawEvent = buffer.slice(0, boundaryIndex);
      buffer = buffer.slice(boundaryIndex + 2);

      const parsedEvent = parseEvent(rawEvent);
      if (parsedEvent) {
        await onEvent(parsedEvent);
      }

      boundaryIndex = buffer.indexOf("\n\n");
    }

    if (done) {
      break;
    }
  }

  if (buffer.trim()) {
    const parsedEvent = parseEvent(buffer);
    if (parsedEvent) {
      await onEvent(parsedEvent);
    }
  }
}
