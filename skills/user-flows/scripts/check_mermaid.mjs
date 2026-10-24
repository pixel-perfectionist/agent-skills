#!/usr/bin/env node
// Renders every ```mermaid block in a markdown file with Mermaid itself, in a
// headless browser, and fails if any block does not render. Parsing alone
// misses errors that only layout finds.
//
//   node check_mermaid.mjs USER-FLOWS.md
//   node check_mermaid.mjs USER-FLOWS.md --png ./diagrams --only 0,7
//
// Mermaid is taken from the project's node_modules when it has it, otherwise
// from jsDelivr (network needed). See references/scripts.md.

import { mkdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { launchBrowser, resolveFrom } from "./lib/browser.mjs";
import { extractMermaidBlocks, parseArgs } from "./lib/flows.mjs";

const MERMAID_CDN = "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js";

function usage(message) {
	if (message) console.error(message);
	console.error(
		"Usage: node check_mermaid.mjs <file.md> [--png <dir>] [--only <i,j>] [--resolve-from <dir>]",
	);
	process.exit(2);
}

/** Runs in the page. Renders one diagram; returns the SVG or the error. */
async function renderOne([source, id]) {
	const mermaid = window.mermaid;
	mermaid.initialize({ startOnLoad: false, securityLevel: "strict" });
	try {
		await mermaid.parse(source);
		const { svg } = await mermaid.render(id, source);
		document.getElementById("out").innerHTML = svg;
		return { ok: true, bytes: svg.length };
	} catch (error) {
		return { ok: false, message: String(error?.message ?? error) };
	}
}

async function main() {
	let args;
	try {
		args = parseArgs(process.argv.slice(2));
	} catch (error) {
		usage(error.message);
	}
	const { options, positional } = args;
	const file = positional[0];
	if (!file) usage("Give the markdown file to check.");

	const blocks = extractMermaidBlocks(readFileSync(file, "utf8"));
	const only = options.only
		? new Set(options.only.split(",").map((value) => Number(value.trim())))
		: null;
	const selected = blocks.filter((block) => only === null || only.has(block.index));
	console.log(`${blocks.length} diagrams in ${file}`);
	if (selected.length === 0) process.exit(0);

	const directories = [options["resolve-from"], process.cwd()].filter(Boolean);
	const local = resolveFrom(directories, "mermaid/dist/mermaid.min.js");
	const session = await launchBrowser(directories);
	const { page } = session;
	await session.setViewport(1400, 1000);
	let failures = 0;
	try {
		await page.setContent(
			"<!doctype html><html><body style='background:#fff'><div id='out'></div></body></html>",
		);
		await page.addScriptTag(local ? { path: local } : { url: MERMAID_CDN });
		if (options.png) mkdirSync(options.png, { recursive: true });

		for (const block of selected) {
			const result = await page.evaluate(renderOne, [
				block.source,
				`diagram${block.index}`,
			]);
			const where = `#${block.index} (line ${block.line})`;
			if (!result.ok) {
				failures++;
				console.log(`${where}: FAIL ${result.message.slice(0, 400)}`);
				continue;
			}
			let note = "";
			if (options.png) {
				const target = path.join(options.png, `diagram-${block.index}.png`);
				const svg = await page.$("#out svg");
				await svg.screenshot({ path: target });
				note = `, ${target}`;
			}
			console.log(`${where}: ok (${result.bytes} bytes${note})`);
		}
	} finally {
		await session.close();
	}
	console.log(
		failures === 0
			? `All ${selected.length} rendered.`
			: `${failures} of ${selected.length} failed.`,
	);
	process.exit(failures === 0 ? 0 : 1);
}

main().catch((error) => {
	console.error(error instanceof Error ? error.message : error);
	process.exit(1);
});
