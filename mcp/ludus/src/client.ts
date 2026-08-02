import { Agent, fetch as undiciFetch, FormData } from "undici";
import { readFile } from "node:fs/promises";
import { basename } from "node:path";

/**
 * Scoped undici Agent that skips TLS certificate verification.
 * Used for self-signed certs on Ludus servers.
 */
export const tlsAgent = new Agent({
  connect: { rejectUnauthorized: false },
});

/**
 * Wrapper around undici.fetch that uses our TLS-skipping agent.
 */
export function secureFetch(
  url: string | URL,
  init?: Parameters<typeof undiciFetch>[1],
): ReturnType<typeof undiciFetch> {
  return undiciFetch(url, {
    ...init,
    dispatcher: tlsAgent,
  });
}

const PATH_PARAM_RE = /\{([A-Za-z0-9_-]+)\}/g;

export interface ApiRequest {
  method: string;
  path: string;
  pathParams?: Record<string, string>;
  queryParams?: Record<string, string>;
  body?: unknown;
  contentType?: string;
  /**
   * Names of multipart body fields whose string values should be treated
   * as local file paths to read and attach. If omitted when contentType
   * is "multipart/form-data", the legacy behavior (only the literal key
   * "file" is treated as a path) is preserved for backwards compatibility
   * with direct client callers.
   */
  fileFields?: string[];
}

export interface ApiResponse {
  statusCode: number;
  body: string;
  json: unknown | null;
  success: boolean;
  /**
   * Set when the response Content-Type indicates a non-text payload
   * (zip, octet-stream, images, audio, video, pdf, etc.). The raw bytes
   * are not returned through `body` because UTF-8-decoding binary data
   * produces garbage — callers should fetch the endpoint directly with
   * an HTTP client if they need the bytes, or extend the client to
   * stream to disk.
   */
  binary?: {
    contentType: string;
    size: number;
  };
}

export class LudusClient {
  readonly baseUrl: string;
  readonly apiBasePath: string;
  private readonly apiKey: string;

  constructor(baseUrl: string, apiKey: string, apiBasePath = "/api/v2") {
    this.baseUrl = baseUrl.replace(/\/+$/, "");
    this.apiBasePath = apiBasePath.replace(/\/+$/, "");
    this.apiKey = apiKey;
  }

  async do(req: ApiRequest): Promise<ApiResponse> {
    if (!this.apiKey.trim()) {
      throw new Error("Missing API key");
    }

    const filledPath = fillPathParams(req.path, req.pathParams);
    const endpoint = this.buildUrl(filledPath, req.queryParams);

    const ct = req.contentType?.trim() || "application/json";
    const isMultipart = ct === "multipart/form-data";

    let fetchBody: string | FormData | undefined;
    const headers: Record<string, string> = {
      "X-API-KEY": this.apiKey,
      Accept: "application/json",
    };

    if (isMultipart) {
      const fileFields = new Set(req.fileFields ?? ["file"]);
      fetchBody = await buildFormData(
        req.body as Record<string, unknown>,
        fileFields,
      );
      // Don't set Content-Type — fetch sets it with the boundary
    } else {
      const { bodyContent, resolvedContentType } = marshalBody(
        req.body,
        req.contentType,
      );
      fetchBody = bodyContent;
      if (resolvedContentType) {
        headers["Content-Type"] = resolvedContentType;
      }
    }

    const resp = await secureFetch(endpoint, {
      method: req.method.toUpperCase(),
      headers,
      body: fetchBody,
    });

    const respContentType = resp.headers.get("content-type") ?? "";
    const statusCode = resp.status;

    if (isBinaryContentType(respContentType)) {
      const bytes = await resp.arrayBuffer();
      return {
        statusCode,
        body: "",
        json: null,
        success: statusCode >= 200 && statusCode < 300,
        binary: {
          contentType: respContentType,
          size: bytes.byteLength,
        },
      };
    }

    const rawBody = await resp.text();
    const json = parseMaybeJSON(rawBody);

    return {
      statusCode,
      body: rawBody,
      json,
      success: statusCode >= 200 && statusCode < 300,
    };
  }

