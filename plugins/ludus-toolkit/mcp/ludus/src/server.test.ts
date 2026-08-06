import { describe, it, before, after } from "node:test";
import assert from "node:assert/strict";
import { createServer, type Server } from "node:http";
import { writeFile, unlink } from "node:fs/promises";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { createMcpServer } from "./server.ts";
import { loadCatalog, type Catalog } from "./catalog.ts";
import { LudusClient } from "./client.ts";

// ── Fixtures ───────────────────────────────────────────────────────────

const SPEC = `
openapi: "3.1.0"
info:
  title: Test API
  version: "1.0"
paths:
  /range:
    get:
      operationId: getRange
      summary: Get all ranges
      description: Returns a list of ranges
      tags:
        - Range Management
      responses:
        "200":
          description: success
  /range/{rangeId}:
    get:
      operationId: getRangeById
      summary: Get a range by ID
      description: Returns a single range
      tags:
        - Range Management
      parameters:
        - name: rangeId
          in: path
          required: true
          schema:
            type: string
      responses:
        "200":
          description: success
    delete:
      operationId: deleteRange
      summary: Delete a range
      description: Destroys a range and all VMs
      tags:
        - Range Management
      parameters:
        - name: rangeId
          in: path
          required: true
          schema:
            type: string
      responses:
        "200":
          description: deleted
  /templates:
    get:
      operationId: getTemplates
      summary: List templates
      description: Returns available VM templates
      tags:
        - Template Management
      responses:
        "200":
          description: success
  /deprecated-endpoint:
    get:
      operationId: deprecatedOp
      summary: Old endpoint
      description: This is deprecated
      tags:
        - Legacy
      deprecated: true
      responses:
        "200":
          description: success
`;

// Helper to call a tool handler through the McpServer's internal tool map.
// Since McpServer doesn't expose a direct "call tool" method for unit tests,
// we test the logic by constructing a Catalog and exercising the handler
// functions indirectly via the MCP protocol's callTool.
// We use the server's connect + client pattern for a proper integration test.

import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { InMemoryTransport } from "@modelcontextprotocol/sdk/inMemory.js";

async function setupTestServer(
  catalog: Catalog,
  client: LudusClient,
  refreshCatalog?: () => Promise<Catalog>,
) {
  const { server, updateCatalog } = createMcpServer(
    catalog,
    client,
    refreshCatalog,
  );
  const [clientTransport, serverTransport] =
    InMemoryTransport.createLinkedPair();

  const mcpClient = new Client({ name: "test-client", version: "1.0.0" });
  await server.connect(serverTransport);
  await mcpClient.connect(clientTransport);

  return { mcpClient, server, updateCatalog };
}

// ── Tests ──────────────────────────────────────────────────────────────

