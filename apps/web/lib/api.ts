const isBrowser = typeof window !== "undefined";

export const API_BASE =
  (isBrowser ? "/api" : (process.env.API_ORIGIN ?? "http://axiom-api:7200"));

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
  report?: string;
  error?: string;
  references?: JobReference[];
  sources?: JobReference[];
}

export interface GraphData {
  nodes: { id: string; label: string; type: string }[];
  links: { source: string; target: string; type: string }[];
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
  created_at: string;
  persisted?: boolean;
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

export async function fetchAxioms(limit = 25): Promise<AxiomRecord[]> {
  return getJson<AxiomRecord[]>(`${API_BASE}/axioms?limit=${encodeURIComponent(String(limit))}`);
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
