#!/usr/bin/env node
import { readFile, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";

const [, , input, output] = process.argv;

if (!input || !output) {
  console.error("Usage: node markdown_to_hwpx.mjs <input.md> <output.hwpx>");
  process.exit(2);
}

const kordocPath = resolve("node_modules/kordoc/dist/index.js");
const { markdownToHwpx } = await import(pathToFileURL(kordocPath).href);
const markdown = await readFile(resolve(input), "utf8");
const hwpx = await markdownToHwpx(markdown);
await writeFile(resolve(output), Buffer.from(hwpx));
console.log(`Wrote HWPX: ${resolve(output)}`);