describe("MCP Server", () => {
  describe("list_ludus_operations", () => {
    it("should list all operations", async () => {
      const catalog = await loadCatalog("", undefined, SPEC);
      const client = new LudusClient("https://localhost:8080", "test-key");
      const { mcpClient } = await setupTestServer(catalog, client);

      const result = await mcpClient.callTool({
        name: "list_ludus_operations",
        arguments: {},
      });

      const parsed = JSON.parse(
        (result.content as Array<{ type: string; text: string }>)[0].text,
      );
      assert.equal(parsed.operation_count, 4); // excludes deprecated by default
      assert.ok(
        parsed.operations.some(
          (op: { operation_id: string }) => op.operation_id === "getRange",
        ),
      );
      assert.ok(
        !parsed.operations.some(
          (op: { operation_id: string }) => op.operation_id === "deprecatedOp",
        ),
      );
    });

    it("should include deprecated when requested", async () => {
      const catalog = await loadCatalog("", undefined, SPEC);
      const client = new LudusClient("https://localhost:8080", "test-key");
      const { mcpClient } = await setupTestServer(catalog, client);

      const result = await mcpClient.callTool({
        name: "list_ludus_operations",
        arguments: { include_deprecated: true },
      });

      const parsed = JSON.parse(
        (result.content as Array<{ type: string; text: string }>)[0].text,
      );
      assert.equal(parsed.operation_count, 5);
      assert.ok(
        parsed.operations.some(
          (op: { operation_id: string }) => op.operation_id === "deprecatedOp",
        ),
      );
    });

    it("should filter by tag", async () => {
      const catalog = await loadCatalog("", undefined, SPEC);
      const client = new LudusClient("https://localhost:8080", "test-key");
      const { mcpClient } = await setupTestServer(catalog, client);

      const result = await mcpClient.callTool({
        name: "list_ludus_operations",
        arguments: { tag: "template" },
      });

      const parsed = JSON.parse(
        (result.content as Array<{ type: string; text: string }>)[0].text,
      );
      assert.equal(parsed.operation_count, 1);
      assert.equal(parsed.operations[0].operation_id, "getTemplates");
    });

    it("should filter by query", async () => {
      const catalog = await loadCatalog("", undefined, SPEC);
      const client = new LudusClient("https://localhost:8080", "test-key");
      const { mcpClient } = await setupTestServer(catalog, client);

      const result = await mcpClient.callTool({
        name: "list_ludus_operations",
        arguments: { query: "delete" },
      });

      const parsed = JSON.parse(
        (result.content as Array<{ type: string; text: string }>)[0].text,
      );
      assert.equal(parsed.operation_count, 1);
      assert.equal(parsed.operations[0].operation_id, "deleteRange");
    });

    it("should return source info", async () => {
      const catalog = await loadCatalog("", undefined, SPEC);
      const client = new LudusClient("https://localhost:8080", "test-key");
      const { mcpClient } = await setupTestServer(catalog, client);

      const result = await mcpClient.callTool({
        name: "list_ludus_operations",
        arguments: {},
      });

      const parsed = JSON.parse(
        (result.content as Array<{ type: string; text: string }>)[0].text,
      );
      assert.equal(parsed.source, "bundled-fallback");
    });
  });

  describe("describe_ludus_operation", () => {
    it("should return operation detail", async () => {
      const catalog = await loadCatalog("", undefined, SPEC);
      const client = new LudusClient("https://localhost:8080", "test-key");
      const { mcpClient } = await setupTestServer(catalog, client);

      const result = await mcpClient.callTool({
        name: "describe_ludus_operation",
        arguments: { operation_id: "getRangeById" },
      });

      assert.equal(result.isError, undefined);
      const parsed = JSON.parse(
        (result.content as Array<{ type: string; text: string }>)[0].text,
      );
      assert.equal(parsed.id, "getRangeById");
      assert.equal(parsed.method, "GET");
      assert.equal(parsed.path, "/range/{rangeId}");
      assert.ok(parsed.parameters);
      assert.equal(parsed.parameters[0].name, "rangeId");
    });

    it("should return error for unknown operation", async () => {
      const catalog = await loadCatalog("", undefined, SPEC);
      const client = new LudusClient("https://localhost:8080", "test-key");
      const { mcpClient } = await setupTestServer(catalog, client);

      const result = await mcpClient.callTool({
        name: "describe_ludus_operation",
        arguments: { operation_id: "nonexistent" },
      });

      assert.equal(result.isError, true);
      const text = (
        result.content as Array<{ type: string; text: string }>
      )[0].text;
      assert.ok(text.includes("Unknown operation_id"));
      assert.ok(text.includes("list_ludus_operations"));
    });

    it("should return error for empty operation_id", async () => {
      const catalog = await loadCatalog("", undefined, SPEC);
      const client = new LudusClient("https://localhost:8080", "test-key");
      const { mcpClient } = await setupTestServer(catalog, client);

      const result = await mcpClient.callTool({
        name: "describe_ludus_operation",
        arguments: { operation_id: "  " },
      });

      assert.equal(result.isError, true);
    });
  });

  describe("call_ludus_api", () => {
    it("should return error for unknown operation", async () => {
      const catalog = await loadCatalog("", undefined, SPEC);
      const client = new LudusClient("https://localhost:8080", "test-key");
      const { mcpClient } = await setupTestServer(catalog, client);

      const result = await mcpClient.callTool({
        name: "call_ludus_api",
        arguments: { operation_id: "nonexistent" },
      });

      assert.equal(result.isError, true);
      const text = (
        result.content as Array<{ type: string; text: string }>
      )[0].text;
      assert.ok(text.includes("Unknown operation_id"));
      assert.ok(text.includes("list_ludus_operations"));
    });
  });

  describe("tool listing", () => {
    it("should register all three tools", async () => {
      const catalog = await loadCatalog("", undefined, SPEC);
      const client = new LudusClient("https://localhost:8080", "test-key");
      const { mcpClient } = await setupTestServer(catalog, client);

      const tools = await mcpClient.listTools();
      const names = tools.tools.map((t) => t.name).sort();
      assert.deepEqual(names, [
        "call_ludus_api",
        "describe_ludus_operation",
        "list_ludus_operations",
      ]);
    });

    it("should have correct annotations on tools", async () => {
      const catalog = await loadCatalog("", undefined, SPEC);
      const client = new LudusClient("https://localhost:8080", "test-key");
      const { mcpClient } = await setupTestServer(catalog, client);

      const tools = await mcpClient.listTools();
      const byName = Object.fromEntries(tools.tools.map((t) => [t.name, t]));

      // list and describe are read-only
      assert.equal(byName["list_ludus_operations"].annotations?.readOnlyHint, true);
      assert.equal(byName["describe_ludus_operation"].annotations?.readOnlyHint, true);
      // call is not read-only
      assert.equal(byName["call_ludus_api"].annotations?.readOnlyHint, false);
    });
  });
});

