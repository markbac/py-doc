#!/usr/bin/env node
// Print a py-doc poster (one self-contained HTML page) to a one-page PDF with Chromium.
//
//   node poster_pdf.js <poster.html> <poster.pdf> <puppeteer.json>
//
// The page sets its paper size with @page and scales itself to it on `beforeprint`, as it does in a
// browser's print dialogue, so the PDF is the same as printing from Chrome with no margins and
// background graphics on.
"use strict";
const fs = require("fs");
const path = require("path");
const url = require("url");
const puppeteer = require("puppeteer");

async function main() {
  const [input, output, config] = process.argv.slice(2);
  if (!input || !output || !config) {
    console.error("usage: poster_pdf.js <poster.html> <poster.pdf> <puppeteer.json>");
    process.exit(2);
  }
  const browser = await puppeteer.launch({ headless: true, ...JSON.parse(fs.readFileSync(config, "utf8")) });
  try {
    const page = await browser.newPage();
    await page.goto(url.pathToFileURL(path.resolve(input)).href, { waitUntil: "load", timeout: 120000 });
    // Fonts the page could load, then the layout script's fit, then the print scaling.
    await page.evaluate(async () => {
      if (document.fonts && document.fonts.ready) await document.fonts.ready;
      await new Promise((done) => requestAnimationFrame(() => requestAnimationFrame(done)));
    });
    await page.emulateMediaType("print");
    await page.evaluate(() => window.dispatchEvent(new Event("beforeprint")));
    await page.pdf({ path: output, printBackground: true, preferCSSPageSize: true, pageRanges: "1" });
  } finally {
    await browser.close();
  }
}

main().catch((error) => {
  console.error(error && error.stack ? error.stack : String(error));
  process.exit(1);
});
