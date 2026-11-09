export class ApiClientError extends Error {
  constructor(
    message: string,
    readonly code: string,
    readonly requestId: string | null,
    readonly status: number,
  ) {
    super(message);
    this.name = "ApiClientError";
  }
}

type ErrorEnvelope = {
  error?: { code?: string; message?: string; request_id?: string };
};

function requestId(): string {
  return globalThis.crypto?.randomUUID?.() ?? `web-${Date.now()}`;
}

export async function getApi<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`/api/v1${path}`, {
    ...init,
    headers: { Accept: "application/json", "X-Request-ID": requestId(), ...init.headers },
  });
  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as ErrorEnvelope;
    throw new ApiClientError(
      body.error?.message ?? "No fue posible obtener los datos solicitados.",
      body.error?.code ?? "request_failed",
      body.error?.request_id ?? response.headers.get("X-Request-ID"),
      response.status,
    );
  }
  if (response.status === 204 || !response.headers.get("content-type")) return undefined as T;
  return response.json() as Promise<T>;
}

export async function postApi<T>(path: string, body?: unknown, csrfToken?: string): Promise<T> {
  return getApi<T>(path, {
    method: "POST",
    credentials: "same-origin",
    headers: { "Content-Type": "application/json", "Idempotency-Key": requestId(), ...(csrfToken ? { "X-CSRF-Token": csrfToken } : {}) },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}
