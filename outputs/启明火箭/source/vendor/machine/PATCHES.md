# Local task adapter

Source: `/Users/qianqiming/Desktop/skill-repos/AirsupHQ--machine-skill`.
The `kit`, `scripts` and `LICENSE` files were copied for an editable, inspectable delivery. The original repository was not changed.

`scripts/lib/browser.mjs` adds a fallback to the existing Codex bundled Playwright installation when normal `playwright` and `playwright-core` imports are unavailable. An environment override, `MACHINE_PLAYWRIGHT_MODULE`, accepts an installed module URL. This is a local runtime adapter; no package is installed globally. The bundle's expected Chromium revision is absent locally, so the adapter falls back to the existing `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome` in a separate headless session with a fresh temporary profile. `MACHINE_CHROMIUM_EXECUTABLE` overrides this executable. It does not control or read the user's existing browser tabs or profile.

The kit's geometry and material implementation is unchanged. The import map in a copied template still uses jsDelivr until the project build replaces or bundles those imports. Film `seek(t)` advances only; reload the page before taking an earlier frame. The original record script's music URL/FreePD options access the network and are unused in this task.
