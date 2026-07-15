import { test, expect } from "@playwright/test";

test.describe("Settings page", () => {
  test("renders settings heading and description", async ({ page }) => {
    await page.goto("/settings");
    await expect(page.getByRole("heading", { name: "Settings" })).toBeVisible();
    await expect(page.getByText("Runtime defaults and model selection.")).toBeVisible();
  });

  test("renders Save button", async ({ page }) => {
    await page.goto("/settings");
    await expect(page.getByRole("button", { name: /Save|Saving\.\.\.|Saved/ })).toBeVisible();
  });

  test("renders model labels and runtime fields", async ({ page }) => {
    await page.goto("/settings");
    await expect(page.getByText("Planner")).toBeVisible();
    await expect(page.getByText("Synthesizer")).toBeVisible();
    await expect(page.getByText("Code")).toBeVisible();
    await expect(page.getByText("Critic")).toBeVisible();
    await expect(page.getByText("Chairman")).toBeVisible();
    await expect(page.getByText("Axiomatizer")).toBeVisible();
    await expect(page.getByText("Breadth")).toBeVisible();
    await expect(page.getByText("Depth")).toBeVisible();
    await expect(page.getByText("Max results / query")).toBeVisible();
    await expect(page.getByText("Council size")).toBeVisible();
    await expect(page.getByText("Council enabled")).toBeVisible();
    await expect(page.getByText("Axiomatizer enabled")).toBeVisible();
  });
});
