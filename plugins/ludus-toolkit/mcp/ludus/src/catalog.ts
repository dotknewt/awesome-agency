import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import SwaggerParser from "@apidevtools/swagger-parser";
import type { OpenAPI, OpenAPIV3 } from "openapi-types";
import { secureFetch } from "./client.js";

// ── Public types ──────────────────────────────────────────────────────

export interface Operation {
  id: string;
  method: string;
  path: string;
  summary: string;
  description: string;
  tags: string[];
  deprecated: boolean;
}

export interface OperationDetail extends Operation {
  parameters?: Parameter[];
  requestBody?: RequestBody;
  responses?: ResponseSchema[];
}

export interface Parameter {
  name: string;
  in: string;
  description?: string;
  required?: boolean;
  schema?: Record<string, unknown>;
}

export interface RequestBody {
  contentType?: string;
  schema?: Record<string, unknown>;
}

export interface ResponseSchema {
  statusCode: string;
  description?: string;
  schema?: Record<string, unknown>;
}

// ── Catalog ───────────────────────────────────────────────────────────

export class Catalog {
  private _source: string;
  private _operations: Operation[];
  private _byId: Map<string, Operation>;
  private _details: Map<string, OperationDetail>;

  constructor(
    source: string,
    operations: Operation[],
    byId: Map<string, Operation>,
    details: Map<string, OperationDetail>,
  ) {
    this._source = source;
    this._operations = operations;
    this._byId = byId;
    this._details = details;
  }

  source(): string {
    return this._source;
  }

  operations(): Operation[] {
    return [...this._operations];
  }

  get(id: string): Operation | undefined {
    return this._byId.get(id);
  }

  getDetail(id: string): OperationDetail | undefined {
    return this._details.get(id);
  }
}

// ── Loader ────────────────────────────────────────────────────────────

function loadBundledSpec(): string {
  const __filename = fileURLToPath(import.meta.url);
  const __dirname = dirname(__filename);
  return readFileSync(join(__dirname, "openapi.yaml"), "utf-8");
}

export async function loadCatalog(
  specUrl: string,
  apiKey?: string,
  fallbackSpec?: string,
): Promise<Catalog> {
  let yamlText: string | undefined;
  let source = specUrl;

  if (specUrl.trim()) {
    try {
      const headers: Record<string, string> = {};
      if (apiKey) {
        headers["X-API-KEY"] = apiKey;
      }
      const resp = await secureFetch(specUrl, { headers });
      if (resp.ok) {
        yamlText = await resp.text();
      }
    } catch {
      // fetch failed, fall through
    }
  }

  if (!yamlText && fallbackSpec) {
    yamlText = fallbackSpec;
    source = "bundled-fallback";
  }

  if (!yamlText) {
    try {
      yamlText = loadBundledSpec();
      source = "bundled-spec";
    } catch {
      throw new Error(
        "Failed to fetch OpenAPI spec from server and no bundled spec found",
      );
    }
  }

  return parseSpec(yamlText, source);
}

// ── Parser ────────────────────────────────────────────────────────────

const METHODS = ["get", "post", "put", "patch", "delete"] as const;

