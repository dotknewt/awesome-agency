import { z } from "zod";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import type { CallToolResult } from "@modelcontextprotocol/sdk/types.js";
import { Catalog, type Operation, type OperationDetail } from "./catalog.js";
import { LudusClient } from "./client.js";

/**
 * Operations that require explicit `confirm: true` before executing.
 * The guard catches the two categories where a mistaken call causes
 * data loss or irreversible state changes:
 *
 *   1. All HTTP DELETE operations (handled by method check below).
 *   2. The specific POST/PUT ops listed here that cause data loss
 *      without being DELETEs.
 *
 * Long-running mutations like deployRange or buildTemplates are
 * intentionally NOT guarded — they consume resources but are
 * reversible, and guarding them would train agents to pass
 * `confirm: true` reflexively, defeating the guard.
 */
const DESTRUCTIVE_OPERATION_IDS = new Set<string>([
  "snapshotsRemove",
  "snapshotsRollback",
  "stopTesting",
]);

function isDestructiveOperation(op: Operation): boolean {
  return op.method === "DELETE" || DESTRUCTIVE_OPERATION_IDS.has(op.id);
}

// ── Input schemas ─────────────────────────────────────────────────────

// Accept either a plain object or a JSON-stringified object. Some MCP
// client harnesses serialize complex tool arguments to strings before
// transmitting them over stdio; this preprocessor absorbs both forms.
const JsonObjectSchema = z.preprocess(
  (val) => {
    if (typeof val === "string" && val.trim()) {
      try {
        return JSON.parse(val);
      } catch {
        return val;
      }
    }
    return val;
  },
  z.record(z.any()),
);

// Scalar params (path/query): accept string, number, or boolean values,
// then coerce each value to a string for URL construction. Also accepts
// a JSON-stringified object as a whole for the same reason as above.
const ScalarParamsSchema = z.preprocess(
  (val) => {
    if (typeof val === "string" && val.trim()) {
      try {
        return JSON.parse(val);
      } catch {
        return val;
      }
    }
    return val;
  },
  z
    .record(z.union([z.string(), z.number(), z.boolean()]))
    .transform((obj) =>
      Object.fromEntries(
        Object.entries(obj).map(([k, v]) => [k, String(v)]),
      ),
    ),
);

const ListOperationsInputSchema = z.object({
  tag: z
    .string()
    .optional()
    .describe("Optional tag filter (case-insensitive contains match)"),
  query: z
    .string()
    .optional()
    .describe(
      "Optional text filter applied to operation id, path, summary, and description",
    ),
  include_deprecated: z
    .boolean()
    .optional()
    .default(false)
    .describe("Include deprecated operations in results"),
});

const DescribeOperationInputSchema = z.object({
  operation_id: z
    .string()
    .describe("Operation ID from list_ludus_operations"),
});

const CallApiInputSchema = z.object({
  operation_id: z
    .string()
    .describe("Operation ID from list_ludus_operations"),
  path_params: ScalarParamsSchema.optional().describe(
    "Path parameters for templated paths (values coerced to strings)",
  ),
  query_params: ScalarParamsSchema.optional().describe(
    "Query string parameters (values coerced to strings)",
  ),
  body: JsonObjectSchema.optional().describe(
    "Request body for POST/PUT/PATCH operations. For multipart operations, fields flagged as file uploads (format: binary in the OpenAPI spec) must be local file paths.",
  ),
  content_type: z
    .string()
    .optional()
    .describe(
      "Request content type. If omitted, it is auto-detected from the operation's OpenAPI requestBody content type.",
    ),
  confirm: z
    .boolean()
    .optional()
    .describe(
      "Required for destructive operations (all DELETE methods plus snapshotsRemove, snapshotsRollback, stopTesting). If the operation is destructive and confirm is not true, the tool returns a preview instead of executing.",
    ),
});

const RefreshCatalogInputSchema = z.object({});

// ── Output schemas ────────────────────────────────────────────────────

const OperationSummarySchema = z.object({
  operation_id: z.string(),
  method: z.string(),
  path: z.string(),
  summary: z.string(),
  tags: z.array(z.string()),
  deprecated: z.boolean(),
});

const ListOperationsOutputSchema = z.object({
  source: z.string().describe("Where the OpenAPI spec was loaded from"),
  operation_count: z.number().describe("Number of matched operations"),
  operations: z.array(OperationSummarySchema),
});

