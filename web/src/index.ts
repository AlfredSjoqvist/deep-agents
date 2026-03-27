/**
 * Sentinel Dashboard — Bun HTTP server.
 * Serves static files from web/src/ on port 3001.
 */

import { readFileSync, existsSync } from "fs";
import { join, extname } from "path";

const SRC_DIR = import.meta.dir; // web/src/
const PORT = 3001;

const MIME_TYPES: Record<string, string> = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".ts": "application/javascript; charset=utf-8",
  ".js": "application/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".png": "image/png",
  ".svg": "image/svg+xml",
  ".ico": "image/x-icon",
};

/**
 * Transpile TypeScript on the fly for browser consumption.
 * Bun's transpiler converts TS to JS so the browser can execute it.
 */
function transpileTS(filePath: string): string {
  const source = readFileSync(filePath, "utf-8");
  const transpiler = new Bun.Transpiler({ loader: "ts" });
  return transpiler.transformSync(source);
}

Bun.serve({
  port: PORT,
  fetch(req) {
    const url = new URL(req.url);
    let pathname = url.pathname;

    // Default route -> index.html
    if (pathname === "/" || pathname === "/index.html") {
      pathname = "/index.html";
    }

    const filePath = join(SRC_DIR, pathname);

    if (!existsSync(filePath)) {
      return new Response("Not Found", { status: 404 });
    }

    const ext = extname(filePath);
    const contentType = MIME_TYPES[ext] || "application/octet-stream";

    // Transpile .ts files to JS for the browser
    if (ext === ".ts") {
      try {
        const js = transpileTS(filePath);
        return new Response(js, {
          headers: {
            "Content-Type": "application/javascript; charset=utf-8",
            "Cache-Control": "no-cache",
          },
        });
      } catch (e) {
        console.error(`Transpile error: ${e}`);
        return new Response(`// Transpile error: ${e}`, {
          status: 500,
          headers: { "Content-Type": "application/javascript" },
        });
      }
    }

    const file = Bun.file(filePath);
    return new Response(file, {
      headers: {
        "Content-Type": contentType,
        "Cache-Control": "no-cache",
      },
    });
  },
});

console.log(`\n  Sentinel Dashboard running at http://localhost:${PORT}\n`);
