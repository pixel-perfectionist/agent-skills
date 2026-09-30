// Playwright job runner for release-notes screenshots.
//
// Run from the `frontend/` of the checkout that serves the dev server, after
// sourcing its env file, so `@playwright/test` resolves and the dev-login key
// stays inside this process:
//
//   cd <checkout>/frontend && set -a && . ./.env.local && set +a && \
//     OUT_DIR=<scratch>/notes JOB=<scratch>/notes/jobs/01.json \
//     node --input-type=module -e "$(cat <skill-dir>/scripts/run.mjs)"
//
// Env: OUT_DIR (required; shots land in $OUT_DIR/shots, the browser profile in
// $OUT_DIR/profile — delete it when done), JOB (required; a JSON array of
// steps), BASE_URL (default http://localhost:3000), WIDTH/HEIGHT (default
// 1440x900), SCALE (device scale factor, default 1.5).
//
// Steps ({"op": …}). A target is `selector`, or `role` + `name`, or `text`;
// add `nth` / `exact` when needed.
//   login                      dev-login once (key from process.env only)
//   goto   {url, ms}           relative to BASE_URL, or absolute http(s)/file URL
//   settle {ms}                wait for network idle and skeletons to clear
//   wait   {ms} | {for: target}
//   click  {target, ms, force} hover {target, ms}   press {key}
//   type   {target, value}     fills an input (search boxes only)
//   scroll {target} | {dy}
//   text   {selector?, max}    print visible text
//   links  {match?, max}       print hrefs
//   buttons{match?, max}       print button / menuitem / tab labels
//   eval   {js, max}           evaluate an expression and print the JSON result
//   shot   {name, target?, fullPage?, clip?}   JPEG into $OUT_DIR/shots/<name>.jpg
//   shotAround {name, target, pad:[l,t,r,b]}  viewport crop around one element
//   cookie {name, value}
// Add "required": true to stop the job when that step fails.
//
// Screenshots are read-only work: never click Save / Send / Publish / Move /
// Pin / Delete / Create, and never flip a switch, even unsaved.
import { chromium } from '@playwright/test';
import { mkdirSync, readFileSync } from 'node:fs';

const OUT = process.env.OUT_DIR;
if (!OUT || !process.env.JOB) {
  console.error('OUT_DIR and JOB are required');
  process.exit(1);
}
const BASE = process.env.BASE_URL ?? 'http://localhost:3000';
const steps = JSON.parse(readFileSync(process.env.JOB, 'utf8'));
mkdirSync(`${OUT}/shots`, { recursive: true });

const context = await chromium.launchPersistentContext(`${OUT}/profile`, {
  channel: 'chrome',
  headless: true,
  viewport: {
    width: Number(process.env.WIDTH ?? 1440),
    height: Number(process.env.HEIGHT ?? 900)
  },
  deviceScaleFactor: Number(process.env.SCALE ?? 1.5),
  colorScheme: 'light'
});
// Hide the Next.js dev indicator so shots look like the deployed app.
await context.addInitScript(() => {
  const hide = () => {
    const s = document.createElement('style');
    s.textContent = 'nextjs-portal{display:none!important}';
    document.head.appendChild(s);
  };
  if (document.head) hide();
  else document.addEventListener('DOMContentLoaded', hide);
});
const page = context.pages()[0] ?? (await context.newPage());
page.setDefaultTimeout(30000);

const log = (...a) => console.log(...a);
const locate = (s) =>
  s.selector
    ? page.locator(s.selector).nth(s.nth ?? 0)
    : s.role
      ? page.getByRole(s.role, { name: s.name, exact: s.exact ?? false }).nth(s.nth ?? 0)
      : page.getByText(s.text, { exact: s.exact ?? false }).nth(s.nth ?? 0);
const hasTarget = (s) => Boolean(s.selector || s.role || s.text);

async function settle(ms = 1200) {
  await page.waitForLoadState('networkidle', { timeout: 20000 }).catch(() => {});
  // The stage backend answers slowly; wait out skeleton placeholders.
  await page
    .waitForFunction(
      () =>
        [...document.querySelectorAll('.animate-pulse, [data-slot="skeleton"]')].filter(
          (el) => el.getClientRects().length > 0
        ).length === 0,
      null,
      { timeout: 25000, polling: 400 }
    )
    .catch(() => log('  (skeletons still visible)'));
  await page.waitForTimeout(ms);
}

