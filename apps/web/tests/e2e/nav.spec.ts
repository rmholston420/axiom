import { test, expect } from "@playwright/test";

test.describe("Navigation", () => {
  test("renders all primary nav links", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("link", { name: "Dashboard" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Graph" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Settings" })).toBeVisible();
  });

  test("navigates to Graph when clicking nav link", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("link", { name: "Graph" }).click();
    await expect(page.getByRole("heading", { name: "Graph" })).toBeVisible();
  });

  test("navigates to Settings when clicking nav link", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("link", { name: "Settings" }).click();
    await expect(page.getByRole("heading", { name: "Settings" })).toBeVisible();
  });
});