// ── Improvement regression tests ──────────────────────────────────────

const MULTIPART_SPEC = `openapi: "3.1.0"
info:
  title: Test
  version: "1.0"
paths:
  /range/config:
    put:
      operationId: putConfig
      summary: Put config
      requestBody:
        content:
          multipart/form-data:
            schema:
              type: object
              properties:
                file:
                  type: string
                  format: binary
                force:
                  type: boolean
      responses:
        "200":
          description: OK
  /range/artifact:
    post:
      operationId: putArtifact
      summary: Upload an artifact with a non-"file" field name
      requestBody:
        content:
          multipart/form-data:
            schema:
              type: object
              properties:
                artifact:
                  type: string
                  format: binary
                label:
                  type: string
      responses:
        "200":
          description: OK
`;

const JSON_SPEC_WITH_PARAMS = `openapi: "3.1.0"
info:
  title: Test
  version: "1.0"
paths:
  /range/{rangeId}/deploy:
    post:
      operationId: deployRange
      summary: Deploy a range
      parameters:
        - name: rangeId
          in: path
          required: true
          schema: { type: string }
        - name: limit
          in: query
          schema: { type: integer }
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                force:
                  type: boolean
                tags:
                  type: string
      responses:
        "201":
          description: accepted
        "409":
          description: conflict — use force
`;

const SPEC_WITH_EXAMPLES = `openapi: "3.1.0"
info:
  title: Test
  version: "1.0"
paths:
  /build/{projectId}:
    post:
      operationId: buildProject
      summary: Build project
      parameters:
        - name: projectId
          in: path
          required: true
          schema:
            type: string
            example: DEMO
        - name: tail
          in: query
          schema:
            type: integer
            example: 100
        - name: verbose
          in: query
          schema:
            type: boolean
      requestBody:
        content:
          application/json:
            schema:
              type: object
              required: [name, targets]
              properties:
                name:
                  type: string
                  example: "My cool build"
                targets:
                  type: array
                  items: { type: string }
                  example: ["debian-12", "ubuntu-22.04"]
                parallel:
                  type: integer
                  example: 3
                dryRun:
                  type: boolean
      responses:
        "200":
          description: ok
`;