async function parseSpec(yamlText: string, source: string): Promise<Catalog> {
  // swagger-parser can parse YAML directly from a string via a dummy path
  // but it needs an object. Parse YAML ourselves, then dereference.
  const { default: YAML } = await import("yaml");
  const raw = YAML.parse(yamlText) as OpenAPI.Document;
  const api = (await SwaggerParser.dereference(raw)) as OpenAPIV3.Document;

  if (!api.paths || Object.keys(api.paths).length === 0) {
    throw new Error("OpenAPI spec has no paths");
  }

  const operations: Operation[] = [];
  const details = new Map<string, OperationDetail>();

  for (const [route, pathItem] of Object.entries(api.paths)) {
    if (!pathItem) continue;

    for (const method of METHODS) {
      const op = pathItem[method];
      if (!op || !op.operationId?.trim()) continue;

      const id = op.operationId.trim();
      const path = route.startsWith("/") ? route : `/${route}`;

      const operation: Operation = {
        id,
        method: method.toUpperCase(),
        path,
        summary: (op.summary ?? "").trim(),
        description: (op.description ?? "").trim(),
        tags: op.tags ?? [],
        deprecated: op.deprecated ?? false,
      };
      operations.push(operation);

      const detail: OperationDetail = {
        ...operation,
        parameters: [],
        responses: [],
      };

      // Parameters — after dereference, these are resolved objects.
      if (op.parameters) {
        for (const p of op.parameters) {
          const param = p as OpenAPIV3.ParameterObject;
          detail.parameters!.push({
            name: param.name,
            in: param.in,
            description: (param.description ?? "").trim(),
            required: param.required ?? false,
            schema: param.schema
              ? cleanSchema(param.schema as Record<string, unknown>)
              : undefined,
          });
        }
      }

      // Request body.
      if (op.requestBody) {
        const rb = op.requestBody as OpenAPIV3.RequestBodyObject;
        if (rb.content) {
          for (const [ct, media] of Object.entries(rb.content)) {
            if (media.schema) {
              const schema = cleanSchema(
                media.schema as Record<string, unknown>,
              );
              // Annotate multipart file fields so callers know to pass a path.
              if (ct === "multipart/form-data") {
                const props = schema.properties as
                  | Record<string, Record<string, unknown>>
                  | undefined;
                if (props) {
                  for (const [, prop] of Object.entries(props)) {
                    if (prop.format === "binary") {
                      prop.description =
                        `Local file path to upload${prop.description ? ` — ${prop.description}` : ""}`;
                    }
                  }
                }
              }
              detail.requestBody = { contentType: ct, schema };
              break;
            }
          }
        }
      }

      // Responses.
      if (op.responses) {
        for (const code of Object.keys(op.responses).sort()) {
          const resp = op.responses[code] as OpenAPIV3.ResponseObject;
          const rs: ResponseSchema = {
            statusCode: code,
            description: (resp.description ?? "").trim(),
          };
          if (resp.content) {
            for (const media of Object.values(resp.content)) {
              if (media.schema) {
                rs.schema = cleanSchema(
                  media.schema as Record<string, unknown>,
                );
                break;
              }
            }
          }
          detail.responses!.push(rs);
        }
      }

      details.set(id, detail);
    }
  }

  operations.sort((a, b) => {
    if (a.path === b.path) return a.method.localeCompare(b.method);
    return a.path.localeCompare(b.path);
  });

  const byId = new Map<string, Operation>();
  for (const op of operations) {
    byId.set(op.id, op);
  }

  if (operations.length === 0) {
    throw new Error("No operations found in OpenAPI spec");
  }

  return new Catalog(source, operations, byId, details);
}

// ── Schema cleanup ────────────────────────────────────────────────────

/**
 * Clean a dereferenced schema for presentation.
 * Merges allOf into a single object schema and strips circular refs
 * that swagger-parser replaces with object identity.
 */
function cleanSchema(
  schema: Record<string, unknown>,
  seen = new WeakSet<object>(),
): Record<string, unknown> {
  if (seen.has(schema)) return { type: "object", description: "(circular)" };
  seen.add(schema);

  // Merge allOf into a flat object.
  if (Array.isArray(schema.allOf)) {
    const merged: Record<string, unknown> = { type: "object" };
    const mergedProps: Record<string, unknown> = {};
    const mergedRequired: string[] = [];

    for (const sub of schema.allOf as Record<string, unknown>[]) {
      const cleaned = cleanSchema(sub, seen);
      if (cleaned.properties && typeof cleaned.properties === "object") {
        Object.assign(mergedProps, cleaned.properties);
      }
      if (Array.isArray(cleaned.required)) {
        mergedRequired.push(...(cleaned.required as string[]));
      }
      // Copy other fields from sub-schemas (description, type, etc.)
      for (const [k, v] of Object.entries(cleaned)) {
        if (k !== "properties" && k !== "required" && k !== "type") {
          merged[k] = v;
        }
      }
    }

    if (Object.keys(mergedProps).length > 0) merged.properties = mergedProps;
    if (mergedRequired.length > 0) merged.required = mergedRequired;
    return merged;
  }

  const result: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(schema)) {
    if (value && typeof value === "object" && !Array.isArray(value)) {
      result[key] = cleanSchema(value as Record<string, unknown>, seen);
    } else if (Array.isArray(value)) {
      result[key] = value.map((item) =>
        item && typeof item === "object"
          ? cleanSchema(item as Record<string, unknown>, seen)
          : item,
      );
    } else {
      result[key] = value;
    }
  }
  return result;
}
