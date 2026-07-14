export const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:7200";

export type JobStatus = "queued" | "running" | "done" | "error";

export interface Job {
  id: string;
  query: string;
  status: JobStatus;
  created_at: string;
  updated_at: string;
  report?: string;
  error?: string;
}

export interface GraphNode {
  id: string;
  label: string;
  type: string;
}

export interface GraphLink {
  source: string;
  target: string;
  type: string;
}

export interface GraphData {
  nodes: GraphNode[];
  links: GraphLink[];
}

export interface SettingsData {
  model_planner: string;
  model_synthesizer: string;
  model_code: string;
  model_critic: string;
  breadth: number;
  depth: number;
  max_results_per_query: number;
  council_enabled: boolean;
  axiomatizer_enabled: boolean;
}

async function parseJson<T>(res: Response, label: string): Promise<T> {
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${label}: ${res.status} ${text}`);
  }
  return res.json() as Promise<T>;
}

export async function fetchJobs(): Promise<Job[]> {
  const res = await fetch(`${API_BASE}/jobs`, { cache: "no-store" });
  return parseJson<Job[]>(res, "fetchJobs");
}

export async function fetchJob(id: string): Promise<Job> {
  const res = await fetch(`${API_BASE}/jobs/${id}`, { cache: "no-store" });
  return parseJson<Job>(res, "fetchJob");
}

export async function createJob(query: string): Promise<Job> {
  const res = await fetch(`${API_BASE}/jobs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query }),
  });
  return parseJson<Job>(res, "createJob");
}

export async function fetchGraph(): Promise<GraphData> {
  const res = await fetch(`${API_BASE}/graph`, { cache: "no-store" });
  return parseJson<GraphData>(res, "fetchGraph");
}

export async function fetchSettings(): Promise<SettingsData> {
  const res = await fetch(`${API_BASE}/settings`, { cache: "no-store" });
  return parseJson<SettingsData>(res, "fetchSettings");
}

export async function saveSettings(data: Partial<SettingsData>): Promise<SettingsData> {
  const res = await fetch(`${API_BASE}/settings`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  return parseJson<SettingsData>(res, "saveSettings");
}

export async function fetchModels(): Promise<string[]> {
  const res = await fetch(`${API_BASE}/models`, { cache: "no-store" });
  if (!res.ok) return [];
  const data = (await res.json()) as { models?: string[] };
  return data.models ?? [];
}
