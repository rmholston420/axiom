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

  test("shows loading state or loaded sections", async ({ page }) => {
    await page.goto("/settings");
    const loading = page.getByText("Loading settings...");
    const modelsHeading = page.getByRole("heading", { name: "Models" });
    const runtimeHeading = page.getByRole("heading", { name: "Runtime" });

    if (await loading.isVisible()) {
      await expect(loading).toBeVisible();
    } else {
      await expect(modelsHeading).toBeVisible();
      await expect(runtimeHeading).toBeVisible();
    }
  });
});
