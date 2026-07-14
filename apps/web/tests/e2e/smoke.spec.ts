import { test, expect } from "@playwright/test";

test("dashboard renders", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();
});

test("settings renders", async ({ page }) => {
  await page.goto("/settings");
  await expect(page.getByRole("heading", { name: "Settings" })).toBeVisible();
});

test("graph renders", async ({ page }) => {
  await page.goto("/graph");
  await expect(page.getByRole("heading", { name: "Graph" })).toBeVisible();
});
