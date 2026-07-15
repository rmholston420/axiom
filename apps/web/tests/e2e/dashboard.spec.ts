import { test, expect } from "@playwright/test";
import { openDashboard, dashboardQueryInput, dashboardRunButton } from "./helpers";

test.describe("Dashboard page", () => {
  test("renders dashboard heading and query form", async ({ page }) => {
    await openDashboard(page);
    await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();
    await expect(dashboardQueryInput(page)).toBeVisible();
    await expect(dashboardRunButton(page)).toBeVisible();
  });

  test("Run button is disabled when query is empty", async ({ page }) => {
    await openDashboard(page);
    await expect(dashboardRunButton(page)).toBeDisabled();
  });

  test("accepts query text input", async ({ page }) => {
    await openDashboard(page);
    const input = dashboardQueryInput(page);
    await input.fill("Test research question");
    await expect(input).toHaveValue("Test research question");
  });

  test("shows empty queue state when there are no jobs", async ({ page }) => {
    await openDashboard(page);
    await expect(page.getByRole("heading", { name: "Queue" })).toBeVisible();
    await expect(page.getByText("No jobs yet.")).toBeVisible();
  });

  test("shows idle dashboard prompt before a job is selected", async ({ page }) => {
    await openDashboard(page);
    await expect(page.getByText("Submit a query or select a job to see output.")).toBeVisible();
  });
});
