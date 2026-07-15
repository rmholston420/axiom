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

  test("accepts query text input", async ({ page }) => {
    await page.goto("/");
    const input = page.getByPlaceholder("Ask a research question…");
    await input.fill("Test research question");
    await expect(input).toHaveValue("Test research question");
  });

  test("shows empty queue state when there are no jobs", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { name: "Queue" })).toBeVisible();
    await expect(page.getByText("No jobs yet.")).toBeVisible();
  });

  test("shows idle dashboard prompt before a job is selected", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByText("Submit a query or select a job to see output.")).toBeVisible();
  });
});
