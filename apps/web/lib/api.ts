export type JobStatus = "queued" | "running" | "done" | "error" | string;

export interface Job {
  id: string;
  query?: string;
  question?: string;
  status: JobStatus;
  created_at: string;
  updated_at: string;
  report?: string;
  error?: string;
}

export interface GraphNode {
  id: string;
  label?: string;
  type?: string;
  group?: string;
}

export interface GraphLink {
  source: string;
  target: string;
  type?: string;
  label?: string;
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

async function parseJsonResponse(res: Response) {
  const text = await res.text();
  try {
    return text ? JSON.parse(text) : {};
  } catch {
    throw new Error(`${res.status} ${text}`);
  }
}

async function getJson(path: string) {
  const res = await fetch(path, { cache: "no-store" });
  const data = await parseJsonResponse(res);
  if (!res.ok) {
    throw new Error(`${res.status} ${JSON.stringify(data)}`);
  }
  return data;
}

export async function fetchJobs(): Promise<Job[]> {
  const data = await getJson("/api/jobs");
  return Array.isArray(data) ? data : [];
}

export async function fetchJob(id: string): Promise<Job> {
  return getJson(`/api/jobs/${id}`);
}

export async function createJob(question: string): Promise<Job> {
  return fetch("/api/jobs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  }).then(async (res) => {
    const data = await parseJsonResponse(res);
    if (!res.ok) {
      throw new Error(`createJob: ${res.status} ${JSON.stringify(data)}`);
    }
    return data;
  });
}

export async function fetchGraph(): Promise<GraphData> {
  return getJson("/api/graph");
}

type RawSettings = {
  axiom_model_planner?: string;
  axiom_model_synthesizer?: string;
  axiom_model_code?: string;
  axiom_model_critic?: string;
  axiom_breadth?: number;
  axiom_depth?: number;
  axiom_max_results_per_query?: number;
  axiom_council_enabled?: boolean;
  axiom_axiomatizer_enabled?: boolean;
};

function normalizeSettings(raw: RawSettings): SettingsData {
  return {
    model_planner: raw.axiom_model_planner ?? "",
    model_synthesizer: raw.axiom_model_synthesizer ?? "",
    model_code: raw.axiom_model_code ?? "",
    model_critic: raw.axiom_model_critic ?? "",
    breadth: raw.axiom_breadth ?? 4,
    depth: raw.axiom_depth ?? 3,
    max_results_per_query: raw.axiom_max_results_per_query ?? 5,
    council_enabled: raw.axiom_council_enabled ?? true,
    axiomatizer_enabled: raw.axiom_axiomatizer_enabled ?? false,
  };
}

export async function fetchSettings(): Promise<SettingsData> {
  const raw = await getJson("/api/settings");
  return normalizeSettings(raw);
}

export async function saveSettings(data: Partial<SettingsData>): Promise<SettingsData> {
  const payload = {
    axiom_model_planner: data.model_planner,
    axiom_model_synthesizer: data.model_synthesizer,
    axiom_model_code: data.model_code,
    axiom_model_critic: data.model_critic,
    axiom_breadth: data.breadth,
    axiom_depth: data.depth,
    axiom_max_results_per_query: data.max_results_per_query,
    axiom_council_enabled: data.council_enabled,
    axiom_axiomatizer_enabled: data.axiomatizer_enabled,
  };

  const res = await fetch("/api/settings", {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const raw = await parseJsonResponse(res);
  if (!res.ok) {
    throw new Error(`saveSettings: ${res.status} ${JSON.stringify(raw)}`);
  }
  return normalizeSettings(raw);
}

export async function fetchModels(): Promise<string[]> {
  const raw = await getJson("/api/models");
  const models = Array.isArray(raw?.models) ? raw.models : [];
  return models.map((m: unknown) => {
    if (typeof m === "string") return m;
    if (m && typeof m === "object" && "name" in m) {
      const name = (m as { name?: unknown }).name;
      return typeof name === "string" ? name : "";
    }
    return "";
  }).filter(Boolean);
}
