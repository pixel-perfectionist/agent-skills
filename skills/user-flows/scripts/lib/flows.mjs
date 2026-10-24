// Pure helpers shared by walk_ui.mjs and check_mermaid.mjs. No browser and no
// file system here, so they can be tested directly.

const STEP_KINDS = [
	"go",
	"wait",
	"click",
	"type",
	"upload",
	"eval",
	"shot",
	"dump",
	"viewport",
];

/** Collapses whitespace and case, so `GET STARTED →` matches `Get started`. */
export function normalizeLabel(text) {
	return String(text ?? "")
		.replace(/\s+/g, " ")
		.trim()
		.toLowerCase();
}

/**
 * Picks the element a click step means, from labels read in the page.
 *
 * An exact match wins over a prefix match, so `Dev` does not click `Developer
 * tools` when a `Dev` button is there. Returns the candidate's index, or -1.
 */
export function pickCandidate(labels, wanted) {
	const target = normalizeLabel(wanted);
	if (target === "") {
		return -1;
	}
	const normalized = labels.map(normalizeLabel);
	const exact = normalized.indexOf(target);
	if (exact !== -1) {
		return exact;
	}
	return normalized.findIndex((label) => label.startsWith(target));
}

/** Validates walk steps, so a typo fails before a browser is launched. */
export function parseSteps(value) {
	const steps = typeof value === "string" ? JSON.parse(value) : value;
	if (!Array.isArray(steps)) {
		throw new Error("Steps must be a JSON array.");
	}
	steps.forEach((step, index) => {
		if (step === null || typeof step !== "object" || Array.isArray(step)) {
			throw new Error(`Step ${index} must be an object.`);
		}
		const keys = Object.keys(step);
		if (keys.length !== 1 || !STEP_KINDS.includes(keys[0])) {
			throw new Error(
				`Step ${index} must have exactly one of: ${STEP_KINDS.join(", ")}.`,
			);
		}
		const [kind] = keys;
		const arg = step[kind];
		const fail = (expected) => {
			throw new Error(`Step ${index} (${kind}) expects ${expected}.`);
		};
		switch (kind) {
			case "go":
			case "click":
			case "eval":
			case "shot":
				if (typeof arg !== "string" || arg === "") fail("a non-empty string");
				break;
			case "wait":
				if (typeof arg !== "number" || arg < 0) fail("milliseconds");
				break;
			case "dump":
				if (arg !== true) fail("true");
				break;
			case "type":
				if (!isStringPair(arg)) fail('["css selector", "text"]');
				break;
			case "upload":
				if (typeof arg !== "string" && !isStringPair(arg)) {
					fail('"path" or ["css selector", "path"]');
				}
				break;
			case "viewport":
				if (
					!Array.isArray(arg) ||
					arg.length !== 2 ||
					!arg.every((n) => Number.isInteger(n) && n > 0)
				) {
					fail("[width, height]");
				}
				break;
		}
	});
	return steps;
}

function isStringPair(value) {
	return (
		Array.isArray(value) &&
		value.length === 2 &&
		value.every((item) => typeof item === "string" && item !== "")
	);
}

/** Every fenced mermaid block, with the line its fence opens on. */
export function extractMermaidBlocks(markdown) {
	const blocks = [];
	const lines = String(markdown).split("\n");
	let current = null;
	lines.forEach((line, index) => {
		if (current === null) {
			if (/^\s*```mermaid\s*$/.test(line)) {
				current = { line: index + 1, body: [] };
			}
			return;
		}
		if (/^\s*```\s*$/.test(line)) {
			blocks.push({
				index: blocks.length,
				line: current.line,
				source: current.body.join("\n"),
			});
			current = null;
			return;
		}
		current.body.push(line);
	});
	if (current !== null) {
		throw new Error(`Unclosed mermaid block opened on line ${current.line}.`);
	}
	return blocks;
}

/**
 * Minimal `--flag value` parser. Flags listed in `booleans` take no value;
 * everything else that is not a flag is positional.
 */
export function parseArgs(argv, booleans = []) {
	const options = {};
	const positional = [];
	for (let index = 0; index < argv.length; index++) {
		const arg = argv[index];
		if (!arg.startsWith("--")) {
			positional.push(arg);
			continue;
		}
		const name = arg.slice(2);
		if (booleans.includes(name)) {
			options[name] = true;
			continue;
		}
		const value = argv[index + 1];
		if (value === undefined || value.startsWith("--")) {
			throw new Error(`--${name} needs a value.`);
		}
		options[name] = value;
		index++;
	}
	return { options, positional };
}
