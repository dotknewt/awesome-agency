import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { loadCatalog } from "./catalog.ts";

const BASIC_SPEC = `openapi: 3.0.1
info:
  title: Test
  version: "1.0"
paths:
  /range:
    get:
      operationId: listRange
      summary: List range
      tags: [Range Management]
      parameters:
        - name: rangeID
          in: query
          description: The range to query
          required: false
          schema:
            type: string
      responses:
        '200':
          description: OK
          content:
            application/json:
              schema:
                type: object
                properties:
                  rangeID:
                    type: string
    delete:
      operationId: deleteRange
      summary: Delete range
      responses:
        '200':
          description: OK
`;

const SPEC_WITH_REF = `openapi: 3.0.1
info:
  title: Test
  version: "1.0"
paths:
  /user:
    get:
      operationId: listUser
      summary: Get user
      responses:
        '200':
          description: OK
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/UserObj'
components:
  schemas:
    UserObj:
      type: object
      required: [name]
      properties:
        name:
          type: string
          description: User name
        isAdmin:
          type: boolean
`;

const SPEC_WITH_NESTED_REF = `openapi: 3.0.1
info:
  title: Test
  version: "1.0"
paths:
  /range:
    get:
      operationId: getRange
      summary: Get range
      responses:
        '200':
          description: OK
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/RangeObj'
components:
  schemas:
    IDType:
      type: string
      pattern: '^[A-Z]+$'
    RangeObj:
      type: object
      properties:
        id:
          $ref: '#/components/schemas/IDType'
        name:
          type: string
`;

const SPEC_WITH_ARRAY_REF = `openapi: 3.0.1
info:
  title: Test
  version: "1.0"
paths:
  /users:
    get:
      operationId: listUsers
      summary: List users
      responses:
        '200':
          description: OK
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: '#/components/schemas/UserObj'
components:
  schemas:
    UserObj:
      type: object
      properties:
        name:
          type: string
`;

const SPEC_WITH_REQUEST_BODY = `openapi: 3.0.1
info:
  title: Test
  version: "1.0"
paths:
  /range/deploy:
    post:
      operationId: deployRange
      summary: Deploy range
      parameters:
        - name: rangeID
          in: query
          description: Range to deploy
          required: false
          schema:
            type: string
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                tags:
                  type: string
                  description: ansible tags
                force:
                  type: boolean
                  description: force deploy
      responses:
        '201':
          description: range deployed
        '400':
          description: bad input
`;

const SPEC_WITH_ALLOF = `openapi: 3.0.1
info:
  title: Test
  version: "1.0"
paths:
  /user:
    post:
      operationId: addUser
      summary: Add user
      responses:
        '201':
          description: user created
          content:
            application/json:
              schema:
                allOf:
                  - $ref: '#/components/schemas/UserObj'
                  - type: object
                    properties:
                      apiKey:
                        type: string
components:
  schemas:
    UserObj:
      type: object
      required: [name]
      properties:
        name:
          type: string
`;

