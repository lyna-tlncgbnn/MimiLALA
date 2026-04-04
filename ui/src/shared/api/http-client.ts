import { API_BASE_URL } from "@/app/config/env";

export async function requestJson<T>(
  path: string,
  init: RequestInit,
  parse: (value: unknown) => T,
) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(init.headers ?? {}),
    },
    ...init,
  });

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

  if (response.status === 204) {
    return parse(undefined);
  }

  return parse(await response.json());
}