describe("Improvements: describe_ludus_operation example_call", () => {
  it("synthesizes path_params, query_params, and JSON body shape", async () => {
    const catalog = await loadCatalog("", undefined, JSON_SPEC_WITH_PARAMS);
    const client = new LudusClient("https://localhost:8080", "test-key");
    const { mcpClient } = await setupTestServer(catalog, client);

    const result = await mcpClient.callTool({
      name: "describe_ludus_operation",
      arguments: { operation_id: "deployRange" },
    });

    const parsed = JSON.parse(
      (result.content as Array<{ type: string; text: string }>)[0].text,
    );
    assert.ok(parsed.example_call, "output includes example_call");
    assert.equal(parsed.example_call.operation_id, "deployRange");
    assert.deepEqual(parsed.example_call.path_params, { rangeId: "<rangeId>" });
    assert.deepEqual(parsed.example_call.query_params, { limit: "<limit>" });
    assert.equal(parsed.example_call.content_type, "application/json");
    assert.equal(parsed.example_call.body.force, false);
    assert.equal(parsed.example_call.body.tags, "<string>");
  });

  it("synthesizes multipart body with <local file path> for binary fields", async () => {
    const catalog = await loadCatalog("", undefined, MULTIPART_SPEC);
    const client = new LudusClient("https://localhost:8080", "test-key");
    const { mcpClient } = await setupTestServer(catalog, client);

    const result = await mcpClient.callTool({
      name: "describe_ludus_operation",
      arguments: { operation_id: "putArtifact" },
    });

    const parsed = JSON.parse(
      (result.content as Array<{ type: string; text: string }>)[0].text,
    );
    assert.equal(parsed.example_call.content_type, "multipart/form-data");
    assert.equal(parsed.example_call.body.artifact, "<local file path>");
    assert.equal(parsed.example_call.body.label, "<string>");
  });

  it("uses schema.example from parameters and body properties when present", async () => {
    const catalog = await loadCatalog("", undefined, SPEC_WITH_EXAMPLES);
    const client = new LudusClient("https://localhost:8080", "test-key");
    const { mcpClient } = await setupTestServer(catalog, client);

    const result = await mcpClient.callTool({
      name: "describe_ludus_operation",
      arguments: { operation_id: "buildProject" },
    });

    const parsed = JSON.parse(
      (result.content as Array<{ type: string; text: string }>)[0].text,
    );
    const ec = parsed.example_call;
    // Path param has an example — use it instead of "<projectId>".
    assert.equal(ec.path_params.projectId, "DEMO");
    // Query param with example → value; query param without → sentinel.
    assert.equal(ec.query_params.tail, 100);
    assert.equal(ec.query_params.verbose, "<verbose>");
    // Body fields with examples → real values.
    assert.equal(ec.body.name, "My cool build");
    assert.deepEqual(ec.body.targets, ["debian-12", "ubuntu-22.04"]);
    assert.equal(ec.body.parallel, 3);
    // Body field without example → type-appropriate sentinel.
    assert.equal(ec.body.dryRun, false);
  });

  it("emits body_required when the body schema has required fields", async () => {
    const catalog = await loadCatalog("", undefined, SPEC_WITH_EXAMPLES);
    const client = new LudusClient("https://localhost:8080", "test-key");
    const { mcpClient } = await setupTestServer(catalog, client);

    const result = await mcpClient.callTool({
      name: "describe_ludus_operation",
      arguments: { operation_id: "buildProject" },
    });

    const parsed = JSON.parse(
      (result.content as Array<{ type: string; text: string }>)[0].text,
    );
    assert.deepEqual(parsed.example_call.body_required, ["name", "targets"]);
  });

  it("omits body_required when the schema has no required list", async () => {
    // JSON_SPEC_WITH_PARAMS has a body but no required array.
    const catalog = await loadCatalog("", undefined, JSON_SPEC_WITH_PARAMS);
    const client = new LudusClient("https://localhost:8080", "test-key");
    const { mcpClient } = await setupTestServer(catalog, client);

    const result = await mcpClient.callTool({
      name: "describe_ludus_operation",
      arguments: { operation_id: "deployRange" },
    });

    const parsed = JSON.parse(
      (result.content as Array<{ type: string; text: string }>)[0].text,
    );
    assert.equal(parsed.example_call.body_required, undefined);
  });

  it("falls back to sentinels when no examples are present (unchanged behavior)", async () => {
    // JSON_SPEC_WITH_PARAMS deliberately omits examples — sentinels should still render.
    const catalog = await loadCatalog("", undefined, JSON_SPEC_WITH_PARAMS);
    const client = new LudusClient("https://localhost:8080", "test-key");
    const { mcpClient } = await setupTestServer(catalog, client);

    const result = await mcpClient.callTool({
      name: "describe_ludus_operation",
      arguments: { operation_id: "deployRange" },
    });

    const parsed = JSON.parse(
      (result.content as Array<{ type: string; text: string }>)[0].text,
    );
    assert.equal(parsed.example_call.path_params.rangeId, "<rangeId>");
    assert.equal(parsed.example_call.query_params.limit, "<limit>");
    assert.equal(parsed.example_call.body.force, false);
    assert.equal(parsed.example_call.body.tags, "<string>");
  });

  it("omits path_params/query_params/body when none are defined", async () => {
    const catalog = await loadCatalog("", undefined, SPEC);
    const client = new LudusClient("https://localhost:8080", "test-key");
    const { mcpClient } = await setupTestServer(catalog, client);

    const result = await mcpClient.callTool({
      name: "describe_ludus_operation",
      arguments: { operation_id: "getRange" },
    });

    const parsed = JSON.parse(
      (result.content as Array<{ type: string; text: string }>)[0].text,
    );
    assert.equal(parsed.example_call.path_params, undefined);
    assert.equal(parsed.example_call.query_params, undefined);
    assert.equal(parsed.example_call.body, undefined);
  });
});

