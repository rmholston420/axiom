# Web Architecture

This document explains how the `axiom-web` (Next.js) frontend talks to the
`axiom-api` (FastAPI) backend, and records some gotchas that have already
been debugged.

## Overview

The web app and API run as separate containers:

- `axiom-web` — Next.js app, serving on port 7100
- `axiom-api` — FastAPI app, serving on port 7200

The only supported way for the web app to talk to the API is via internal
app routes under `apps/web/app/api/...` using the shared server-side helpers
in `apps/web/lib/server-api.ts`. Direct global rewrites to another origin
have already caused production issues in Docker and should be avoided.

## No global Next.js /api rewrite

Earlier versions used a global rewrite in `apps/web/next.config.ts`:

```ts
const API_ORIGIN = process.env.API_ORIGIN ?? "http://axiom-api:7200";

const nextConfig: NextConfig = {
  output: "standalone",
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${API_ORIGIN}/:path*`,
      },
    ];
  },
};
```

In Docker, this combined with:

```dotenv
API_ORIGIN=http://127.0.0.1:7200
```

caused `/api/*` requests inside the `axiom-web` container to be rewritten
to `http://127.0.0.1:7200`, which is not the API container. That produced
runtime errors like:

> Error: connect ECONNREFUSED 127.0.0.1:7200

Known-good state:

- `apps/web/next.config.ts` only configures `output: "standalone"` and does
  not define any global `/api` rewrites.
- `apps/web/.env.local` for local dev should use the Docker service name:
  ```dotenv
  API_ORIGIN=http://axiom-api:7200
  ```

App routes under `apps/web/app/api` should handle all proxying instead.

## App routes as the web proxy

Each web-facing API endpoint is implemented as a Next app route that calls
the backend via `apps/web/lib/server-api.ts`.

### Axioms

- Route: `apps/web/app/api/axioms/route.ts`
- Public URL: `GET /api/axioms`
- Behavior: forwards to `/axiomatizer/axioms` on `axiom-api`.

### Council

- Public URL: `POST /api/council`
- Behavior: forwards to `/council` on `axiom-api` and may run for ~40s.

### Jobs stream (SSE)

- Route: `apps/web/app/api/jobs/[id]/stream/route.ts`
- Public URL: `GET /api/jobs/{id}/stream`
- Behavior: forwards a `text/event-stream` response from
  `/jobs/{id}/stream` on `axiom-api` to the browser.

These routes use shared helpers such as:

```ts
import { buildUpstreamUrl, fetchUpstream } from "@/lib/server-api";
```

to construct container-safe URLs like:

- `http://axiom-api:7200/axiomatizer/axioms`
- `http://axiom-api:7200/council`
- `http://axiom-api:7200/jobs/{id}/stream`

## Container-safe origins

Inside Docker, `127.0.0.1` refers to the current container, not another
service. To reach `axiom-api` from `axiom-web`, use the service name:

- `API_ORIGIN=http://axiom-api:7200`

Avoid setting `API_ORIGIN` to `http://127.0.0.1:7200` in any Docker-backed
environment.

## Timeouts for long-running requests

The shared helper uses a 90-second timeout:

```ts
const REQUEST_TIMEOUT_MS = 90000;
```

This is required because council requests can take around 40 seconds
end-to-end. Shorter timeouts like 15000 ms caused confirmed 504
`Upstream API timeout` failures through the web proxy.

## Quick validation checklist

After any change touching the web/API boundary, validate:

1. Axioms

   ```bash
   curl -i http://localhost:7100/api/axioms?limit=25
   ```

   Expect `HTTP/1.1 200 OK` with a JSON array, often `[]`.

2. Council

   ```bash
   curl -i http://localhost:7100/api/council \
     -H 'Content-Type: application/json' \
     -d '{"question":"What is rigpa?","mode":"sequential","council_size":3}'
   ```

   Expect `HTTP/1.1 200 OK` and a JSON body within roughly 60–90 seconds.

3. Jobs stream (SSE)

   ```bash
   curl -i -N http://localhost:7100/api/jobs/<job-id>/stream
   ```

   Expect `HTTP/1.1 200 OK` with `content-type: text/event-stream` and
   streamed events such as:

   ```text
   data: {"event": "status", ...}
   data: {"event": "done", ...}
   ```

If any `/api/*` call logs `ECONNREFUSED 127.0.0.1:7200` from `axiom-web`,
check:

- `apps/web/next.config.ts` for reintroduced global rewrites.
- `apps/web/.env.local` or other environment variables for `API_ORIGIN`
  pointing at `127.0.0.1` instead of `axiom-api`.
