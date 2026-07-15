import { test, expect } from "@playwright/test";
import {
  openSettings,
  settingsHeading,
  settingsLoadingText,
  settingsModelsHeading,
  settingsRuntimeHeading,
  settingsSaveButton,
} from "./helpers";

test.describe("Settings page", () => {
  test("renders settings heading and description", async ({ page }) => {
    await openSettings(page);
    await expect(settingsHeading(page)).toBeVisible();
    await expect(page.getByText("Runtime defaults and model selection.")).toBeVisible();
  });

  test("renders Save button", async ({ page }) => {
    await openSettings(page);
    await expect(settingsSaveButton(page)).toBeVisible();
  });

  test("shows loading state or loaded sections", async ({ page }) => {
    await openSettings(page);
    const loading = settingsLoadingText(page);
    const modelsHeading = settingsModelsHeading(page);
    const runtimeHeading = settingsRuntimeHeading(page);

    if (await loading.isVisible()) {
      await expect(loading).toBeVisible();
    } else {
      await expect(modelsHeading).toBeVisible();
      await expect(runtimeHeading).toBeVisible();
    }
  });
});
