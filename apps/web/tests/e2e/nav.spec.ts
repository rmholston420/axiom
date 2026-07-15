import { test, expect } from "@playwright/test";
import { openDashboard, navDashboard, navGraph, navSettings } from "./helpers";

test.describe("Navigation", () => {
  test("renders all primary nav links", async ({ page }) => {
    await openDashboard(page);

    await expect(navDashboard(page)).toBeVisible();
    await expect(navGraph(page)).toBeVisible();
    await expect(navSettings(page)).toBeVisible();
  });

  test("navigates to Graph when clicking nav link", async ({ page }) => {
    await openDashboard(page);

    await navGraph(page).click();
    await expect(page.getByRole("heading", { name: "Graph" })).toBeVisible();
  });

  test("navigates to Settings when clicking nav link", async ({ page }) => {
    await openDashboard(page);

    await navSettings(page).click();
    await expect(page.getByRole("heading", { name: "Settings" })).toBeVisible();
  });
});