describe("Improvements: call_ludus_api HTTP behavior", () => {
  let server: Server;
  let baseUrl: string;
  let lastRequest: {
    method: string;
    url: string;
    headers: Record<string, string | string[] | undefined>;
    body: string;
  };
  let nextStatus = 200;
  let nextBody: string | null = null;
  let nextBinary: Buffer | null = null;

  before(async () => {
    await new Promise<void>((resolve) => {
      server = createServer((req, res) => {
        let body = "";
        req.on("data", (chunk) => (body += chunk));
        req.on("end", () => {
          lastRequest = {
            method: req.method ?? "",
            url: req.url ?? "",
            headers: req.headers as Record<string, string | string[] | undefined>,
            body,
          };
          const status = nextStatus;
          if (nextBinary) {
            const bytes = nextBinary;
            nextStatus = 200;
            nextBinary = null;
            res.writeHead(status, { "Content-Type": "application/zip" });
            res.end(bytes);
            return;
          }
          const payload =
            nextBody ?? JSON.stringify({ result: "ok", received: body || null });
          nextStatus = 200;
          nextBody = null;
          res.writeHead(status, { "Content-Type": "application/json" });
          res.end(payload);
        });
      });
      server.listen(0, "127.0.0.1", () => {
        const addr = server.address();
        if (addr && typeof addr === "object") {
          baseUrl = `http://127.0.0.1:${addr.port}`;
        }
        resolve();
      });
    });
  });

  after(async () => {
    await new Promise<void>((resolve) => server.close(() => resolve()));
  });

  it("returns isError:false for non-2xx completed round-trip", async () => {
    const catalog = await loadCatalog("", undefined, JSON_SPEC_WITH_PARAMS);
    const client = new LudusClient(baseUrl, "key");
    const { mcpClient } = await setupTestServer(catalog, client);

    nextStatus = 409;
    nextBody = JSON.stringify({ error: "use --force to override" });

    const result = await mcpClient.callTool({
      name: "call_ludus_api",
      arguments: {
        operation_id: "deployRange",
        path_params: { rangeId: "abc" },
        body: {},
      },
    });

    assert.equal(result.isError, false);
    const parsed = JSON.parse(
      (result.content as Array<{ type: string; text: string }>)[0].text,
    );
    assert.equal(parsed.status_code, 409);
    assert.equal(parsed.success, false);
    assert.deepEqual(parsed.response, { error: "use --force to override" });
    assert.match(parsed.error, /409/);
  });

  it("auto-detects content_type from catalog for multipart operation", async () => {
    const catalog = await loadCatalog("", undefined, MULTIPART_SPEC);
    const client = new LudusClient(baseUrl, "key");
    const { mcpClient } = await setupTestServer(catalog, client);

    const tmpFile = join(tmpdir(), `ludus-auto-ct-${Date.now()}.yml`);
    await writeFile(tmpFile, "ok: true");

    try {
      await mcpClient.callTool({
        name: "call_ludus_api",
        arguments: {
          operation_id: "putConfig",
          body: { file: tmpFile, force: true },
          // content_type intentionally omitted
        },
      });

      assert.ok(
        (lastRequest.headers["content-type"] as string).includes(
          "multipart/form-data",
        ),
        "content-type should be auto-set to multipart/form-data",
      );
      assert.ok(lastRequest.body.includes("ok: true"));
    } finally {
      await unlink(tmpFile);
    }
  });

  it("uploads binary field with non-'file' name as file path", async () => {
    const catalog = await loadCatalog("", undefined, MULTIPART_SPEC);
    const client = new LudusClient(baseUrl, "key");
    const { mcpClient } = await setupTestServer(catalog, client);

    const tmpFile = join(tmpdir(), `ludus-artifact-${Date.now()}.bin`);
    await writeFile(tmpFile, "ARTIFACT-CONTENT");

    try {
      await mcpClient.callTool({
        name: "call_ludus_api",
        arguments: {
          operation_id: "putArtifact",
          body: { artifact: tmpFile, label: "test" },
        },
      });

      // The file contents should appear in the multipart body, NOT the path.
      assert.ok(
        lastRequest.body.includes("ARTIFACT-CONTENT"),
        "file contents should be in multipart body",
      );
      assert.ok(
        !lastRequest.body.includes(tmpFile),
        "the local file path should not leak into the multipart body",
      );
    } finally {
      await unlink(tmpFile);
    }
  });

  it("accepts JSON-stringified body from clients that serialize args", async () => {
    const catalog = await loadCatalog("", undefined, JSON_SPEC_WITH_PARAMS);
    const client = new LudusClient(baseUrl, "key");
    const { mcpClient } = await setupTestServer(catalog, client);

    await mcpClient.callTool({
      name: "call_ludus_api",
      arguments: {
        operation_id: "deployRange",
        path_params: { rangeId: "abc" },
        // Passed as a string — the preprocessor should JSON.parse it.
        body: JSON.stringify({ force: true, tags: "deploy" }),
      },
    });

    const sent = JSON.parse(lastRequest.body);
    assert.equal(sent.force, true);
    assert.equal(sent.tags, "deploy");
  });

  it("surfaces binary response metadata instead of mangled text", async () => {
    const catalog = await loadCatalog("", undefined, JSON_SPEC_WITH_PARAMS);
    const client = new LudusClient(baseUrl, "key");
    const { mcpClient } = await setupTestServer(catalog, client);

    // 7-byte "zip" prelude with a non-UTF8 byte to prove we don't decode it.
    nextBinary = Buffer.from([0x50, 0x4b, 0x03, 0x04, 0xff, 0xfe, 0xfd]);

    const result = await mcpClient.callTool({
      name: "call_ludus_api",
      arguments: {
        operation_id: "deployRange",
        path_params: { rangeId: "abc" },
        body: {},
      },
    });

    assert.equal(result.isError, false);
    const parsed = JSON.parse(
      (result.content as Array<{ type: string; text: string }>)[0].text,
    );
    assert.equal(parsed.status_code, 200);
    assert.ok(parsed.response);
    assert.equal(parsed.response.binary, true);
    assert.ok(parsed.response.content_type.startsWith("application/zip"));
    assert.equal(parsed.response.size_bytes, 7);
    // The raw bytes must not leak into the response as a mangled string.
    assert.equal(typeof parsed.response, "object");
    assert.match(parsed.response.note, /binary/i);
  });

  it("accepts number and boolean query params and coerces to strings", async () => {
    const catalog = await loadCatalog("", undefined, JSON_SPEC_WITH_PARAMS);
    const client = new LudusClient(baseUrl, "key");
    const { mcpClient } = await setupTestServer(catalog, client);

    await mcpClient.callTool({
      name: "call_ludus_api",
      arguments: {
        operation_id: "deployRange",
        path_params: { rangeId: "abc" },
        query_params: { limit: 10 },
        body: {},
      },
    });

    assert.ok(lastRequest.url.includes("limit=10"));
  });
});

