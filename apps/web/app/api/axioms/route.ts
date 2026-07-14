import { NextResponse } from "next/server";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:7200";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const limit = searchParams.get("limit") ?? "25";

  try {
    const response = await fetch(
      `${API_BASE}/axiomatizer/axioms?limit=${encodeURIComponent(limit)}`,
      { cache: "no-store" },
    );

    const text = await response.text();

    return new NextResponse(text, {
      status: response.status,
      headers: { "content-type": "application/json" },
    });
  } catch (error) {
    return NextResponse.json(
      {
        detail: "Failed to fetch axioms",
        error: error instanceof Error ? error.message : String(error),
      },
      { status: 502 },
    );
  }
}
