const isBrowser = typeof window !== "undefined";

export const API_BASE =
  (isBrowser ? "/api" : (process.env.API_ORIGIN ?? "http://axiom-api:7200"));


export type FindingResult = {
  url?: string;
  title?: string;
  snippet?: string;
};

export type Finding = {
  index?: number;
  sub_query?: string;
  summary?: string;
  results?: FindingResult[];
};

export type JobStatus = "queued" | "running" | "done" | "error";

export interface JobReference {
  title?: string;
  url?: string;
  snippet?: string;
}

export interface Job {
  id: string;
  query: string;
  question?: string;
  status: JobStatus;
  created_at: string;
  updated_at: string;
  started_at?: string;
  completed_at?: string;
  elapsed_seconds?: number | null;
  query_id?: string;
  axiom_id?: string;
  report?: string;
  error?: string;
  findings?: Finding[];
  references?: JobReference[];
  sources?: JobReference[];
}

export interface GraphData {
  nodes: { id: string; label: string; type: string }[];
  links: { source: string; target: string; type: string }[];
}

export interface WikiPageStub {
  page_id: string;
  page_type: string;
  title: string;
  slug: string;
  version: number;
  generated_at: string;
}


export interface AxiomRecord {
  id?: string;
  axiom_id?: string;
  label: string;
  statement: string;
  justification: string;
  confidence: number;
  approved?: boolean;
  eval_reason?: string;
  evaluation_warning?: boolean;
  created_at: string;
  persisted?: boolean;
}

export type CouncilMode = "sequential" | "parallel";

export interface CouncilMemberOpinion {
  member_id: number;
  role: string;
  opinion: string;
}

export interface CouncilRequest {
  question: string;
  context?: string;
  council_size?: number;
  mode?: CouncilMode;
}

export interface CouncilResponse {
  question: string;
  mode: CouncilMode;
  members: CouncilMemberOpinion[];
  consensus: string;
  has_disagreement: boolean;
  chairman_synthesis: string;
}

export interface SettingsData {
  axiom_model_planner: string;
  axiom_model_synthesizer: string;
  axiom_model_code: string;
  axiom_model_critic: string;
  axiom_model_chairman: string;
  axiom_model_axiomatizer: string;
  axiom_breadth: number;
  axiom_depth: number;
  axiom_max_results_per_query: number;
  axiom_council_size: number;
  axiom_council_enabled: boolean;
  axiom_axiomatizer_enabled: boolean;
  axiom_graph_node_limit: number;
  axiom_graph_edge_limit: number;
}

async function sleep(ms: number) {
  await new Promise((resolve) => setTimeout(resolve, ms));
}

async function getJson<T>(url: string, init?: RequestInit, retries = 4): Promise<T> {
  let lastErr: unknown;

  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      const res = await fetch(url, {
        ...init,
        cache: "no-store",
        headers: {
          "Content-Type": "application/json",
          ...(init?.headers ?? {}),
        },
      });

      if (!res.ok) {
        throw new Error(`${url} -> ${res.status}`);
      }

      return (await res.json()) as T;
    } catch (err) {
      lastErr = err;
      if (attempt === retries) break;
      await sleep(250 * (attempt + 1));
    }
  }

  throw lastErr instanceof Error ? lastErr : new Error(String(lastErr));
}

export async function fetchJobs(): Promise<Job[]> {
  return getJson<Job[]>(`${API_BASE}/jobs`);
}

export async function fetchJob(id: string): Promise<Job> {
  return getJson<Job>(`${API_BASE}/jobs/${id}`);
}

export async function createJob(query: string): Promise<Job> {
  return getJson<Job>(`${API_BASE}/jobs`, {
    method: "POST",
    body: JSON.stringify({ question: query }),
  }, 1);
}

export async function fetchGraph(): Promise<GraphData> {
  return getJson<GraphData>(`${API_BASE}/graph`);
}

export async function fetchWikiPages(limit = 10): Promise<WikiPageStub[]> {
  const params = new URLSearchParams({ limit: String(limit) });
  return getJson<WikiPageStub[]>(`${API_BASE}/wiki/pages?${params.toString()}`);
}


export async function fetchAxioms(limit = 25): Promise<AxiomRecord[]> {
  return getJson<AxiomRecord[]>(`${API_BASE}/axioms?limit=${encodeURIComponent(String(limit))}`);
}

export async function approveAxiom(id: string, approved: boolean): Promise<{ id: string; approved: boolean }> {
  return getJson<{ id: string; approved: boolean }>(
    `${API_BASE}/axioms/${encodeURIComponent(id)}/approve`,
    { method: "PATCH", body: JSON.stringify({ approved }) },
    1,
  );
}

export async function fetchSettings(): Promise<SettingsData> {
  return getJson<SettingsData>(`${API_BASE}/settings`);
}

export async function saveSettings(data: Partial<SettingsData>): Promise<SettingsData> {
  return getJson<SettingsData>(`${API_BASE}/settings`, {
    method: "PATCH",
    body: JSON.stringify(data),
  }, 1);
}

export async function fetchModels(): Promise<string[]> {
  try {
    const data = await getJson<{ models?: Array<string | { name?: string }> }>(`${API_BASE}/models`);
    return (data.models ?? [])
      .map((m) => (typeof m === "string" ? m : m?.name ?? ""))
      .filter((m): m is string => Boolean(m));
  } catch {
    return [];
  }
}

export async function runCouncil(body: CouncilRequest): Promise<CouncilResponse> {
  return getJson<CouncilResponse>(`${API_BASE}/council`, {
    method: "POST",
    body: JSON.stringify(body),
  }, 1);
}
