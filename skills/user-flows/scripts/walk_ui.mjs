#!/usr/bin/env node
// Walks a running web app step by step and prints what a person could act on
// after each step: links with their targets, buttons, inputs, headings, and
// whatever sits in an open dialog. Screenshots go to --out.
//
//   node walk_ui.mjs --base http://localhost:3000 --out ./shots \
//     '[{"go":"/"},{"dump":true},{"click":"Get started"},{"shot":"new"},{"dump":true}]'
//
// Steps: go, wait, click, type, upload, eval, shot, dump, viewport.
// See references/scripts.md.

import { mkdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { launchBrowser } from "./lib/browser.mjs";
import { parseArgs, parseSteps, pickCandidate } from "./lib/flows.mjs";

const CLICKABLE =
	"a,button,[role=button],[role=menuitem],[role=tab],[role=option],[role=link],summary,label";

function usage(message) {
	if (message) console.error(message);
	console.error(
		"Usage: node walk_ui.mjs --base <url> [--out <dir>] [--resolve-from <dir>] " +
			"(--steps <file.json> | '<steps json>')",
	);
	process.exit(2);
}

/** Runs in the page. Lists what is visible and actionable. */
function inventory() {
	const visible = (element) => {
		const box = element.getBoundingClientRect();
		const style = getComputedStyle(element);
		return (
			box.width > 0 &&
			box.height > 0 &&
			style.visibility !== "hidden" &&
			style.display !== "none"
		);
	};
	const selector =
		"a,button,input,textarea,select,h1,h2,h3,[role=dialog] p,[role=menuitem],[role=tab],[role=option],[role=alert],[role=status]";
	const lines = [...document.querySelectorAll(selector)]
		.filter(visible)
		.map((element) => {
			const tag = element.tagName.toLowerCase();
			const type = element.getAttribute("type");
			const label = (
				element.getAttribute("aria-label") ||
				element.innerText ||
				element.getAttribute("placeholder") ||
				element.getAttribute("name") ||
				""
			)
				.replace(/\s+/g, " ")
				.trim()
				.slice(0, 100);
			const href = element.getAttribute("href");
			const role = element.getAttribute("role");
			const where = element.closest("[role=dialog],[role=alertdialog],dialog")
				? " [dialog]"
				: "";
			const kind = role
				? `${tag}[${role}]`
				: tag === "input" && type
					? `${tag}[${type}]`
					: tag;
			const disabled = element.disabled ? " (disabled)" : "";
			return `${kind}${where}${disabled}: ${label}${href ? ` -> ${href}` : ""}`;
		});
	return [location.href, ...lines].join("\n");
}

/** Runs in the page. The accessible label of each clickable element. */
function clickableLabels(selector) {
	return [...document.querySelectorAll(selector)].map((element) => {
		const box = element.getBoundingClientRect();
		if (box.width === 0 || box.height === 0) return "";
		return (
			element.getAttribute("aria-label") ||
			element.innerText ||
			element.textContent ||
			""
		);
	});
}

/** Runs in the page. Clicks the element at that index. */
function clickAt([selector, index]) {
	const element = document.querySelectorAll(selector)[index];
	element.scrollIntoView({ block: "center" });
	element.click();
}

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

async function main() {
	let args;
	try {
		args = parseArgs(process.argv.slice(2));
	} catch (error) {
		usage(error.message);
	}
	const { options, positional } = args;
	if (!options.base) usage("--base is required.");
	const source = options.steps
		? readFileSync(options.steps, "utf8")
		: positional[0];
	if (!source) usage("Give steps as JSON or with --steps.");

	let steps;
	try {
		steps = parseSteps(source);
	} catch (error) {
		usage(`Invalid steps: ${error.message}`);
	}

	const out = path.resolve(options.out ?? "user-flow-shots");
	const directories = [options["resolve-from"], process.cwd()].filter(Boolean);
	const session = await launchBrowser(directories);
	const { page } = session;
	await session.setViewport(1400, 900);
	page.on("pageerror", (error) => console.log(`PAGE ERROR: ${error}`));

	let failed = false;
	try {
		for (const step of steps) {
			const [kind] = Object.keys(step);
			const arg = step[kind];
			switch (kind) {
				case "go":
					await session.goto(new URL(arg, options.base).href);
					break;
				case "wait":
					await sleep(arg);
					break;
				case "viewport":
					await session.setViewport(arg[0], arg[1]);
					break;
				case "click": {
					const labels = await page.evaluate(clickableLabels, CLICKABLE);
					const index = pickCandidate(labels, arg);
					if (index === -1) {
						console.log(`CLICK "${arg}": not found`);
						failed = true;
						break;
					}
					await page.evaluate(clickAt, [CLICKABLE, index]);
					console.log(`CLICK "${arg}": ok`);
					await sleep(800);
					break;
				}
				case "type":
					await session.type(arg[0], arg[1]);
					break;
				case "upload": {
					const [selector, file] =
						typeof arg === "string" ? ["input[type=file]", arg] : arg;
					await session.upload(selector, path.resolve(file));
					await sleep(1500);
					console.log(`UPLOAD ${file}: ok`);
					break;
				}
				case "eval": {
					const result = await page.evaluate(arg);
					console.log(`EVAL ${JSON.stringify(result)}`);
					break;
				}
				case "shot": {
					mkdirSync(out, { recursive: true });
					const file = path.join(out, `${arg}.png`);
					await page.screenshot({ path: file });
					console.log(`SHOT ${file}`);
					break;
				}
				case "dump":
					console.log(`----\n${await page.evaluate(inventory)}`);
					break;
			}
		}
	} finally {
		await session.close();
	}
	process.exit(failed ? 1 : 0);
}

main().catch((error) => {
	console.error(error instanceof Error ? error.message : error);
	process.exit(1);
});