const DescribeOperationOutputSchema = z.object({
  id: z.string(),
  method: z.string(),
  path: z.string(),
  summary: z.string(),
  description: z.string(),
  tags: z.array(z.string()),
  deprecated: z.boolean(),
  parameters: z.array(z.any()).optional(),
  requestBody: z.any().optional(),
  responses: z.array(z.any()).optional(),
  example_call: z
    .record(z.any())
    .describe(
      "Synthetic example showing the exact call_ludus_api arguments for this operation. When the OpenAPI spec provides example values on parameters or properties, those are used; otherwise sentinel placeholders are emitted. If requestBody has required fields, they are listed as `body_required`.",
    ),
});

// ── Server factory ────────────────────────────────────────────────────

export interface LudusMcpServer {
  server: McpServer;
  updateCatalog(newCatalog: Catalog): void;
}

export function createMcpServer(
  initialCatalog: Catalog,
  client: LudusClient,
  refreshCatalog?: () => Promise<Catalog>,
): LudusMcpServer {
  let catalog = initialCatalog;

  const server = new McpServer(
    {
      name: "ludus-mcp",
      version: "0.1.0",
    },
    {
      instructions:
        "Ludus local MCP server. Discover operations with list_ludus_operations, inspect parameters with describe_ludus_operation (the output includes an example_call showing the exact call shape), then execute with call_ludus_api.\n\nWhen passing string values to tools, send the content directly without escape sequences. For example, use real newlines in markdown content rather than literal backslash-n (\\n) characters.",
    },
  );

  // ── list_ludus_operations ──────────────────────────────────────────

  server.registerTool(
    "list_ludus_operations",
    {
      title: "List Ludus Operations",
      description:
        "List available Ludus API operations loaded from OpenAPI spec. Filter by tag or free-text query.",
      inputSchema: ListOperationsInputSchema,
      outputSchema: ListOperationsOutputSchema,
      annotations: {
        readOnlyHint: true,
        openWorldHint: false,
      },
    },
    async (args): Promise<CallToolResult> => {
      const tag = (args.tag ?? "").trim().toLowerCase();
      const query = (args.query ?? "").trim().toLowerCase();
      const includeDeprecated = args.include_deprecated ?? false;

      const matched = catalog.operations().filter((op) => {
        if (op.deprecated && !includeDeprecated) return false;
        if (tag && !operationHasTag(op, tag)) return false;
        if (query && !operationMatchesQuery(op, query)) return false;
        return true;
      });

      const structuredContent = {
        source: catalog.source(),
        operation_count: matched.length,
        operations: matched.map((op) => ({
          operation_id: op.id,
          method: op.method,
          path: op.path,
          summary: op.summary,
          tags: op.tags,
          deprecated: op.deprecated,
        })),
      };

      return {
        content: [{ type: "text", text: JSON.stringify(structuredContent, null, 2) }],
        structuredContent,
      };
    },
  );

  // ── describe_ludus_operation ────────────────────────────────────────

  server.registerTool(
    "describe_ludus_operation",
    {
      title: "Describe Ludus Operation",
      description:
        "Get full parameter, request body, and response schemas for a single Ludus API operation, plus a synthesized example_call showing the exact arguments to pass to call_ludus_api.",
      inputSchema: DescribeOperationInputSchema,
      outputSchema: DescribeOperationOutputSchema,
      annotations: {
        readOnlyHint: true,
        openWorldHint: false,
      },
    },
    async (args): Promise<CallToolResult> => {
      const id = args.operation_id.trim();
      if (!id) {
        return {
          isError: true,
          content: [{ type: "text", text: "operation_id is required" }],
        };
      }

      const detail = catalog.getDetail(id);
      if (!detail) {
        return {
          isError: true,
          content: [
            {
              type: "text",
              text: `Unknown operation_id "${id}"; use list_ludus_operations to discover available operations`,
            },
          ],
        };
      }

      const output = {
        ...detail,
        example_call: synthesizeExampleCall(detail),
      };

      const json = JSON.stringify(output, null, 2);
      return {
        content: [{ type: "text", text: json }],
        structuredContent: JSON.parse(json),
      };
    },
  );

  // ── call_ludus_api ─────────────────────────────────────────────────

  server.registerTool(
    "call_ludus_api",
    {
      title: "Call Ludus API",
      description:
        "Execute a Ludus API operation by operation_id from list_ludus_operations. " +
        "content_type is auto-detected from the operation's OpenAPI spec if not provided. " +
        "For multipart/form-data operations, any body field marked 'format: binary' in the spec " +
        "(see example_call from describe_ludus_operation) must be an absolute local file path; " +
        "the server reads the file from disk.",
      inputSchema: CallApiInputSchema,
      annotations: {
        readOnlyHint: false,
        openWorldHint: false,
      },
    },
    async (args): Promise<CallToolResult> => {
      const opId = args.operation_id.trim();
      const op = catalog.get(opId);
      if (!op) {
        return {
          isError: true,
          content: [
            {
              type: "text",
              text: `Unknown operation_id "${opId}"; use list_ludus_operations to discover available operations`,
            },
          ],
        };
      }

      const detail = catalog.getDetail(opId);
      const resolvedContentType =
        (args.content_type?.trim() || detail?.requestBody?.contentType) ??
        undefined;
      const fileFields =
        resolvedContentType === "multipart/form-data"
          ? extractBinaryFieldNames(detail?.requestBody?.schema)
          : [];

      // Destructive-operation guard: require an explicit confirm:true
      // before executing. Returns a preview of what would be sent so
      // the caller (or the user reviewing the agent's trace) can
      // inspect the action before authorizing it.
      if (isDestructiveOperation(op) && args.confirm !== true) {
        const would_call_with: Record<string, unknown> = {};
        if (args.path_params) would_call_with.path_params = args.path_params;
        if (args.query_params) would_call_with.query_params = args.query_params;
        if (args.body !== undefined) would_call_with.body = args.body;
        if (resolvedContentType) {
          would_call_with.content_type = resolvedContentType;
        }
        const preview = {
          confirmation_required: true,
          operation_id: op.id,
          method: op.method,
          path: op.path,
          summary: op.summary,
          would_call_with,
          note:
            "This operation is destructive and may cause data loss or irreversible state changes. Re-submit the exact same arguments with `confirm: true` to execute.",
        };
        return {
          isError: false,
          content: [{ type: "text", text: JSON.stringify(preview, null, 2) }],
        };
      }

      try {
        const resp = await client.do({
          method: op.method,
          path: op.path,
          pathParams: args.path_params,
          queryParams: args.query_params,
          body: args.body,
          contentType: resolvedContentType,
          fileFields,
        });

        const result: Record<string, unknown> = {
          operation_id: op.id,
          method: op.method,
          path: op.path,
          status_code: resp.statusCode,
          success: resp.success,
        };

        if (resp.binary) {
          result.response = {
            binary: true,
            content_type: resp.binary.contentType,
            size_bytes: resp.binary.size,
            note:
              "Binary response body is not included. The endpoint returned a non-text payload; call the Ludus API directly (e.g. curl) if you need the bytes.",
          };
        } else if (resp.json !== null) {
          result.response = resp.json;
        } else if (resp.body) {
          result.response = resp.body;
        }

        if (!resp.success) {
          result.error = `Ludus API returned status ${resp.statusCode}`;
        }

        // A completed HTTP round-trip is a successful tool invocation even
        // when the server returned a non-2xx status. Returning isError:false
        // keeps the agent's reasoning loop open so it can inspect the
        // response body (which may contain actionable remediation like
        // "use --force") rather than halting on a terminal tool error.
        return {
          content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
          isError: false,
        };
      } catch (err) {
        const message =
          err instanceof Error ? err.message : String(err);
        return {
          isError: true,
          content: [
            {
              type: "text",
              text: JSON.stringify(
                {
                  operation_id: op.id,
                  method: op.method,
                  path: op.path,
                  error: message,
                },
                null,
                2,
              ),
            },
          ],
        };
      }
    },
  );

  // ── refresh_ludus_catalog ──────────────────────────────────────────

  if (refreshCatalog) {
    server.registerTool(
      "refresh_ludus_catalog",
      {
        title: "Refresh Ludus Catalog",
        description:
          "Re-fetch the OpenAPI spec from the configured Ludus server and replace the in-memory catalog. Use this after the server has been rebuilt with new endpoints so you do not need to restart the MCP process.",
        inputSchema: RefreshCatalogInputSchema,
        annotations: {
          readOnlyHint: false,
          openWorldHint: false,
        },
      },
      async (): Promise<CallToolResult> => {
        try {
          const fresh = await refreshCatalog();
          catalog = fresh;
          return {
            content: [
              {
                type: "text",
                text: `Catalog refreshed from ${fresh.source()} (${fresh.operations().length} operations).`,
              },
            ],
          };
        } catch (err) {
          const message = err instanceof Error ? err.message : String(err);
          return {
            isError: true,
            content: [
              {
                type: "text",
                text: `Failed to refresh catalog: ${message}`,
              },
            ],
          };
        }
      },
    );
  }

  return {
    server,
    updateCatalog(newCatalog: Catalog) {
      catalog = newCatalog;
    },
  };
}

