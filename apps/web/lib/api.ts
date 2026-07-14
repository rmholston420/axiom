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
  type?: string;
  label?: string;
  name?: string;
  title?: string;
  question?: string;
  summary?: string;
  text?: string;
  url?: string;
  properties?: Record<string, unknown>;
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
  raw?: Record<string, unknown>;
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

function asArray<T>(value: unknown, candidateKeys: string[]): T[] {
  if (Array.isArray(value)) return value as T[];

  if (value && typeof value === "object") {
    const obj = value as Record<string, unknown>;
    for (const key of candidateKeys) {
      if (Array.isArray(obj[key])) return obj[key] as T[];
    }
  }

  return [];
}

function truncate(value: string, max = 72): string {
  const s = value.replace(/\s+/g, " ").trim();
  return s.length > max ? `${s.slice(0, max - 1)}…` : s;
}

function hostnameFromUrl(value: string): string | null {
  try {
    return new URL(value).hostname.replace(/^www\./, "");
  } catch {
    return null;
  }
}

function fallbackLabel(nodeType: string): string {
  const t = nodeType.toLowerCase();
  if (t === "query") return "Research question";
  if (t === "finding") return "Finding";
  if (t === "source") return "Source";
  return "Graph node";
}

function graphNodeLabel(node: ApiGraphNode): string {
  const props = node.properties ?? {};
  const nodeType = String(node.type ?? props.type ?? "Node");

  const directQuestion =
    node.question ??
    (typeof props.question === "string" ? props.question : undefined);

  const directTitle =
    node.title ??
    (typeof props.title === "string" ? props.title : undefined);

  const directSummary =
    node.summary ??
    (typeof props.summary === "string" ? props.summary : undefined);

  const directText =
    node.text ??
    (typeof props.text === "string" ? props.text : undefined);

  const directName =
    node.name ??
    (typeof props.name === "string" ? props.name : undefined);

  const directLabel =
    node.label ??
    (typeof props.label === "string" ? props.label : undefined);

  const directUrl =
    node.url ??
    (typeof props.url === "string" ? props.url : undefined);

  if (nodeType.toLowerCase() === "query") {
    const q = directQuestion || directTitle || directText;
    return truncate(q || fallbackLabel(nodeType), 88);
  }

  if (nodeType.toLowerCase() === "source") {
    const sourceLabel = directTitle || directName || (directUrl ? hostnameFromUrl(directUrl) : null) || directUrl;
    return truncate(sourceLabel || fallbackLabel(nodeType), 72);
  }

  if (nodeType.toLowerCase() === "finding") {
    const findingLabel = directSummary || directText || directTitle || directLabel || directName;
    return truncate(findingLabel || fallbackLabel(nodeType), 88);
  }

  const generic = directTitle || directName || directLabel || directSummary || directText || directQuestion || directUrl || node.id;
  return truncate(generic || fallbackLabel(nodeType), 72);
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
  if (data.axiomatizer_enabled !== undefined) out.axiom_axiomatizer_enabled = data.axiom_axiomatizer_enabled;
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

  const nodesPayload = await parseJson<unknown>(nodesRes, "fetchGraph nodes");
  const edgesPayload = await parseJson<unknown>(edgesRes, "fetchGraph edges");

  const nodesRaw = asArray<ApiGraphNode>(nodesPayload, ["nodes", "items", "data", "results"]);
  const edgesRaw = asArray<ApiGraphEdge>(edgesPayload, ["edges", "links", "items", "data", "results"]);

  const nodes: GraphNode[] = nodesRaw.map((n) => ({
    id: String(n.id),
    label: graphNodeLabel(n),
    type: String(n.type ?? (n.properties?.type as string | undefined) ?? "Node"),
    raw: (n.properties ?? n) as Record<string, unknown>,
  }));

  const links: GraphLink[] = edgesRaw
    .map((e) => {
      const source = typeof e.source === "string" ? e.source : e.source?.id;
      const target = typeof e.target === "string" ? e.target : e.target?.id;
      if (!source || !target) return null;
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