describe("Improvements: destructive-op confirmation guard", () => {
  const DESTRUCTIVE_SPEC = `openapi: "3.1.0"
info:
  title: Test
  version: "1.0"
paths:
  /range/{rangeId}:
    delete:
      operationId: deleteRange
      summary: Delete a range from the database and proxmox host
      parameters:
        - name: rangeId
          in: path
          required: true
          schema: { type: string }
      responses:
        "200":
          description: deleted
  /snapshots/remove:
    post:
      operationId: snapshotsRemove
      summary: Delete a snapshot from a VM or multiple VMs
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                name:
                  type: string
      responses:
        "200":
          description: ok
  /range/deploy:
    post:
      operationId: deployRange
      summary: Deploy a range
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                force:
                  type: boolean
      responses:
        "201":
          description: ok
`;

  let server: Server;
  let baseUrl: string;
  let hitCount = 0;

  before(async () => {
    hitCount = 0;
    await new Promise<void>((resolve) => {
      server = createServer((_req, res) => {
        hitCount++;
        res.writeHead(200, { "Content-Type": "application/json" });
        res.end(JSON.stringify({ ok: true }));
      });
      server.listen(0, "127.0.0.1", () => {
        const addr = server.address();
        if (addr && typeof addr === "object") {
          baseUrl = `http://127.0.0.1:${addr.port}`;
        }
        resolve();
      });
    });
  });

  after(async () => {
    await new Promise<void>((resolve) => server.close(() => resolve()));
  });

  it("returns a preview for DELETE ops without confirm, makes no HTTP call", async () => {
    const catalog = await loadCatalog("", undefined, DESTRUCTIVE_SPEC);
    const client = new LudusClient(baseUrl, "key");
    const { mcpClient } = await setupTestServer(catalog, client);
    const before = hitCount;

    const result = await mcpClient.callTool({
      name: "call_ludus_api",
      arguments: {
        operation_id: "deleteRange",
        path_params: { rangeId: "prod" },
      },
    });

    assert.equal(result.isError, false);
    assert.equal(hitCount, before, "no HTTP request should have been made");
    const parsed = JSON.parse(
      (result.content as Array<{ type: string; text: string }>)[0].text,
    );
    assert.equal(parsed.confirmation_required, true);
    assert.equal(parsed.method, "DELETE");
    assert.equal(parsed.operation_id, "deleteRange");
    assert.deepEqual(parsed.would_call_with.path_params, { rangeId: "prod" });
    assert.match(parsed.note, /confirm: true/);
  });

  it("executes the DELETE when confirm:true is passed", async () => {
    const catalog = await loadCatalog("", undefined, DESTRUCTIVE_SPEC);
    const client = new LudusClient(baseUrl, "key");
    const { mcpClient } = await setupTestServer(catalog, client);
    const before = hitCount;

    const result = await mcpClient.callTool({
      name: "call_ludus_api",
      arguments: {
        operation_id: "deleteRange",
        path_params: { rangeId: "prod" },
        confirm: true,
      },
    });

    assert.equal(result.isError, false);
    assert.equal(hitCount, before + 1, "exactly one HTTP request should fire");
    const parsed = JSON.parse(
      (result.content as Array<{ type: string; text: string }>)[0].text,
    );
    assert.equal(parsed.confirmation_required, undefined);
    assert.equal(parsed.status_code, 200);
  });

  it("guards named non-DELETE destructive ops (snapshotsRemove)", async () => {
    const catalog = await loadCatalog("", undefined, DESTRUCTIVE_SPEC);
    const client = new LudusClient(baseUrl, "key");
    const { mcpClient } = await setupTestServer(catalog, client);
    const before = hitCount;

    const result = await mcpClient.callTool({
      name: "call_ludus_api",
      arguments: {
        operation_id: "snapshotsRemove",
        body: { name: "old-snap" },
      },
    });

    assert.equal(hitCount, before, "no HTTP request should fire");
    const parsed = JSON.parse(
      (result.content as Array<{ type: string; text: string }>)[0].text,
    );
    assert.equal(parsed.confirmation_required, true);
    assert.equal(parsed.method, "POST");
    assert.deepEqual(parsed.would_call_with.body, { name: "old-snap" });
  });

  it("does not guard non-destructive mutations (deployRange)", async () => {
    const catalog = await loadCatalog("", undefined, DESTRUCTIVE_SPEC);
    const client = new LudusClient(baseUrl, "key");
    const { mcpClient } = await setupTestServer(catalog, client);
    const before = hitCount;

    const result = await mcpClient.callTool({
      name: "call_ludus_api",
      arguments: {
        operation_id: "deployRange",
        body: { force: false },
      },
    });

    assert.equal(hitCount, before + 1, "deployRange should execute without confirm");
    const parsed = JSON.parse(
      (result.content as Array<{ type: string; text: string }>)[0].text,
    );
    assert.equal(parsed.confirmation_required, undefined);
    assert.equal(parsed.status_code, 200);
  });

  it("confirm:false is treated the same as missing confirm", async () => {
    const catalog = await loadCatalog("", undefined, DESTRUCTIVE_SPEC);
    const client = new LudusClient(baseUrl, "key");
    const { mcpClient } = await setupTestServer(catalog, client);
    const before = hitCount;

    const result = await mcpClient.callTool({
      name: "call_ludus_api",
      arguments: {
        operation_id: "deleteRange",
        path_params: { rangeId: "prod" },
        confirm: false,
      },
    });

    assert.equal(hitCount, before, "no HTTP request should fire");
    const parsed = JSON.parse(
      (result.content as Array<{ type: string; text: string }>)[0].text,
    );
    assert.equal(parsed.confirmation_required, true);
  });
});

