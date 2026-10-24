// Run: node --test skills/constraints/scripts/floor-guard.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { execFileSync, spawnSync } from 'node:child_process';
import { mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const GUARD = join(dirname(fileURLToPath(import.meta.url)), 'floor-guard.mjs');

// Writes files into dir; a null value deletes the file.
function write(dir, files) {
  for (const [path, content] of Object.entries(files)) {
    const full = join(dir, path);
    if (content === null) { rmSync(full); continue; }
    mkdirSync(dirname(full), { recursive: true });
    writeFileSync(full, content);
  }
}

// A throwaway repository with one base commit; returns its directory and the base SHA.
function repo(files) {
  const dir = mkdtempSync(join(tmpdir(), 'floor-guard-'));
  const git = (...a) => execFileSync('git', ['-c', 'core.hooksPath=/dev/null', ...a], { cwd: dir, encoding: 'utf8', stdio: 'pipe' });
  git('init', '-q');
  git('config', 'user.email', 'test@example.com');
  git('config', 'user.name', 'test');
  git('config', 'commit.gpgsign', 'false');
  write(dir, files);
  git('add', '-A');
  git('commit', '-qm', 'base');
  return { dir, base: git('rev-parse', 'HEAD').trim() };
}

function guard(dir, base, { hookMode = false, stdin = '' } = {}) {
  const args = [GUARD, ...(base ? ['--base', base] : []), ...(hookMode ? ['--hook'] : [])];
  const r = spawnSync(process.execPath, args, { cwd: dir, encoding: 'utf8', input: stdin });
  return { code: r.status, out: r.stdout + r.stderr };
}

const CONSTRAINTS = `# Constraints

## Floor (always enforced, no setup required)

- No new suppression comments: \`@ts-ignore\`, \`eslint-disable\`, \`# noqa\`
- No unimplemented stubs: \`throw new Error("Not implemented")\`, empty \`catch {}\`

## Enforced with numbers

| Dimension | Rule | Checked by | Runs at |
|-----------|------|-----------|---------|
| Coverage | Changed lines ≥ 80% covered | \`vitest run --coverage\` | task end |

## Exceptions

| ID | Rule | Path | Reason | Owner | Expires |
|----|------|------|--------|-------|---------|
`;

test('an ordinary change is clean', () => {
  const { dir, base } = repo({ 'src/a.js': 'export const a = 1;\n' });
  write(dir, { 'src/a.js': 'export const a = 2;\nexport const b = 3;\n' });
  assert.deepEqual(guard(dir, base), { code: 0, out: 'floor-guard: clean\n' });
});

test('a new suppression comment is a violation', () => {
  const { dir, base } = repo({ 'src/a.ts': 'export const a = 1;\n' });
  write(dir, { 'src/a.ts': '// @ts-ignore\nexport const a: string = 1;\n' });
  const r = guard(dir, base);
  assert.equal(r.code, 1);
  assert.match(r.out, /\[silenced-checker\] src\/a\.ts/);
});

test('hook mode blocks once, then hands a repeat failure to the user', () => {
  const { dir, base } = repo({ 'src/a.ts': 'export const a = 1;\n' });
  write(dir, { 'src/a.ts': '// eslint-disable-next-line\nexport const a = 1;\n' });
  assert.equal(guard(dir, base, { hookMode: true, stdin: '{"stop_hook_active":false}' }).code, 2);
  const retry = guard(dir, base, { hookMode: true, stdin: '{"stop_hook_active":true}' });
  assert.equal(retry.code, 1);
  assert.match(retry.out, /still present after one retry/);
});

test('hook mode is silent when clean', () => {
  const { dir, base } = repo({ 'src/a.js': 'export const a = 1;\n' });
  assert.deepEqual(guard(dir, base, { hookMode: true, stdin: '{}' }), { code: 0, out: '' });
});

test('a stub in an untracked file is found', () => {
  const { dir, base } = repo({ 'src/a.js': 'export const a = 1;\n' });
  write(dir, { 'src/new.js': 'export function f() {\n  throw new Error("Not implemented");\n}\n' });
  const r = guard(dir, base);
  assert.equal(r.code, 1);
  assert.match(r.out, /\[unfinished-work\] src\/new\.js/);
});

test('skipped tests, deleted tests, and removed assertions are found', () => {
  const { dir, base } = repo({
    'src/a.test.js': "it('a', () => {\n  expect(1).toBe(1);\n  expect(2).toBe(2);\n});\n",
    'src/b.test.js': "it('b', () => { expect(true).toBe(true); });\n",
    'src/c.test.js': "it('c', () => {});\n",
  });
  write(dir, {
    'src/a.test.js': "it('a', () => {\n  expect(1).toBe(1);\n});\n",
    'src/b.test.js': null,
    'src/c.test.js': "it.skip('c', () => {});\n",
  });
  const r = guard(dir, base);
  assert.equal(r.code, 1);
  assert.match(r.out, /\[assertion-removed\] src\/a\.test\.js/);
  assert.match(r.out, /\[test-deleted\] src\/b\.test\.js/);
  assert.match(r.out, /\[test-made-easier\] src\/c\.test\.js/);
});

test('docs and the guard itself are not scanned for suppression patterns', () => {
  const { dir, base } = repo({ 'README.md': '# Readme\n' });
  write(dir, {
    'README.md': '# Readme\n\nNever add eslint-disable or @ts-ignore. TODO: write more.\n',
    'CONSTRAINTS.md': CONSTRAINTS,
    'scripts/floor-guard.mjs': readFileSync(GUARD, 'utf8'),
  });
  assert.equal(guard(dir, base).code, 0);
});

test('a loosened threshold is a violation and a tightened one is not', () => {
  const { dir, base } = repo({ 'CONSTRAINTS.md': CONSTRAINTS });
  write(dir, { 'CONSTRAINTS.md': CONSTRAINTS.replace('≥ 80%', '≥ 70%') });
  const loosened = guard(dir, base);
  assert.equal(loosened.code, 1);
  assert.match(loosened.out, /\[threshold-loosened\]/);
  write(dir, { 'CONSTRAINTS.md': CONSTRAINTS.replace('≥ 80%', '≥ 90%') });
  assert.equal(guard(dir, base).code, 0);
});

test('a removed rule and a new exception are violations', () => {
  const { dir, base } = repo({ 'CONSTRAINTS.md': CONSTRAINTS });
  write(dir, {
    'CONSTRAINTS.md': CONSTRAINTS
      .replace(/^\| Coverage .*\n/m, '')
      .concat('| W1 | `no-explicit-any` | `src/legacy/**` | Rewrite planned | @owner | 2027-01-01 |\n'),
  });
  const r = guard(dir, base);
  assert.equal(r.code, 1);
  assert.match(r.out, /\[rule-removed\] CONSTRAINTS\.md/);
  assert.match(r.out, /\[new-exception\] CONSTRAINTS\.md/);
});

test('outside a git repository the guard cannot run, and never reads as clean', () => {
  const dir = mkdtempSync(join(tmpdir(), 'floor-guard-nogit-'));
  assert.equal(guard(dir, 'main').code, 2);
  assert.equal(guard(dir, 'main', { hookMode: true, stdin: '{}' }).code, 1);
});

test('a missing base ref cannot run', () => {
  const { dir } = repo({ 'src/a.js': 'export const a = 1;\n' });
  const r = guard(dir, 'no-such-ref');
  assert.equal(r.code, 2);
  assert.match(r.out, /no merge base against no-such-ref/);
});