describe("catalog", () => {
  describe("basic parsing", () => {
    it("should parse operations", async () => {
      const catalog = await loadCatalog("", undefined, BASIC_SPEC);
      const ops = catalog.operations();
      assert.equal(ops.length, 2);

      const listOp = catalog.get("listRange");
      assert.ok(listOp);
      assert.equal(listOp.method, "GET");
      assert.equal(listOp.path, "/range");

      const deleteOp = catalog.get("deleteRange");
      assert.ok(deleteOp);
      assert.equal(deleteOp.method, "DELETE");
    });

    it("should parse parameters and responses", async () => {
      const catalog = await loadCatalog("", undefined, BASIC_SPEC);
      const detail = catalog.getDetail("listRange");
      assert.ok(detail);
      assert.equal(detail.parameters!.length, 1);
      assert.equal(detail.parameters![0].name, "rangeID");
      assert.equal(detail.responses!.length, 1);
      assert.equal(detail.responses![0].statusCode, "200");
    });
  });

  describe("$ref resolution", () => {
    it("should resolve simple $ref", async () => {
      const catalog = await loadCatalog("", undefined, SPEC_WITH_REF);
      const detail = catalog.getDetail("listUser");
      assert.ok(detail);

      const schema = detail.responses![0].schema as Record<string, unknown>;
      assert.ok(schema);
      assert.equal(schema.type, "object");

      const props = schema.properties as Record<string, Record<string, unknown>>;
      assert.ok(props.name);
      assert.ok(props.isAdmin);
      assert.equal(props.name.type, "string");
    });

    it("should resolve nested $ref", async () => {
      const catalog = await loadCatalog("", undefined, SPEC_WITH_NESTED_REF);
      const detail = catalog.getDetail("getRange");
      assert.ok(detail);

      const schema = detail.responses![0].schema as Record<string, unknown>;
      const props = schema.properties as Record<string, Record<string, unknown>>;
      assert.ok(props.id);
      assert.equal(props.id.type, "string");
      assert.equal(props.id.pattern, "^[A-Z]+$");
    });

    it("should resolve $ref in array items", async () => {
      const catalog = await loadCatalog("", undefined, SPEC_WITH_ARRAY_REF);
      const detail = catalog.getDetail("listUsers");
      assert.ok(detail);

      const schema = detail.responses![0].schema as Record<string, unknown>;
      assert.equal(schema.type, "array");

      const items = schema.items as Record<string, unknown>;
      assert.ok(items);
      assert.equal(items.type, "object");
    });
  });

  describe("request body and responses", () => {
    it("should parse operation with request body", async () => {
      const catalog = await loadCatalog("", undefined, SPEC_WITH_REQUEST_BODY);
      const detail = catalog.getDetail("deployRange");
      assert.ok(detail);

      assert.equal(detail.parameters!.length, 1);
      assert.ok(detail.requestBody);
      assert.equal(detail.requestBody.contentType, "application/json");

      const bodyProps = detail.requestBody.schema?.properties as Record<string, unknown>;
      assert.ok(bodyProps.tags);
      assert.ok(bodyProps.force);

      assert.equal(detail.responses!.length, 2);
    });
  });

  describe("allOf merging", () => {
    it("should merge allOf into a single schema", async () => {
      const catalog = await loadCatalog("", undefined, SPEC_WITH_ALLOF);
      const detail = catalog.getDetail("addUser");
      assert.ok(detail);

      const schema = detail.responses![0].schema as Record<string, unknown>;
      assert.equal(schema.type, "object");

      // Should have both the UserObj props and the extra apiKey prop
      const props = schema.properties as Record<string, Record<string, unknown>>;
      assert.ok(props.name, "should have 'name' from UserObj");
      assert.ok(props.apiKey, "should have 'apiKey' from inline schema");
    });
  });

  describe("multipart file annotation", () => {
    const SPEC_WITH_MULTIPART = `openapi: 3.0.1
info:
  title: Test
  version: "1.0"
paths:
  /range/config:
    put:
      operationId: putConfig
      summary: Update config
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
        '200':
          description: OK
`;

    it("should annotate binary fields with file-path description", async () => {
      const catalog = await loadCatalog("", undefined, SPEC_WITH_MULTIPART);
      const detail = catalog.getDetail("putConfig");
      assert.ok(detail);
      assert.ok(detail.requestBody);
      assert.equal(detail.requestBody.contentType, "multipart/form-data");

      const props = detail.requestBody.schema?.properties as Record<
        string,
        Record<string, unknown>
      >;
      assert.ok(props.file);
      assert.match(
        props.file.description as string,
        /local file path/i,
      );
      // Non-binary fields should not be annotated.
      assert.equal(props.force.description, undefined);
    });
  });

  describe("bundled spec fallback", () => {
    it("should load bundled spec when no URL is provided", async () => {
      const catalog = await loadCatalog("");
      assert.equal(catalog.source(), "bundled-spec");
      assert.ok(catalog.operations().length > 0);
    });
  });
});
