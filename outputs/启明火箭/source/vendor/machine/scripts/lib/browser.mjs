// Launch headless Chromium with the GPU on, guarded against magenta frames.
import { existsSync } from 'node:fs'
let pw
try { pw = await import('playwright') } catch {
  try { pw = await import('playwright-core') } catch {
    // Local task adapter: reuse the Codex bundled dependency without installing globally.
    const bundled = process.env.MACHINE_PLAYWRIGHT_MODULE || 'file:///Users/qianqiming/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright/index.mjs'
    try { pw = await import(bundled) } catch { console.error('Needs Playwright. Set MACHINE_PLAYWRIGHT_MODULE to an installed module URL.'); process.exit(2) }
  }
}
import { guardPage } from './guard.mjs'
export async function launch({ width = 1920, height = 1080, scale = 1 } = {}) {
  const args = ['--ignore-gpu-blocklist', '--enable-gpu-rasterization', '--disable-background-timer-throttling', '--disable-renderer-backgrounding']
  if (process.platform === 'darwin') args.push('--use-angle=metal')
  else if (process.platform === 'linux') args.push('--use-angle=vulkan', '--enable-features=Vulkan')
  const installedChrome = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
  const defaultExe = pw.chromium.executablePath()
  const executablePath = process.env.MACHINE_CHROMIUM_EXECUTABLE ||
    (existsSync(defaultExe) ? defaultExe : existsSync(installedChrome) ? installedChrome : undefined)
  const browser = await pw.chromium.launch({ headless: true, args, ...(executablePath ? { executablePath } : {}) })
  const page = guardPage(await browser.newPage({ viewport: { width, height }, deviceScaleFactor: scale }))
  page.on('pageerror', (e) => console.log('PAGE ERROR', e.message.split('\n')[0]))
  page.on('console', (m) => { if (m.type() === 'error' || m.type() === 'warning') console.log('CONSOLE', m.text().slice(0, 1200)) })
  return { browser, page }
}
