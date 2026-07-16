/**
 * useResearchStream — React hook for Perplexity-style live streaming.
 *
 * Features
 * --------
 * - Opens an EventSource to /api/jobs/{jobId}/stream
 * - Accumulates response.output_text.delta tokens into a smooth text buffer
 * - Flushes the buffer to React state in 40 ms ticks to avoid character-by-
 *   character jitter while still feeling live
 * - Tracks sources arriving via response.sources events
 * - Pins the scroll position only when the user is already near the bottom
 * - Handles reconnects automatically (browser EventSource retries); dedupes
 *   chunks via Last-Event-ID which the browser sends automatically
 * - Closes the connection on terminal events (response.completed / error)
 */
"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { type SourceItem, parseResearchStreamEvent } from "./researchStream";

export type StreamPhase =
  | "idle"
  | "created"
  | "searching"
  | "generating"
  | "done"
  | "error";

export interface ResearchStreamState {
  phase: StreamPhase;
  /** Accumulated answer text rendered as Markdown. */
  text: string;
  /** Current search query being executed (if any). */
  currentQuery: string | null;
  /** All sources collected so far. */
  sources: SourceItem[];
  /** Terminal error message, if any. */
  errorMessage: string | null;
  /** Finding count from the completed event. */
  findingCount: number | null;
}

const INITIAL_STATE: ResearchStreamState = {
  phase: "idle",
  text: "",
  currentQuery: null,
  sources: [],
  errorMessage: null,
  findingCount: null,
};

/** How often (ms) the buffer is flushed to React state. */
const FLUSH_INTERVAL_MS = 40;

/** User is considered "near bottom" when within this many px. */
const SCROLL_THRESHOLD_PX = 120;

export function useResearchStream(
  jobId: string | null,
  apiBase = "",
): ResearchStreamState {
  const [state, setState] = useState<ResearchStreamState>(INITIAL_STATE);

  // Pending text deltas accumulate here between flush ticks.
  const pendingBuffer = useRef("");
  // Full accumulated text (source of truth, not React state).
  const fullText = useRef("");
  const flushTimer = useRef<ReturnType<typeof setInterval> | null>(null);
  const esRef = useRef<EventSource | null>(null);

  const stopFlush = useCallback(() => {
    if (flushTimer.current !== null) {
      clearInterval(flushTimer.current);
      flushTimer.current = null;
    }
  }, []);

  const startFlush = useCallback(() => {
    if (flushTimer.current !== null) return;
    flushTimer.current = setInterval(() => {
      if (pendingBuffer.current === "") return;
      const chunk = pendingBuffer.current;
      pendingBuffer.current = "";
      fullText.current += chunk;
      setState((prev) => ({ ...prev, text: fullText.current, phase: "generating" }));
    }, FLUSH_INTERVAL_MS);
  }, []);

  const close = useCallback(() => {
    stopFlush();
    if (esRef.current) {
      esRef.current.close();
      esRef.current = null;
    }
  }, [stopFlush]);

  useEffect(() => {
    if (!jobId) {
      setState(INITIAL_STATE);
      return;
    }

    // Reset for the new job.
    setState(INITIAL_STATE);
    fullText.current = "";
    pendingBuffer.current = "";

    const url = `${apiBase}/api/jobs/${jobId}/stream`;
    const es = new EventSource(url);
    esRef.current = es;

    es.onmessage = (event: MessageEvent<string>) => {
      const parsed = parseResearchStreamEvent(event.data);
      if (!parsed) return;

      switch (parsed.event) {
        case "response.created":
          setState((prev) => ({ ...prev, phase: "created" }));
          startFlush();
          break;

        case "response.status":
          // Only update phase if not already further along.
          setState((prev) =>
            prev.phase === "idle" || prev.phase === "created"
              ? { ...prev, phase: "created" }
              : prev,
          );
          break;

        case "response.searching":
          setState((prev) => ({
            ...prev,
            phase: prev.phase === "idle" ? "searching" : prev.phase,
            currentQuery: parsed.data.query,
          }));
          break;

        case "response.sources": {
          const incoming = parsed.data.sources ?? [];
          setState((prev) => ({
            ...prev,
            sources: dedupeByUrl([...prev.sources, ...incoming]),
          }));
          break;
        }

        case "response.output_text.delta":
          // Accumulate in buffer — flushed by the interval tick.
          pendingBuffer.current += parsed.data.delta;
          break;

        case "response.output_text.completed":
          // Force-flush everything so the final state is exactly right.
          stopFlush();
          fullText.current = parsed.data.text;
          pendingBuffer.current = "";
          setState((prev) => ({ ...prev, text: fullText.current, phase: "generating" }));
          break;

        case "response.completed":
          stopFlush();
          // Use the authoritative report from the completed event if available.
          if (parsed.data.report) {
            fullText.current = parsed.data.report;
          }
          setState((prev) => ({
            ...prev,
            text: fullText.current,
            phase: "done",
            currentQuery: null,
            findingCount: parsed.data.finding_count ?? prev.findingCount,
          }));
          close();
          break;

        case "error":
          stopFlush();
          setState((prev) => ({
            ...prev,
            phase: "error",
            errorMessage: parsed.data.message ?? "Unknown error",
          }));
          close();
          break;

        default:
          break;
      }
    };

    es.onerror = () => {
      // EventSource will retry automatically.  Only mark error if the
      // connection has been closed without a terminal event.
      if (es.readyState === EventSource.CLOSED) {
        setState((prev) =>
          prev.phase !== "done" && prev.phase !== "error"
            ? { ...prev, phase: "error", errorMessage: "Connection lost" }
            : prev,
        );
      }
    };

    return () => {
      close();
    };
  }, [jobId, apiBase, close, startFlush, stopFlush]);

  return state;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function dedupeByUrl(sources: SourceItem[]): SourceItem[] {
  const seen = new Set<string>();
  return sources.filter((s) => {
    if (seen.has(s.url)) return false;
    seen.add(s.url);
    return true;
  });
}

/**
 * scrollPinned — call this inside a scroll handler or a ResizeObserver on
 * the answer container.  Returns true when the viewport should auto-scroll.
 */
export function isScrollPinned(container: HTMLElement): boolean {
  const { scrollTop, scrollHeight, clientHeight } = container;
  return scrollHeight - scrollTop - clientHeight < SCROLL_THRESHOLD_PX;
}
