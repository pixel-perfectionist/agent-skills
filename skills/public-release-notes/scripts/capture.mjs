// Release Note captures from the local stack (scripts/local-stack.sh).
//
//   cd <worktree>/frontend && set -a && . ./.env.local && set +a && \
//     OUT=<dir> PROFILE=<dir> JOB=<job.json> \
//     node --input-type=module -e "$(cat <skill>/scripts/capture.mjs)"
//
// The dev-login key is read from the environment by this process and never
// printed. JOB is a JSON array of steps:
//   {op:"enterCompany", name}              pick a Company on /auth/select-company
//   {op:"goto", url}                       path relative to the local frontend
//   {op:"click", text} | {op:"click", role, name}   visible element only
//   {op:"xy", x, y}                        click at viewport coordinates
//   {op:"wait", ms}
//   {op:"escape"}
//   {op:"highlight", target}               outline the changed element
//   {op:"shot", name, targets:[target...], pad?}   crop to the union + padding
// A target is {text, up?} (element by exact visible text; up = how many parent
// steps to climb, or "row" for the nearest ancestor holding a control),
// {role, name}, or {selector}.
// Read-only by contract: never save, send, publish, delete or toggle.
import { chromium } from '@playwright/test';
import { mkdirSync, readFileSync } from 'node:fs';

const BASE = process.env.BASE_URL ?? 'http://127.0.0.1:3300';
const OUT = process.env.OUT;
mkdirSync(OUT, { recursive: true });
const steps = JSON.parse(readFileSync(process.env.JOB, 'utf8'));
const REFUSE = /\b(save|send|publish|delete|remove|create|submit|approve|merge)\b/i;

const ctx = await chromium.launchPersistentContext(process.env.PROFILE, {
  channel: 'chrome',
  viewport: { width: 1440, height: 900 },
  deviceScaleFactor: 2,
  colorScheme: 'light'
});
const page = ctx.pages()[0] ?? (await ctx.newPage());
const STYLE = `
  nextjs-portal { display: none !important; }
  *, *::before, *::after { transition: none !important; animation: none !important; caret-color: transparent !important; }
`;
const RING_OFFSET = 6;
const highlights = [];

await page.goto(`${BASE}/api/auth/dev-login`, { waitUntil: 'domcontentloaded' });
const login = await page.evaluate(async (key) => {
  const r = await fetch('/api/auth/dev-login', {
    method: 'POST',
    headers: { 'content-type': 'application/json', 'x-decipher-dev-login-key': key },
    body: JSON.stringify({})
  });
  return r.status;
}, process.env.DEV_LOGIN_KEY);
if (login !== 200) {
  console.error(`dev-login failed (${login})`);
  process.exit(1);
}

function locate(t) {
  if (t.selector) return page.locator(t.selector).locator('visible=true').first();
  if (t.role) return page.getByRole(t.role, { name: t.name }).locator('visible=true').first();
  let l = page.getByText(t.text, { exact: true }).locator('visible=true').first();
  if (t.up === 'row') l = l.locator('xpath=ancestor::*[.//button or .//input][1]');
  else if (typeof t.up === 'number') for (let i = 0; i < t.up; i++) l = l.locator('xpath=..');
  return l;
}

async function settle() {
  await page.addStyleTag({ content: STYLE }).catch(() => {});
  await page.waitForTimeout(500);
}

