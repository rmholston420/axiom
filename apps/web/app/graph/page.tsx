import GraphClient from "./GraphClient";
import type { AxiomRecord, GraphData, WikiPageStub } from "@/lib/api";

export const dynamic = "force-dynamic";

async function fetchJson<T>(url: string): Promise<T> {
  const res = await fetch(url, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Failed to fetch ${url}: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

export default async function GraphPage() {
  const apiBase =
    process.env.API_BASE_URL ||
    process.env.NEXT_PUBLIC_API_BASE_URL ||
    "http://127.0.0.1:7200";

  let initialGraph: GraphData = { nodes: [], links: [] };
  let initialAxioms: AxiomRecord[] = [];
  let initialWikiPages: WikiPageStub[] = [];

  try {
    const [graph, axioms, wikiPages] = await Promise.all([
      fetchJson<GraphData>(`${apiBase}/graph`),
      fetchJson<AxiomRecord[]>(`${apiBase}/axiomatizer/axioms?limit=25`),
      fetchJson<WikiPageStub[]>(`${apiBase}/wiki/pages?limit=10`),
    ]);

    initialGraph = graph;
    initialAxioms = axioms;
    initialWikiPages = wikiPages;
  } catch (error) {
    console.error("[graph/page] initial fetch failed", error);
  }

  return (
    <GraphClient
      initialGraph={initialGraph}
      initialAxioms={initialAxioms}
      initialWikiPages={initialWikiPages}
    />
  );
}
