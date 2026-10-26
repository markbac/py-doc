#!/usr/bin/env node
// Print a py-doc HTML deck to a PDF with Chromium, one slide a page, the page the size of a slide.
//
//   node deck_pdf.js <deck.html> <deck.pdf> <puppeteer.json>
//
// The deck's print styles show every slide at its own size, one after the other. Before printing, the
// page's own check marks the slides whose content overflows them; their numbers are written to standard
// output as "PYDOC-OVERFLOW [3, 7]" for py-doc to report.
"use strict";
const fs = require("fs");
const path = require("path");
const url = require("url");
const puppeteer = require("puppeteer");

async function main() {
  const [input, output, config] = process.argv.slice(2);
  if (!input || !output || !config) {
    console.error("usage: deck_pdf.js <deck.html> <deck.pdf> <puppeteer.json>");
    process.exit(2);
  }
  const browser = await puppeteer.launch({ headless: true, ...JSON.parse(fs.readFileSync(config, "utf8")) });
  try {
    const page = await browser.newPage();
    await page.setViewport({ width: 1280, height: 800 });
    await page.goto(url.pathToFileURL(path.resolve(input)).href, { waitUntil: "load", timeout: 120000 });
    const overflow = await page.evaluate(async () => {
      if (document.fonts && document.fonts.ready) await document.fonts.ready;
      await new Promise((done) => requestAnimationFrame(() => requestAnimationFrame(done)));
      return window.pyDocOverflow || [];
    });
    console.log("PYDOC-OVERFLOW " + JSON.stringify(overflow));
    await page.emulateMediaType("print");
    await page.pdf({ path: output, printBackground: true, preferCSSPageSize: true });
  } finally {
    await browser.close();
  }
}

main().catch((error) => {
  console.error(error && error.stack ? error.stack : String(error));
  process.exit(1);
});
