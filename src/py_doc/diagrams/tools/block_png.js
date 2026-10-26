#!/usr/bin/env node
// Photograph a poster block for a document: one HTML page with the block in #block, as a PNG of that element,
// or print that element alone to a one-page PDF when the output ends in .pdf (its text and SVG stay vector).
//
//   node block_png.js <block.html> <block.png|block.pdf> <puppeteer.json> [scale]
//
// The page has the poster's styles and the block at the width of the document's text. The picture is taken
// at `scale` times the CSS pixels (default 2), so it is sharp at the 192 dpi of the other diagrams.
"use strict";
const fs = require("fs");
const path = require("path");
const url = require("url");
const puppeteer = require("puppeteer");

async function main() {
  const [input, output, config, scale] = process.argv.slice(2);
  if (!input || !output || !config) {
    console.error("usage: block_png.js <block.html> <block.png|block.pdf> <puppeteer.json> [scale]");
    process.exit(2);
  }
  const browser = await puppeteer.launch({ headless: true, ...JSON.parse(fs.readFileSync(config, "utf8")) });
  try {
    const page = await browser.newPage();
    await page.setViewport({ width: 2000, height: 1000, deviceScaleFactor: Number(scale) || 2 });
    await page.goto(url.pathToFileURL(path.resolve(input)).href, { waitUntil: "load", timeout: 120000 });
    await page.evaluate(async () => {
      if (document.fonts && document.fonts.ready) await document.fonts.ready;
      await new Promise((done) => requestAnimationFrame(() => requestAnimationFrame(done)));
    });
    const block = await page.$("#block");
    if (!block) throw new Error("the page has no #block element");
    if (!output.endsWith(".pdf")) {
      await block.screenshot({ path: output, type: "png" });
      return;
    }
    // The page cut to the block: moved to the top left, so the page's size is the block's far corner
    await page.addStyleTag({ content: ".poster{margin:0!important}" });
    const box = await block.boundingBox();
    const width = Math.ceil(box.x + box.width), height = Math.ceil(box.y + box.height);
    await page.addStyleTag({ content: `@page{size:${width}px ${height}px;margin:0}html,body{overflow:hidden}` });
    await page.pdf({ path: output, width: `${width}px`, height: `${height}px`, printBackground: true, pageRanges: "1" });
  } finally {
    await browser.close();
  }
}

main().catch((error) => {
  console.error(error && error.stack ? error.stack : String(error));
  process.exit(1);
});
