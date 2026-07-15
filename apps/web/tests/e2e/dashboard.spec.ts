import { test, expect } from "@playwright/test";

test.describe("Dashboard page", () => {
  test("renders dashboard heading and query form", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();
    await expect(page.getByPlaceholder("Ask a research question…")).toBeVisible();
    await expect(page.getByRole("button", { name: /Run|Queuing…/ })).toBeVisible();
  });

  test("Run button is disabled when query is empty", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("button", { name: /Run|Queuing…/ })).toBeDisabled();
  });

  test("Run button enables when query is entered", async ({ page }) => {
    await page.goto("/");
    await page.getByPlaceholder("Ask a research question…").fill("Test research question");
    await expect(page.getByRole("button", { name: /Run|Queuing…/ })).toBeEnabled();
  });
});
