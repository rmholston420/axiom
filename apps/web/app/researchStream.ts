/**
 * researchStream.ts
 *
 * Canonical types for the Axiom semantic SSE event protocol.
 *
 * Lifecycle (in order):
 *   response.created            — job accepted
 *   response.status             — status change (queued → running)
 *   response.searching          — sub-query retrieval started
 *   response.sources            — sources found for a sub-query
 *   response.output_text.delta  — incremental text token
 *   response.output_text.completed — full accumulated report text
 *   response.completed          — terminal success
 *   error                       — terminal failure
 */

export interface SourceItem {
  title: string;
  url: string;
}

export type ResearchStreamEvent =
  | { event: "response.created"; data: { job_id: string } }
  | { event: "response.status"; data: { status: string } }
  | { event: "response.searching"; data: { query: string } }
  | { event: "response.sources"; data: { query: string; sources: SourceItem[] } }
  | { event: "response.output_text.delta"; data: { delta: string } }
  | { event: "response.output_text.completed"; data: { text: string } }
  | {
      event: "response.completed";
      data: {
        status: string;
        report: string;
        finding_count?: number;
        query_id?: string;
        elapsed_seconds?: number | null;
        started_at?: string;
        completed_at?: string;
      };
    }
// Legacy / catch-all for unknown events during rollout
  | { event: string; data: Record<string, unknown> };

/** Parse one SSE data line. Returns null on invalid JSON. */
export function parseResearchStreamEvent(data: string): ResearchStreamEvent | null {
  try {
    const parsed = JSON.parse(data) as unknown;
    if (!parsed || typeof parsed !== "object") return null;
    return parsed as ResearchStreamEvent;
  } catch {
    return null;
  }
}

// ---------------------------------------------------------------------------
// Legacy alias — kept so existing imports don't break during rollout
// ---------------------------------------------------------------------------
export type ResearchStreamMessage = ResearchStreamEvent;
export const parseResearchStreamMessage = parseResearchStreamEvent;
