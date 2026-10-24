# Scripts

Two Node.js helpers (Node 18 or later). Neither installs anything: they open
Chromium through whichever of `playwright`, `@playwright/test` or `puppeteer`
the project already has, looked up from `--resolve-from` and then the current
directory. Run them from the project root.

If the project has none, install one outside the repository and point at it:

```sh
mkdir -p /tmp/user-flows-browser && npm --prefix /tmp/user-flows-browser i puppeteer
node <skill>/scripts/walk_ui.mjs --resolve-from /tmp/user-flows-browser ...
```

## `walk_ui.mjs`

Walks a running app and prints what a person could act on after each step.

```sh
node <skill>/scripts/walk_ui.mjs --base http://localhost:3000 --out /tmp/shots \
  '[{"go":"/"},{"dump":true},{"click":"Get started"},{"shot":"new-project"},{"dump":true}]'
```

Use `--steps file.json` for longer walks. Keep screenshots outside the
repository unless the user wants them committed.

| Step | Argument | Effect |
| --- | --- | --- |
| `go` | path or URL | Navigate, relative to `--base`, and wait for the network to settle. |
| `wait` | milliseconds | Pause, for animations and late requests. |
| `click` | label | Click the visible link, button, tab, option or menu item whose accessible label or text matches. Case and spacing are ignored; an exact match wins over a prefix. Prints `not found` and exits 1 at the end when nothing matches. |
| `type` | `[selector, text]` | Type into a field. |
| `upload` | path, or `[selector, path]` | Set a file input (default `input[type=file]`). |
| `eval` | JavaScript expression | Evaluate in the page and print the JSON result. Good for reading full `href`s, ticking a checkbox, or reading `localStorage`. |
| `shot` | name | Save `<out>/<name>.png`. |
| `dump` | `true` | Print the URL and every visible link (with target), button, input, heading, alert, and dialog paragraph. Items inside a dialog are marked `[dialog]`; disabled ones `(disabled)`. |
| `viewport` | `[width, height]` | Resize, for mobile layouts. |

Each run starts a fresh browser profile, so `localStorage` flags such as
"already confirmed" are cleared. To see the second-visit state, set the flag
with `eval` and reload with `go`.

Reading a dump: compare it with what the code said should be there. A control
the code renders but the dump lacks is gated by something (role, data, flag) the
walk did not satisfy; find out what before writing the journey.

## `check_mermaid.mjs`

Renders every fenced `mermaid` block in a markdown file and exits non-zero if
any fails.

```sh
node <skill>/scripts/check_mermaid.mjs USER-FLOWS.md
node <skill>/scripts/check_mermaid.mjs USER-FLOWS.md --png /tmp/diagrams --only 0,7
```

Mermaid comes from the project's `node_modules` when present, otherwise from
jsDelivr. `--png` writes each rendered diagram as an image; look at the map and
the largest journeys before delivering.

## Tests

```sh
node --test <skill>/scripts/flows.test.mjs
```

They cover label matching, step validation, mermaid extraction and argument
parsing, and need no browser.
