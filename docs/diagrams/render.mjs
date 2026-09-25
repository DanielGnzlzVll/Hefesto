import { mkdirSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const source = pathToFileURL(join(here, "architecture.html")).href + "?render";
const outDir = resolve(here, "../assets/diagrams");

// `npx -p puppeteer` only puts the package on PATH, not on the module search path.
async function loadPuppeteer() {
  try {
    return (await import("puppeteer")).default;
  } catch {
    for (const dir of (process.env.PATH || "").split(":")) {
      if (!dir.endsWith(join("node_modules", ".bin"))) continue;
      try {
        const require = createRequire(join(dir, "..", "noop.js"));
        return (await import(pathToFileURL(require.resolve("puppeteer")).href)).default;
      } catch {}
    }
    throw new Error("puppeteer not found; run: npx -y -p puppeteer node docs/diagrams/render.mjs");
  }
}

const puppeteer = await loadPuppeteer();
const browser = await puppeteer.launch();
try {
  const page = await browser.newPage();
  await page.setViewport({ width: 1600, height: 1000, deviceScaleFactor: 2 });
  await page.goto(source, { waitUntil: "networkidle0" });
  await page.waitForFunction("window.__diagramsReady === true");
  mkdirSync(outDir, { recursive: true });
  for (const figure of await page.$$("figure.ve-fig")) {
    const id = await figure.evaluate((el) => el.id);
    const path = join(outDir, `${id}.png`);
    await figure.screenshot({ path, omitBackground: false });
    console.log(path);
  }
} finally {
  await browser.close();
}
