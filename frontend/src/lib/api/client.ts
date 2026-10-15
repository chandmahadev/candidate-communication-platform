export const API_BASE_URL = (
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000"
).replace(/\/+$/, "");

export type FieldErrors = Record<string, string[]>;

export class ApiError extends Error {
  /** HTTP status code, or 0 when the server could not be reached. */
  readonly status: number;
  /** Machine-readable error code from the backend (e.g. "permanent_failure"). */
  readonly code?: string;
  readonly fieldErrors: FieldErrors;
  readonly data: unknown;

  constructor(
    message: string,
    options: { status: number; code?: string; fieldErrors?: FieldErrors; data?: unknown },
  ) {
    super(message);
    this.name = "ApiError";
    this.status = options.status;
    this.code = options.code;
    this.fieldErrors = options.fieldErrors ?? {};
    this.data = options.data;
  }

  get isNetworkError(): boolean {
    return this.status === 0;
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function toMessages(value: unknown): string[] {
  if (typeof value === "string") return [value];
  if (Array.isArray(value)) return value.flatMap(toMessages);
  if (isRecord(value)) return Object.values(value).flatMap(toMessages);
  return [];
}

function humanizeField(field: string): string {
  const label = field.replace(/_/g, " ");
  return label.charAt(0).toUpperCase() + label.slice(1);
}

function fallbackMessage(status: number): string {
  if (status === 404) return "The requested resource was not found.";
  if (status >= 500) return "The server encountered an error. Please try again.";
  return `Request failed with status ${status}.`;
}

/** Converts a DRF error payload ({detail, code} or field errors) into an ApiError. */
function buildApiError(status: number, data: unknown): ApiError {
  if (isRecord(data) && typeof data.detail === "string") {
    return new ApiError(data.detail, {
      status,
      code: typeof data.code === "string" ? data.code : undefined,
      data,
    });
  }

  if (isRecord(data)) {
    const fieldErrors: FieldErrors = {};
    for (const [field, value] of Object.entries(data)) {
      const messages = toMessages(value);
      if (messages.length) fieldErrors[field] = messages;
    }
    const entries = Object.entries(fieldErrors);
    if (entries.length) {
      const message = entries
        .map(([field, messages]) =>
          field === "non_field_errors" ? messages.join(" ") : `${humanizeField(field)}: ${messages.join(" ")}`,
        )
        .join(" ");
      return new ApiError(message, { status, fieldErrors, data });
    }
  }

  return new ApiError(fallbackMessage(status), { status, data });
}

export function toApiError(error: unknown): ApiError {
  if (error instanceof ApiError) return error;
  if (error instanceof Error) return new ApiError(error.message, { status: 0 });
  return new ApiError("Something went wrong.", { status: 0 });
}

export function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === "AbortError";
}

type QueryValue = string | number | undefined | null;

export interface RequestOptions {
  method?: "GET" | "POST" | "DELETE";
  body?: unknown;
  query?: Record<string, QueryValue>;
  signal?: AbortSignal;
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const url = new URL(`${API_BASE_URL}${path}`);
  for (const [key, value] of Object.entries(options.query ?? {})) {
    if (value !== undefined && value !== null && value !== "") {
      url.searchParams.set(key, String(value));
    }
  }

  let response: Response;
  try {
    response = await fetch(url, {
      method: options.method ?? "GET",
      headers: {
        Accept: "application/json",
        ...(options.body !== undefined ? { "Content-Type": "application/json" } : {}),
      },
      body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
      signal: options.signal,
      cache: "no-store",
    });
  } catch (error) {
    if (isAbortError(error)) throw error;
    throw new ApiError(
      `Unable to reach the server at ${API_BASE_URL}. Check that the backend is running and try again.`,
      { status: 0 },
    );
  }

  const text = await response.text();
  let data: unknown = null;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = text;
    }
  }

  if (!response.ok) throw buildApiError(response.status, data);
  return data as T;
}
