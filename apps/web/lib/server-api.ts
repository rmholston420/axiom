const DEFAULT_API_ORIGIN = "http://127.0.0.1:7200";
const REQUEST_TIMEOUT_MS = 15000;

function trimSlash(value: string): string {
  return value.replace(/\/+$/, "");
}

export function getApiOrigin(): string {
  const candidates = [
    process.env.API_ORIGIN,
    process.env.AXIOM_API_ORIGIN,
    process.env.NEXT_PUBLIC_API_ORIGIN,
  ].filter((value): value is string => Boolean(value && value.trim()));

  return trimSlash(candidates[0] ?? DEFAULT_API_ORIGIN);
}

export function buildUpstreamUrl(pathname: string, search = ""): string {
  const base = getApiOrigin();
  const normalizedPath = pathname.startsWith("/") ? pathname : `/${pathname}`;
  return `${base}${normalizedPath}${search}`;
}

export async function fetchUpstream(
  pathname: string,
  init?: RequestInit,
  search = "",
): Promise<Response> {
  const url = buildUpstreamUrl(pathname, search);
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  try {
    const upstream = await fetch(url, {
      ...init,
      cache: "no-store",
      signal: controller.signal,
      headers: {
        accept: "application/json, text/plain, */*",
        ...(init?.headers ?? {}),
      },
    });

    const body = await upstream.text();
    const headers = new Headers();
    headers.set(
      "content-type",
      upstream.headers.get("content-type") || "application/json; charset=utf-8",
    );
    headers.set("cache-control", "no-store");

    return new Response(body, {
      status: upstream.status,
      statusText: upstream.statusText,
      headers,
    });
  } catch (error) {
    const detail = error instanceof Error ? error.message : String(error);
    const status =
      error instanceof Error && error.name === "AbortError" ? 504 : 502;

    return Response.json(
      {
        error: status === 504 ? "Upstream API timeout" : "Upstream API unreachable",
        upstream: url,
        detail,
      },
      { status },
    );
  } finally {
    clearTimeout(timeout);
  }
}

export async function forwardJsonBody(
  req: Request,
  pathname: string,
  method: "POST" | "PATCH" | "PUT" | "DELETE",
): Promise<Response> {
  const search = new URL(req.url).search;
  const body = await req.text();

  return fetchUpstream(
    pathname,
    {
      method,
      headers: {
        "content-type": req.headers.get("content-type") || "application/json",
      },
      body,
    },
    search,
  );
}