// ── Helpers ───────────────────────────────────────────────────────────

function operationHasTag(
  op: { tags: string[] },
  tag: string,
): boolean {
  return op.tags.some((t) => t.toLowerCase().includes(tag));
}

function operationMatchesQuery(
  op: { id: string; path: string; summary: string; description: string },
  query: string,
): boolean {
  const haystack = `${op.id} ${op.path} ${op.summary} ${op.description}`.toLowerCase();
  return haystack.includes(query);
}

/**
 * Synthesize a concrete call_ludus_api argument example for the given
 * operation. The goal is to collapse the gap between the OpenAPI
 * parameter/requestBody schema (which describes the REST endpoint) and
 * the MCP tool's argument shape (path_params / query_params / body /
 * content_type).
 *
 * When the spec provides an `example` on a parameter schema or property
 * we prefer that over a generic sentinel — agents then get a runnable,
 * copy-pasteable example rather than a placeholder they have to fill in.
 */
function synthesizeExampleCall(
  detail: OperationDetail,
): Record<string, unknown> {
  const example: Record<string, unknown> = { operation_id: detail.id };

  const params = detail.parameters ?? [];
  const pathParams = params.filter((p) => p.in === "path");
  if (pathParams.length) {
    example.path_params = Object.fromEntries(
      pathParams.map((p) => [p.name, paramExample(p)]),
    );
  }

  const queryParams = params.filter((p) => p.in === "query");
  if (queryParams.length) {
    example.query_params = Object.fromEntries(
      queryParams.map((p) => [p.name, paramExample(p)]),
    );
  }

  if (detail.requestBody) {
    if (detail.requestBody.contentType) {
      example.content_type = detail.requestBody.contentType;
    }
    const body = synthesizeBody(detail.requestBody.schema);
    if (body !== undefined) example.body = body;
    const required = detail.requestBody.schema?.required;
    if (Array.isArray(required) && required.length > 0) {
      example.body_required = required;
    }
  }

  return example;
}

