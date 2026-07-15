import type { Page } from "@playwright/test";

export async function openDashboard(page: Page) {
  await page.goto("/");
}

export async function openGraph(page: Page) {
  await page.goto("/graph");
}

export async function openSettings(page: Page) {
  await page.goto("/settings");
}

export function navDashboard(page: Page) {
  return page.getByRole("link", { name: "Dashboard" });
}

export function navGraph(page: Page) {
  return page.getByRole("link", { name: "Graph" });
}

export function navSettings(page: Page) {
  return page.getByRole("link", { name: "Settings" });
}

export function dashboardHeading(page: Page) {
  return page.getByRole("heading", { name: "Dashboard" });
}

export function dashboardQueryInput(page: Page) {
  return page.getByPlaceholder("Ask a research question…");
}

export function dashboardRunButton(page: Page) {
  return page.getByRole("button", { name: /Run|Queuing…/ });
}

export function graphHeading(page: Page) {
  return page.getByRole("heading", { name: "Graph" });
}

export function graph2DButton(page: Page) {
  return page.getByRole("button", { name: /2D/ });
}

export function graph3DButton(page: Page) {
  return page.getByRole("button", { name: /3D/ });
}

export function graphRefreshButton(page: Page) {
  return page.getByRole("button", { name: /Refresh/ });
}

export function settingsHeading(page: Page) {
  return page.getByRole("heading", { name: "Settings" });
}

export function settingsSaveButton(page: Page) {
  return page.getByRole("button", { name: /Save|Saving\.\.\.|Saved/ });
}

export function settingsLoadingText(page: Page) {
  return page.getByText("Loading settings...");
}

export function settingsModelsHeading(page: Page) {
  return page.getByRole("heading", { name: "Models" });
}

export function settingsRuntimeHeading(page: Page) {
  return page.getByRole("heading", { name: "Runtime" });
}