for (const s of steps) {
  if (s.op === 'enterCompany') {
    await page.goto(`${BASE}/auth/select-company`, { waitUntil: 'networkidle', timeout: 120000 });
    await settle();
    // The last-entered Company opens expanded; clicking its card would close it.
    const enter = page.getByRole('button', { name: `Enter ${s.name}` }).locator('visible=true').first();
    if (!(await enter.isVisible())) {
      await page.getByText(s.name, { exact: true }).locator('visible=true').first().click();
      await page.waitForTimeout(1000);
    }
    await enter.click({ timeout: 60000 });
    await page.waitForURL((url) => !url.pathname.startsWith('/auth/'), { timeout: 60000 });
    await page.waitForTimeout(1500);
  } else if (s.op === 'goto') {
    await page.goto(BASE + s.url, { waitUntil: 'networkidle', timeout: 120000 });
    await settle();
  } else if (s.op === 'click') {
    const label = s.text ?? s.name ?? '';
    if (REFUSE.test(label) && !s.opensOnly) throw new Error(`refusing to click "${label}"`);
    await locate(s).click();
    await page.waitForTimeout(s.ms ?? 1500);
    await settle();
  } else if (s.op === 'xy') {
    await page.mouse.click(s.x, s.y);
    await page.waitForTimeout(s.ms ?? 1500);
  } else if (s.op === 'wait') {
    await page.waitForTimeout(s.ms);
  } else if (s.op === 'escape') {
    await page.keyboard.press('Escape');
  } else if (s.op === 'highlight') {
    // Recorded for the next shot only, then forgotten.
    highlights.push(s.target);
  } else if (s.op === 'shot') {
    await page.mouse.move(1, 1);
    await page.evaluate(() => document.activeElement?.blur?.());
    // Boxes are viewport coordinates; bring the targets on screen first,
    // including inside a scrolling rail.
    await locate(s.targets[0]).evaluate((el) => el.scrollIntoView({ block: 'center' }));
    await page.waitForTimeout(400);
    // The highlight is a separate ring appended to <body> above everything, so
    // no ancestor with overflow hidden/auto can clip it (an outline on the
    // element itself was cut off at rail edges).
    const rings = [];
    for (const t of highlights) {
      const l = locate(t);
      // Ring the part of the element the reader can actually see: its box
      // intersected with every ancestor that clips (a scrolling list inside a
      // popover is taller than the popover).
      const box = await l.evaluate((el) => {
        const r = el.getBoundingClientRect();
        let left = r.left, top = r.top, right = r.right, bottom = r.bottom;
        for (let a = el.parentElement; a; a = a.parentElement) {
          const o = getComputedStyle(a);
          if (/(hidden|auto|scroll|clip)/.test(o.overflow + o.overflowX + o.overflowY)) {
            const p = a.getBoundingClientRect();
            left = Math.max(left, p.left); top = Math.max(top, p.top);
            right = Math.min(right, p.right); bottom = Math.max(top, Math.min(bottom, p.bottom));
          }
        }
        return { x: left, y: top, width: Math.max(0, right - left), height: Math.max(0, bottom - top) };
      });
      rings.push({ x: box.x - RING_OFFSET, y: box.y - RING_OFFSET, width: box.width + RING_OFFSET * 2, height: box.height + RING_OFFSET * 2 });
    }
    await page.evaluate((list) => {
      for (const b of list) {
        const d = document.createElement('div');
        d.setAttribute('data-rn-ring', '');
        Object.assign(d.style, {
          position: 'fixed', left: `${b.x}px`, top: `${b.y}px`, width: `${b.width}px`, height: `${b.height}px`,
          border: '2px solid rgb(14 165 233)', borderRadius: '10px', boxSizing: 'border-box',
          pointerEvents: 'none', zIndex: '2147483647'
        });
        document.body.appendChild(d);
      }
    }, rings);
    const pad = s.pad ?? 14;
    const boxes = [...rings];
    for (const t of s.targets) boxes.push(await locate(t).boundingBox());
    const x = Math.max(0, Math.min(...boxes.map((b) => b.x)) - pad);
    const y = Math.max(0, Math.min(...boxes.map((b) => b.y)) - pad);
    const r = Math.max(...boxes.map((b) => b.x + b.width)) + pad;
    const bottom = Math.max(...boxes.map((b) => b.y + b.height)) + pad;
    await page.screenshot({ path: `${OUT}/${s.name}.png`, clip: { x, y, width: r - x, height: bottom - y } });
    await page.evaluate(() => document.querySelectorAll('[data-rn-ring]').forEach((n) => n.remove()));
    highlights.length = 0;
    console.log(`${s.name}.png ${Math.round((r - x) * 2)}x${Math.round((bottom - y) * 2)}`);
  }
}
await ctx.close();
