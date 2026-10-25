#!/usr/bin/env node
// Photograph a poster block for a document: one HTML page with the block in #block, as a PNG of that element.
//
//   node block_png.js <block.html> <block.png> <puppeteer.json>
//
// The page has the poster's styles and the block at the width of the document's text. The picture is taken
// at twice the CSS pixels, so it is sharp at the 192 dpi of the other diagrams.
"use strict";
const fs = require("fs");
const path = require("path");
const url = require("url");
const puppeteer = require("puppeteer");

async function main() {
  const [input, output, config] = process.argv.slice(2);
  if (!input || !output || !config) {
    console.error("usage: block_png.js <block.html> <block.png> <puppeteer.json>");
    process.exit(2);
  }
  const browser = await puppeteer.launch({ headless: true, ...JSON.parse(fs.readFileSync(config, "utf8")) });
  try {
    const page = await browser.newPage();
    await page.setViewport({ width: 2000, height: 1000, deviceScaleFactor: 2 });
    await page.goto(url.pathToFileURL(path.resolve(input)).href, { waitUntil: "load", timeout: 120000 });
    await page.evaluate(async () => {
      if (document.fonts && document.fonts.ready) await document.fonts.ready;
      await new Promise((done) => requestAnimationFrame(() => requestAnimationFrame(done)));
    });
    const block = await page.$("#block");
    if (!block) throw new Error("the page has no #block element");
    await block.screenshot({ path: output, type: "png" });
  } finally {
    await browser.close();
  }
}

main().catch((error) => {
  console.error(error && error.stack ? error.stack : String(error));
  process.exit(1);
});
