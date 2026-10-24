import assert from "node:assert/strict";
import { test } from "node:test";
import {
	extractMermaidBlocks,
	normalizeLabel,
	parseArgs,
	parseSteps,
	pickCandidate,
} from "./lib/flows.mjs";

test("labels match regardless of case, spacing and CSS uppercasing", () => {
	assert.equal(normalizeLabel("  GET\n STARTED  →"), "get started →");
	assert.equal(pickCandidate(["Docs", "GET STARTED →"], "Get started"), 1);
});

test("an exact label wins over a longer one that starts the same", () => {
	assert.equal(pickCandidate(["Developer tools", "Dev"], "Dev"), 1);
	assert.equal(pickCandidate(["Developer tools", "Docs"], "Dev"), 0);
});

test("nothing is picked for a missing or empty label", () => {
	assert.equal(pickCandidate(["Docs"], "Publish"), -1);
	assert.equal(pickCandidate(["Docs"], "   "), -1);
});

test("steps accept every kind with its argument shape", () => {
	const steps = parseSteps(
		JSON.stringify([
			{ go: "/" },
			{ wait: 500 },
			{ click: "New project" },
			{ type: ["input[name=title]", "Demo"] },
			{ upload: "site.zip" },
			{ upload: ["#file", "site.zip"] },
			{ eval: "document.title" },
			{ shot: "home" },
			{ dump: true },
			{ viewport: [390, 844] },
		]),
	);
	assert.equal(steps.length, 10);
});

test("steps reject unknown kinds, extra keys and wrong arguments", () => {
	assert.throws(() => parseSteps("{}"), /JSON array/);
	assert.throws(() => parseSteps([{ hover: "x" }]), /exactly one of/);
	assert.throws(() => parseSteps([{ go: "/", wait: 1 }]), /exactly one of/);
	assert.throws(() => parseSteps([{ wait: "1s" }]), /milliseconds/);
	assert.throws(() => parseSteps([{ dump: 1 }]), /true/);
	assert.throws(() => parseSteps([{ type: ["only selector"] }]), /selector/);
	assert.throws(() => parseSteps([{ viewport: [0, 800] }]), /width, height/);
});

test("mermaid blocks are found with the line their fence opens on", () => {
	const markdown = [
		"# Title",
		"```mermaid",
		"flowchart TD",
		"    A --> B",
		"```",
		"```ts",
		"const x = 1;",
		"```",
		"```mermaid",
		"flowchart LR",
		"```",
	].join("\n");
	assert.deepEqual(extractMermaidBlocks(markdown), [
		{ index: 0, line: 2, source: "flowchart TD\n    A --> B" },
		{ index: 1, line: 9, source: "flowchart LR" },
	]);
});

test("an unclosed mermaid block is an error, not a silent skip", () => {
	assert.throws(
		() => extractMermaidBlocks("text\n```mermaid\nflowchart TD"),
		/line 2/,
	);
});

test("arguments split into flags, boolean flags and positionals", () => {
	assert.deepEqual(
		parseArgs(["doc.md", "--png", "out", "--verbose", "--only", "0,3"], [
			"verbose",
		]),
		{ options: { png: "out", verbose: true, only: "0,3" }, positional: ["doc.md"] },
	);
	assert.throws(() => parseArgs(["--png"]), /needs a value/);
	assert.throws(() => parseArgs(["--png", "--only", "1"]), /needs a value/);
});
