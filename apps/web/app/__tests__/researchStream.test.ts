import { describe, expect, it } from "vitest";
import { parseResearchStreamMessage } from "../researchStream";

describe("parseResearchStreamMessage", () => {
  it("parses generic event messages", () => {
    expect(parseResearchStreamMessage(JSON.stringify({ type: "event", message: "hello" }))).toEqual({
      type: "event",
      message: "hello",
    });
  });

  it("parses finding messages", () => {
    expect(
      parseResearchStreamMessage(
        JSON.stringify({
          type: "finding",
          data: { index: 1, sub_query: "foo", summary: "bar" },
        }),
      ),
    ).toEqual({
      type: "finding",
      data: { index: 1, sub_query: "foo", summary: "bar" },
    });
  });

  it("returns null for malformed json", () => {
    expect(parseResearchStreamMessage("not-json")).toBeNull();
  });

  it("returns null for primitive json", () => {
    expect(parseResearchStreamMessage('"hello"')).toBeNull();
    expect(parseResearchStreamMessage("1")).toBeNull();
  });
});
