export type ResearchStreamMessage =
  | { type: "event"; message?: unknown }
  | { type: "report"; content?: unknown }
  | { type: "error"; message?: unknown }
  | { type: "finding"; data?: { index?: unknown; sub_query?: unknown; summary?: unknown } }
  | { type: string; [key: string]: unknown };

export function parseResearchStreamMessage(data: string): ResearchStreamMessage | null {
  try {
    const parsed = JSON.parse(data) as unknown;
    if (!parsed || typeof parsed !== "object") return null;
    return parsed as ResearchStreamMessage;
  } catch {
    return null;
  }
}
