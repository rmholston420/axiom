import { test, expect } from "@playwright/test";

test.describe("Graph page", () => {
  test("renders graph heading and controls", async ({ page }) => {
    await page.goto("/graph");
    await expect(page.getByRole("heading", { name: "Graph" })).toBeVisible();
    await expect(page.getByRole("button", { name: /2D/ })).toBeVisible();
    await expect(page.getByRole("button", { name: /3D/ })).toBeVisible();
    await expect(page.getByRole("button", { name: /Refresh/ })).toBeVisible();
  });

  test("renders graph KPI labels", async ({ page }) => {
    await page.goto("/graph");
    await expect(page.getByText("Nodes")).toBeVisible();
    await expect(page.getByText("Links")).toBeVisible();
    await expect(page.getByText("Axioms")).toBeVisible();
  });

  test("renders graph legend labels", async ({ page }) => {
    await page.goto("/graph");
    await expect(page.getByText("Query")).toBeVisible();
    await expect(page.getByText("Finding")).toBeVisible();
    await expect(page.getByText("Source")).toBeVisible();
    await expect(page.getByText("Axiom")).toBeVisible();
  });

  test("renders recent axioms panel", async ({ page }) => {
    await page.goto("/graph");
    await expect(page.getByRole("heading", { name: "Recent axioms" })).toBeVisible();
    await expect(page.getByText("Latest persisted axioms from the axiomatizer service.")).toBeVisible();
  });

  test("shows empty axioms state when no axioms are available", async ({ page }) => {
    await page.goto("/graph");
    await expect(page.getByText("No axioms have been persisted yet.")).toBeVisible();
  });
});
