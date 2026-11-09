const RAW_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

/** Base URL of the backend, without a trailing slash. Configure with VITE_API_BASE_URL. */
export const API_BASE_URL = RAW_BASE.replace(/\/+$/, "");

export type ApiErrorKind = "network" | "timeout" | "http" | "invalid";

export class ApiError extends Error {
  readonly kind: ApiErrorKind;
  readonly status?: number;

  constructor(kind: ApiErrorKind, message: string, status?: number) {
    super(message);
    this.name = "ApiError";
    this.kind = kind;
    this.status = status;
  }
}

/** FastAPI sends { detail: string } or, for validation errors, { detail: [{ msg, loc }] }. */
function readDetail(body: unknown): string | null {
  if (!body || typeof body !== "object" || !("detail" in body)) return null;
  const detail = (body as { detail: unknown }).detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const msgs = detail
      .map((d) => (d && typeof d === "object" && "msg" in d ? String((d as { msg: unknown }).msg) : null))
      .filter((m): m is string => Boolean(m));
    if (msgs.length) return msgs.join("; ");
  }
  return null;
}

interface RequestOptions {
  method?: "GET" | "POST" | "DELETE" | "PATCH";
  body?: unknown;
  query?: Record<string, string | number>;
  /** Abort after this many ms. Model calls can be slow, so callers choose their own limit. */
  timeoutMs?: number;
  signal?: AbortSignal;
}

export async function request<T>(
  path: string,
  { method = "GET", body, query, timeoutMs = 20_000, signal }: RequestOptions = {},
): Promise<T> {
  const url = new URL(API_BASE_URL + path, window.location.origin);
  if (query) for (const [k, v] of Object.entries(query)) url.searchParams.set(k, String(v));

  const controller = new AbortController();
  let timedOut = false;
  const timer = window.setTimeout(() => {
    timedOut = true;
    controller.abort();
  }, timeoutMs);
  signal?.addEventListener("abort", () => controller.abort(), { once: true });

  try {
    const res = await fetch(url, {
      method,
      headers: body === undefined ? { Accept: "application/json" } : { Accept: "application/json", "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: controller.signal,
    });

    let payload: unknown = null;
    const text = await res.text();
    if (text) {
      try {
        payload = JSON.parse(text);
      } catch {
        if (res.ok) throw new ApiError("invalid", "The server sent a response the app could not read.");
      }
    }

    if (!res.ok) {
      const detail = readDetail(payload);
      const fallback =
        res.status === 404 ? "That item was not found." :
        res.status >= 500 ? "The server ran into a problem. Try again in a moment." :
        "The request was not accepted.";
      throw new ApiError("http", detail ?? fallback, res.status);
    }
    return payload as T;
  } catch (err) {
    if (err instanceof ApiError) throw err;
    if (err instanceof DOMException && err.name === "AbortError") {
      if (timedOut) throw new ApiError("timeout", "The server took too long to respond. The model may still be working; check again shortly.");
      throw err; // caller cancelled on purpose
    }
    throw new ApiError("network", `Can't reach the SkillPilot backend at ${API_BASE_URL}. Check that it is running and that the address is correct.`);
  } finally {
    window.clearTimeout(timer);
  }
}

export function errorMessage(err: unknown): string {
  if (err instanceof ApiError) return err.message;
  return "Something went wrong. Try again.";
}

export function isAbort(err: unknown): boolean {
  return err instanceof DOMException && err.name === "AbortError";
}
