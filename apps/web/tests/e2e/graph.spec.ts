import { test, expect } from "@playwright/test";
import { openGraph, graph2DButton, graph3DButton, graphRefreshButton } from "./helpers";

test.describe("Graph page", () => {
  test("renders graph heading and controls", async ({ page }) => {
    await openGraph(page);
    await expect(page.getByRole("heading", { name: "Graph" })).toBeVisible();
    await expect(graph2DButton(page)).toBeVisible();
    await expect(graph3DButton(page)).toBeVisible();
    await expect(graphRefreshButton(page)).toBeVisible();
  });

  test("shows 2D mode instructions by default", async ({ page }) => {
    await openGraph(page);
    await expect(page.getByText("Drag to pan, scroll to zoom, hover nodes to highlight connected links, click to pin details.")).toBeVisible();
  });

  test("can click the 3D mode control", async ({ page }) => {
    await openGraph(page);
    await graph3DButton(page).click();
    await expect(page.getByRole("heading", { name: "Graph" })).toBeVisible();
    await expect(graphRefreshButton(page)).toBeVisible();
  });

  test("can switch back to 2D mode instructions", async ({ page }) => {
    await openGraph(page);
    await graph3DButton(page).click();
    await graph2DButton(page).click();
    await expect(page.getByText("Drag to pan, scroll to zoom, hover nodes to highlight connected links, click to pin details.")).toBeVisible();
  });

  test("renders graph KPI labels", async ({ page }) => {
    await openGraph(page);
    await expect(page.getByText("Nodes", { exact: true })).toBeVisible();
    await expect(page.getByText("Links", { exact: true })).toBeVisible();
    await expect(page.getByText("Axioms", { exact: true })).toBeVisible();
  });

  test("renders graph legend labels", async ({ page }) => {
    await openGraph(page);
    await expect(page.getByText("Query", { exact: true })).toBeVisible();
    await expect(page.getByText("Finding", { exact: true })).toBeVisible();
    await expect(page.getByText("Source", { exact: true })).toBeVisible();
    await expect(page.getByRole("main").getByText("Axiom", { exact: true })).toBeVisible();
  });

  test("renders recent axioms panel", async ({ page }) => {
    await openGraph(page);
    await expect(page.getByRole("heading", { name: "Recent axioms" })).toBeVisible();
    await expect(page.getByText("Latest persisted axioms from the axiomatizer service.")).toBeVisible();
  });

  test("shows empty axioms state when no axioms are available", async ({ page }) => {
    await openGraph(page);
    await expect(page.getByText("No axioms have been persisted yet.")).toBeVisible();
  });
});