for (const s of steps) {
  try {
    switch (s.op) {
      case 'login': {
        await page.goto(`${BASE}/api/auth/dev-login`);
        const res = await page.evaluate(async (key) => {
          const r = await fetch('/api/auth/dev-login', {
            method: 'POST',
            credentials: 'same-origin',
            headers: { 'Content-Type': 'application/json', 'x-decipher-dev-login-key': key },
            body: JSON.stringify({ callbackUrl: null })
          });
          const body = await r.json().catch(() => null);
          return { status: r.status, redirectTo: body?.redirectTo ?? null, error: body?.error ?? null };
        }, process.env.DEV_LOGIN_KEY ?? '');
        log('login', res.status, res.error ?? '');
        if (res.redirectTo) {
          await page.goto(res.redirectTo);
          await settle();
          log('landed', page.url());
        }
        break;
      }
      case 'cookie':
        await context.addCookies([{ name: s.name, value: s.value, url: BASE }]);
        break;
      case 'goto':
        await page.goto(/^(https?|file):/.test(s.url) ? s.url : `${BASE}${s.url}`);
        await settle(s.ms);
        log('at', page.url());
        break;
      case 'settle':
        await settle(s.ms);
        break;
      case 'wait':
        if (s.for) await locate(s.for).waitFor({ state: 'visible', timeout: s.timeout ?? 20000 });
        else await page.waitForTimeout(s.ms ?? 1000);
        break;
      case 'click':
        await locate(s).click({ timeout: s.timeout ?? 15000, force: s.force ?? false });
        await settle(s.ms ?? 800);
        break;
      case 'hover':
        await locate(s).hover({ timeout: s.timeout ?? 15000 });
        await page.waitForTimeout(s.ms ?? 600);
        break;
      case 'press':
        await page.keyboard.press(s.key);
        await page.waitForTimeout(s.ms ?? 600);
        break;
      case 'type':
        await locate(s).fill(s.value);
        await page.waitForTimeout(s.ms ?? 800);
        break;
      case 'scroll':
        if (hasTarget(s)) await locate(s).scrollIntoViewIfNeeded();
        else await page.mouse.wheel(0, s.dy ?? 600);
        await page.waitForTimeout(s.ms ?? 500);
        break;
      case 'text': {
        const t = await page.evaluate(
          (sel) => (sel ? document.querySelector(sel)?.innerText : document.body.innerText) ?? '',
          s.selector ?? null
        );
        log(`--- text (${page.url()})\n${t.replace(/\n{3,}/g, '\n\n').slice(0, s.max ?? 4000)}`);
        break;
      }
      case 'links': {
        const links = await page.evaluate(
          (m) =>
            [...document.querySelectorAll('a[href]')]
              .map((a) => `${a.getAttribute('href')}  |  ${a.innerText.replace(/\s+/g, ' ').trim().slice(0, 90)}`)
              .filter((l) => !m || l.includes(m)),
          s.match ?? null
        );
        log(`--- links (${links.length})\n${[...new Set(links)].slice(0, s.max ?? 60).join('\n')}`);
        break;
      }
      case 'buttons': {
        const names = await page.evaluate(
          (m) =>
            [...document.querySelectorAll('button, [role=menuitem], [role=tab]')]
              .map((b) => (b.getAttribute('aria-label') || b.innerText || '').replace(/\s+/g, ' ').trim())
              .filter((t) => t && (!m || new RegExp(m, 'i').test(t))),
          s.match ?? null
        );
        log(`--- buttons (${names.length})\n${[...new Set(names)].slice(0, s.max ?? 80).join(' | ')}`);
        break;
      }
      case 'eval':
        log('eval', JSON.stringify(await page.evaluate(s.js)).slice(0, s.max ?? 4000));
        break;
      case 'shot': {
        const path = `${OUT}/shots/${s.name}.jpg`;
        if (hasTarget(s)) {
          await locate(s).screenshot({ path, type: 'jpeg', quality: s.quality ?? 82 });
        } else {
          await page.screenshot({
            path,
            type: 'jpeg',
            quality: s.quality ?? 82,
            fullPage: s.fullPage ?? false,
            clip: s.clip
          });
        }
        log('shot', path);
        break;
      }
      case 'shotAround': {
        const bb = await locate(s).boundingBox();
        const [l, t, r, b] = s.pad ?? [300, 200, 300, 200];
        const vp = page.viewportSize();
        const x = Math.max(0, bb.x - l);
        const y = Math.max(0, bb.y - t);
        const clip = {
          x,
          y,
          width: Math.min(vp.width - x, bb.width + l + r),
          height: Math.min(vp.height - y, bb.height + t + b)
        };
        const path = `${OUT}/shots/${s.name}.jpg`;
        await page.screenshot({ path, type: 'jpeg', quality: s.quality ?? 85, clip });
        log('shot', path);
        break;
      }
      default:
        log('unknown op', s.op);
    }
  } catch (err) {
    log(`step ${s.op} failed: ${String(err?.message ?? err).split('\n')[0]}`);
    if (s.required) break;
  }
}

await context.close();
