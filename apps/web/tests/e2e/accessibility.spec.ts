import { test, expect } from "@playwright/test";

test.describe("Accessibility basics", () => {
  test("dashboard page has heading and main content", async ({ page }) => {
    await page.goto("/");

    // Main page heading
    await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();

    // Input and Run button have accessible roles and names
    await expect(page.getByPlaceholder("Ask a research question…")).toBeVisible();
    await expect(page.getByRole("button", { name: /Run|Queuing…/ })).toBeVisible();
  });

  test("graph page has heading", async ({ page }) => {
    await page.goto("/graph");

    await expect(page.getByRole("heading", { name: "Graph" })).toBeVisible();
  });

  test("settings page has heading and Save button", async ({ page }) => {
    await page.goto("/settings");

    await expect(page.getByRole("heading", { name: "Settings" })).toBeVisible();
    await expect(
      page.getByRole("button", { name: /Save|Saving\.\.\.|Saved/ })
    ).toBeVisible();
  });
});
