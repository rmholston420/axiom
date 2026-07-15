import { test, expect } from "@playwright/test";
import {
  dashboardHeading,
  dashboardQueryInput,
  dashboardRunButton,
  graphHeading,
  openDashboard,
  openGraph,
  openSettings,
  settingsHeading,
  settingsSaveButton,
} from "./helpers";

test.describe("Accessibility basics", () => {
  test("dashboard page has heading and main content", async ({ page }) => {
    await openDashboard(page);

    await expect(dashboardHeading(page)).toBeVisible();
    await expect(dashboardQueryInput(page)).toBeVisible();
    await expect(dashboardRunButton(page)).toBeVisible();
  });

  test("graph page has heading", async ({ page }) => {
    await openGraph(page);

    await expect(graphHeading(page)).toBeVisible();
  });

  test("settings page has heading and Save button", async ({ page }) => {
    await openSettings(page);

    await expect(settingsHeading(page)).toBeVisible();
    await expect(settingsSaveButton(page)).toBeVisible();
  });
});
