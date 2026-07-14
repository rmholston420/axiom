export const API_BASE = "/api";

export type JobStatus = "queued" | "running" | "done" | "error";

type ApiJob = {
  id: string;
  question: string;
  status: JobStatus;
  created_at: string;
  updated_at: string;
  report?: string;
  error?: string;
};

export interface Job {
  id: string;
  query: string;
  status: JobStatus;
  created_at: string;
  updated_at: string;
  report?: string;
  error?: string;
}

type ApiGraphNode = {
  id: string;
  label?: string;
  type?: string;
  name?: string;
};

type ApiGraphEdge = {
  source: string | { id?: string };
  target: string | { id?: string };
  type?: string;
  label?: string;
};

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

type ApiSettings = {
  axiom_breadth: number;
  axiom_depth: number;
  axiom_max_results_per_query: number;
  axiom_council_size?: number;
  axiom_council_enabled: boolean;
  axiom_axiomatizer_enabled: boolean;
  axiom_model_planner: string;
  axiom_model_synthesizer: string;
  axiom_model_code: string;
  axiom_model_critic: string;
  axiom_model_chairman?: string;
  axiom_model_axiomatizer?: string;
};

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

export interface ModelOption {
  value: string;
  label: string;
}

async function parseJson<T>(res: Response, label: string): Promise<T> {
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${label}: ${res.status} ${text}`);
  }
  return res.json() as Promise<T>;
}

function mapJob(job: ApiJob): Job {
  return {
    id: job.id,
    query: job.question,
    status: job.status,
    created_at: job.created_at,
    updated_at: job.updated_at,
    report: job.report,
    error: job.error,
  };
}

function mapSettings(data: ApiSettings): SettingsData {
  return {
    model_planner: data.axiom_model_planner,
    model_synthesizer: data.axiom_model_synthesizer,
    model_code: data.axiom_model_code,
    model_critic: data.axiom_model_critic,
    breadth: data.axiom_breadth,
    depth: data.axiom_depth,
    max_results_per_query: data.axiom_max_results_per_query,
    council_enabled: data.axiom_council_enabled,
    axiomatizer_enabled: data.axiom_axiomatizer_enabled,
  };
}

function unmapSettings(data: Partial<SettingsData>): Partial<ApiSettings> {
  const out: Partial<ApiSettings> = {};
  if (data.model_planner !== undefined) out.axiom_model_planner = data.model_planner;
  if (data.model_synthesizer !== undefined) out.axiom_model_synthesizer = data.model_synthesizer;
  if (data.model_code !== undefined) out.axiom_model_code = data.model_code;
  if (data.model_critic !== undefined) out.axiom_model_critic = data.model_critic;
  if (data.breadth !== undefined) out.axiom_breadth = data.breadth;
  if (data.depth !== undefined) out.axiom_depth = data.depth;
  if (data.max_results_per_query !== undefined) out.axiom_max_results_per_query = data.max_results_per_query;
  if (data.council_enabled !== undefined) out.axiom_council_enabled = data.council_enabled;
  if (data.axiomatizer_enabled !== undefined) out.axiom_axiomatizer_enabled = data.axiomatizer_enabled;
  return out;
}

export async function fetchJobs(): Promise<Job[]> {
  const res = await fetch(`${API_BASE}/jobs`, { cache: "no-store" });
  const data = await parseJson<ApiJob[]>(res, "fetchJobs");
  return data.map(mapJob);
}

export async function fetchJob(id: string): Promise<Job> {
  const res = await fetch(`${API_BASE}/jobs/${id}`, { cache: "no-store" });
  const data = await parseJson<ApiJob>(res, "fetchJob");
  return mapJob(data);
}

export async function createJob(query: string): Promise<Job> {
  const res = await fetch(`${API_BASE}/jobs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question: query }),
  });
  const data = await parseJson<ApiJob>(res, "createJob");
  return mapJob(data);
}

export async function fetchGraph(): Promise<GraphData> {
  const [nodesRes, edgesRes] = await Promise.all([
    fetch(`${API_BASE}/graph/nodes`, { cache: "no-store" }),
    fetch(`${API_BASE}/graph/edges`, { cache: "no-store" }),
  ]);

  const nodesRaw = await parseJson<ApiGraphNode[]>(nodesRes, "fetchGraph nodes");
  const edgesRaw = await parseJson<ApiGraphEdge[]>(edgesRes, "fetchGraph edges");

  const nodes: GraphNode[] = nodesRaw.map((n) => ({
    id: String(n.id),
    label: String(n.label ?? n.name ?? n.id),
    type: String(n.type ?? "Node"),
  }));

  const links: GraphLink[] = edgesRaw
    .map((e) => {
      const source = typeof e.source === "string" ? e.source : e.source?.id;
      const target = typeof e.target === "string" ? e.target : e.target?.id;
      if (!source || !target) return null
      return {
        source: String(source),
        target: String(target),
        type: String(e.type ?? e.label ?? "RELATED"),
      };
    })
    .filter((x): x is GraphLink => Boolean(x));

  return { nodes, links };
}

export async function fetchSettings(): Promise<SettingsData> {
  const res = await fetch(`${API_BASE}/settings`, { cache: "no-store" });
  const data = await parseJson<ApiSettings>(res, "fetchSettings");
  return mapSettings(data);
}

export async function saveSettings(data: Partial<SettingsData>): Promise<SettingsData> {
  const res = await fetch(`${API_BASE}/settings`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(unmapSettings(data)),
  });
  const result = await parseJson<ApiSettings>(res, "saveSettings");
  return mapSettings(result);
}

function normalizeModel(item: unknown): ModelOption | null {
  if (typeof item === "string") {
    return { value: item, label: item };
  }

  if (item && typeof item === "object") {
    const obj = item as Record<string, unknown>;
    const value =
      (typeof obj.name === "string" && obj.name) ||
      (typeof obj.model === "string" && obj.model) ||
      (typeof obj.id === "string" && obj.id) ||
      null;

    if (!value) return null;

    const size =
      typeof obj.size === "number"
        ? ` (${Math.round(obj.size / 1024 / 1024 / 1024)} GB)`
        : "";

    return { value, label: `${value}${size}` };
  }

  return null;
}

export async function fetchModels(): Promise<ModelOption[]> {
  const res = await fetch(`${API_BASE}/models`, { cache: "no-store" });
  if (!res.ok) return [];

  const data = (await res.json()) as { models?: unknown[] } | unknown[];
  const raw = Array.isArray(data) ? data : Array.isArray(data.models) ? data.models : [];

  return raw
    .map(normalizeModel)
    .filter((item): item is ModelOption => Boolean(item));
}