describe("Improvements: refresh_ludus_catalog", () => {
  const SPEC_V1 = `openapi: "3.1.0"
info:
  title: v1
  version: "1.0"
paths:
  /v1:
    get:
      operationId: v1Only
      responses:
        "200":
          description: ok
`;
  const SPEC_V2 = `openapi: "3.1.0"
info:
  title: v2
  version: "1.0"
paths:
  /v1:
    get:
      operationId: v1Only
      responses:
        "200":
          description: ok
  /v2:
    get:
      operationId: v2Added
      responses:
        "200":
          description: ok
`;

  it("is not registered when no refresh callback is provided", async () => {
    const catalog = await loadCatalog("", undefined, SPEC_V1);
    const client = new LudusClient("https://localhost:8080", "key");
    const { mcpClient } = await setupTestServer(catalog, client);

    const tools = await mcpClient.listTools();
    const names = tools.tools.map((t) => t.name);
    assert.ok(!names.includes("refresh_ludus_catalog"));
  });

  it("is registered when a refresh callback is provided and swaps the catalog", async () => {
    const v1 = await loadCatalog("", undefined, SPEC_V1);
    const client = new LudusClient("https://localhost:8080", "key");

    const refresh = async () => loadCatalog("", undefined, SPEC_V2);
    const { mcpClient } = await setupTestServer(v1, client, refresh);

    const tools = await mcpClient.listTools();
    assert.ok(tools.tools.some((t) => t.name === "refresh_ludus_catalog"));

    // Before refresh — v2Added must not exist.
    let listed = await mcpClient.callTool({
      name: "list_ludus_operations",
      arguments: {},
    });
    let parsed = JSON.parse(
      (listed.content as Array<{ type: string; text: string }>)[0].text,
    );
    assert.ok(
      !parsed.operations.some(
        (op: { operation_id: string }) => op.operation_id === "v2Added",
      ),
    );

    // Refresh.
    const refreshResult = await mcpClient.callTool({
      name: "refresh_ludus_catalog",
      arguments: {},
    });
    assert.notEqual(refreshResult.isError, true);

    // After refresh — v2Added should now be present.
    listed = await mcpClient.callTool({
      name: "list_ludus_operations",
      arguments: {},
    });
    parsed = JSON.parse(
      (listed.content as Array<{ type: string; text: string }>)[0].text,
    );
    assert.ok(
      parsed.operations.some(
        (op: { operation_id: string }) => op.operation_id === "v2Added",
      ),
    );
  });
});
