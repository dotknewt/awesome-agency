#!/usr/bin/env node

import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { loadCatalog } from "./catalog.js";
import { LudusClient } from "./client.js";
import { createMcpServer } from "./server.js";

// ── CLI argument parsing ──────────────────────────────────────────────

function parseArgs(): { url: string; apiKey: string } {
  const args = process.argv.slice(2);

  let url = process.env.LUDUS_URL ?? "";
  let apiKey = process.env.LUDUS_API_KEY ?? "";

  for (let i = 0; i < args.length; i++) {
    if (args[i] === "--url" && i + 1 < args.length) {
      url = args[++i];
    } else if (args[i] === "--api-key" && i + 1 < args.length) {
      apiKey = args[++i];
    }
  }

  if (!url) {
    console.error(
      "Error: Ludus URL is required. Use --url <url> or set LUDUS_URL environment variable.",
    );
    process.exit(1);
  }

  if (!apiKey) {
    console.error(
      "Error: Ludus API key is required. Use --api-key <key> or set LUDUS_API_KEY environment variable.",
    );
    process.exit(1);
  }

  return { url: url.replace(/\/+$/, ""), apiKey };
}

// ── Main ──────────────────────────────────────────────────────────────

async function main(): Promise<void> {
  const { url, apiKey } = parseArgs();

  // Load bundled catalog immediately so the server can start accepting
  // requests right away. Then try to upgrade to the remote spec in the
  // background.
  let catalog = await loadCatalog("", apiKey);

  const client = new LudusClient(url, apiKey);
  const specUrl = `${url}/api/v2/openapi`;
  const refreshCatalog = () => loadCatalog(specUrl, apiKey);
  const { server, updateCatalog } = createMcpServer(
    catalog,
    client,
    refreshCatalog,
  );

  const transport = new StdioServerTransport();
  await server.connect(transport);

  console.error(
    `ludus-mcp started (catalog: ${catalog.source()}, operations: ${catalog.operations().length})`,
  );

  // Try to upgrade to the remote spec after the server is connected.
  try {
    const remoteCatalog = await refreshCatalog();
    updateCatalog(remoteCatalog);
    console.error(
      `ludus-mcp catalog upgraded (source: ${remoteCatalog.source()}, operations: ${remoteCatalog.operations().length})`,
    );
  } catch (err) {
    console.error(
      `Warning: Could not fetch remote spec from ${specUrl}: ${err instanceof Error ? err.message : String(err)}. Using bundled spec.`,
    );
  }
}

main().catch((err) => {
  console.error("Fatal error:", err);
  process.exit(1);
});
