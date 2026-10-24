// Opens a headless Chromium through whichever of Playwright or Puppeteer the
// project already has, so the skill installs nothing of its own.

import { createRequire } from "node:module";
import path from "node:path";
import { pathToFileURL } from "node:url";

const CANDIDATES = ["playwright", "@playwright/test", "puppeteer"];

/** Resolves a package from the first directory that has it. */
export function resolveFrom(directories, name) {
	for (const directory of directories) {
		try {
			const require = createRequire(path.join(path.resolve(directory), "noop.js"));
			return require.resolve(name);
		} catch {
			// Not installed there; try the next directory.
		}
	}
	return null;
}

export async function launchBrowser(directories) {
	for (const name of CANDIDATES) {
		const resolved = resolveFrom(directories, name);
		if (resolved === null) {
			continue;
		}
		const module = await import(pathToFileURL(resolved).href);
		return name === "puppeteer"
			? launchPuppeteer(module.default ?? module)
			: launchPlaywright(module.chromium ?? module.default?.chromium);
	}
	throw new Error(
		`No browser library found from ${directories.join(", ")}. ` +
			"Run from a project that has playwright, @playwright/test or puppeteer, " +
			"or pass --resolve-from <directory where one is installed>.",
	);
}

async function launchPuppeteer(puppeteer) {
	const browser = await puppeteer.launch({
		args: ["--no-sandbox", "--disable-dev-shm-usage"],
	});
	const page = await browser.newPage();
	return {
		library: "puppeteer",
		page,
		setViewport: (width, height) => page.setViewport({ width, height }),
		goto: (url) => page.goto(url, { waitUntil: "networkidle2" }),
		type: (selector, text) => page.type(selector, text),
		upload: async (selector, file) => {
			const handle = await page.$(selector);
			if (handle === null) throw new Error(`No element matches ${selector}.`);
			await handle.uploadFile(file);
		},
		close: () => browser.close(),
	};
}

async function launchPlaywright(chromium) {
	if (chromium === undefined) {
		throw new Error("The Playwright module has no chromium export.");
	}
	// The bundled browser is a separate download that is often missing or a
	// different revision from the installed library; an installed Chrome works.
	let browser;
	try {
		browser = await chromium.launch();
	} catch (error) {
		try {
			browser = await chromium.launch({ channel: "chrome" });
		} catch {
			throw error;
		}
	}
	const page = await browser.newPage();
	return {
		library: "playwright",
		page,
		setViewport: (width, height) => page.setViewportSize({ width, height }),
		goto: (url) => page.goto(url, { waitUntil: "networkidle" }),
		type: (selector, text) => page.fill(selector, text),
		upload: (selector, file) => page.setInputFiles(selector, file),
		close: () => browser.close(),
	};
}
