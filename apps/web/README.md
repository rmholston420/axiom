# Axiom Web

Axiom Web is the Next.js frontend for the Axiom research workbench.

## Development

Run the web app locally from `apps/web`:

```bash
pnpm dev
```

The app runs on `http://127.0.0.1:3000` by default.

## Frontend tests

The frontend uses Playwright for end-to-end coverage.

Run the full suite:

```bash
pnpm test:e2e
```

Run in headed mode:

```bash
pnpm test:e2e:headed
```

Run in Playwright UI mode:

```bash
pnpm test:e2e:ui
```

## Current test areas

The Playwright suite covers:

- Route smoke checks.
- Primary navigation.
- Dashboard query form and empty or idle states.
- Settings page UI presence.
- Accessibility basics across core routes.
- Graph page UI states.

## Test artifacts

Playwright artifact output is ignored in `apps/web/.gitignore`, including:

- `test-results/`
- `playwright-report/`

## Notes

Playwright is configured in `apps/web/playwright.config.ts` and uses the local Next.js dev server for test runs.