  private buildUrl(
    path: string,
    queryParams?: Record<string, string>,
  ): string {
    const fullPath = this.apiBasePath + (path.startsWith("/") ? path : `/${path}`);
    const url = new URL(fullPath, this.baseUrl);

    if (queryParams) {
      for (const [key, value] of Object.entries(queryParams)) {
        const k = key.trim();
        if (k) {
          url.searchParams.set(k, value);
        }
      }
    }

    return url.toString();
  }
}

function fillPathParams(
  path: string,
  params?: Record<string, string>,
): string {
  path = normalizePath(path);

  const missing: string[] = [];

  const result = path.replace(PATH_PARAM_RE, (_match, name: string) => {
    const value = params?.[name];
    if (value === undefined) {
      missing.push(name);
      return `{${name}}`;
    }
    return encodeURIComponent(value);
  });

  if (missing.length > 0) {
    throw new Error(
      `Missing required path parameters: ${missing.join(", ")}`,
    );
  }

  return result;
}

function marshalBody(
  body: unknown,
  contentType?: string,
): { bodyContent: string | undefined; resolvedContentType: string } {
  if (body === undefined || body === null) {
    return { bodyContent: undefined, resolvedContentType: "" };
  }

  const ct = contentType?.trim() || "application/json";

  switch (ct) {
    case "application/json":
      return {
        bodyContent: JSON.stringify(body),
        resolvedContentType: ct,
      };
    case "text/plain":
      if (typeof body !== "string") {
        throw new Error("text/plain body must be a string");
      }
      return { bodyContent: body, resolvedContentType: ct };
    default:
      throw new Error(`Unsupported content type: ${ct}`);
  }
}

function parseMaybeJSON(raw: string): unknown | null {
  const trimmed = raw.trim();
  if (!trimmed) return null;
  try {
    return JSON.parse(trimmed);
  } catch {
    return null;
  }
}

/**
 * Decide whether a response Content-Type should be treated as binary.
 * Conservative — anything starting with `text/`, or one of the JSON /
 * YAML / form / urlencoded families is treated as text. Everything else
 * (application/zip, application/octet-stream, image/*, audio/*, etc.)
 * is binary.
 */
function isBinaryContentType(contentType: string): boolean {
  const ct = contentType.split(";")[0].trim().toLowerCase();
  if (!ct) return false;
  if (ct.startsWith("text/")) return false;
  if (ct === "application/json" || ct.endsWith("+json")) return false;
  if (ct === "application/yaml" || ct === "application/x-yaml") return false;
  if (ct === "application/xml" || ct.endsWith("+xml")) return false;
  if (ct === "application/x-www-form-urlencoded") return false;
  if (ct === "application/javascript" || ct === "application/ecmascript") {
    return false;
  }
  return true;
}

/**
 * Build a FormData object from a body map. Fields whose key is in
 * `fileFields` and whose value is a string are treated as local file
 * paths — the file is read from disk and attached as a Blob. All other
 * fields are appended as stringified form values.
 */
async function buildFormData(
  body: Record<string, unknown> | undefined,
  fileFields: Set<string>,
): Promise<FormData> {
  const form = new FormData();
  if (!body) return form;

  for (const [key, value] of Object.entries(body)) {
    if (fileFields.has(key) && typeof value === "string") {
      const fileBuffer = await readFile(value);
      const blob = new Blob([fileBuffer]);
      form.append(key, blob, basename(value));
    } else {
      form.append(key, String(value));
    }
  }

  return form;
}

function normalizePath(path: string): string {
  path = path.trim();
  if (!path) return "/";
  if (!path.startsWith("/")) {
    path = "/" + path;
  }
  return path;
}
