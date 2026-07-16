import fs from "node:fs";
import path from "node:path";
import process from "node:process";

const root = process.cwd();

const routePath = path.join(root, "apps/web/app/api/council/route.ts");
const helperPath = path.join(root, "apps/web/lib/server-api.ts");

const routeText = fs.readFileSync(routePath, "utf8");
const helperText = fs.readFileSync(helperPath, "utf8");

function assert(condition, message) {
  if (!condition) {
    console.error(`FAIL: ${message}`);
    process.exit(1);
  }
}

assert(
  routeText.includes('export const runtime = "nodejs";'),
  'council route must force Node.js runtime',
);

assert(
  routeText.includes("export const maxDuration = 300;"),
  "council route must declare maxDuration = 300",
);

assert(
  routeText.includes('forwardJsonBody(req, "/council", "POST", 290000)'),
  "council route must pass the 290000ms timeout override",
);

assert(
  helperText.includes("timeoutMs = REQUEST_TIMEOUT_MS"),
  "server-api helper must support a timeout override parameter",
);

assert(
  helperText.includes("timeout_ms: timeoutMs"),
  "server-api helper must expose timeout_ms in timeout error responses",
);

console.log("PASS: council web proxy timeout regression checks");