function paramExample(
  param: { name: string; schema?: Record<string, unknown> },
): unknown {
  const schema = param.schema;
  if (schema?.example !== undefined) return schema.example;
  return `<${param.name}>`;
}

function synthesizeBody(
  schema: Record<string, unknown> | undefined,
): unknown {
  if (!schema) return undefined;
  // A whole-body example trumps property-by-property synthesis.
  if (schema.example !== undefined) return schema.example;
  if (schema.type === "object" && schema.properties) {
    const props = schema.properties as Record<string, Record<string, unknown>>;
    const result: Record<string, unknown> = {};
    for (const [name, prop] of Object.entries(props)) {
      result[name] = synthesizeValue(prop);
    }
    return result;
  }
  return synthesizeValue(schema);
}

function synthesizeValue(schema: Record<string, unknown>): unknown {
  // Prefer the spec's own example. This makes example_call a runnable
  // starting point rather than a template the agent has to fill in.
  if (schema.example !== undefined) return schema.example;
  if (schema.format === "binary") return "<local file path>";
  if (Array.isArray(schema.enum) && schema.enum.length > 0) {
    return `<${(schema.enum as unknown[]).map((v) => String(v)).join("|")}>`;
  }
  switch (schema.type) {
    case "string":
      if (typeof schema.format === "string") return `<${schema.format}>`;
      return `<string>`;
    case "boolean":
      return false;
    case "integer":
    case "number":
      return 0;
    case "array":
      return [];
    case "object":
      if (schema.properties) return synthesizeBody(schema);
      return {};
    default:
      return null;
  }
}

function extractBinaryFieldNames(
  schema: Record<string, unknown> | undefined,
): string[] {
  if (!schema || schema.type !== "object") return [];
  const props = schema.properties as
    | Record<string, Record<string, unknown>>
    | undefined;
  if (!props) return [];
  return Object.entries(props)
    .filter(([, prop]) => prop.format === "binary")
    .map(([name]) => name);
}
