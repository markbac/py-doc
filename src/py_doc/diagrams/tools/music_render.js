#!/usr/bin/env node
// Engrave ABC notation as SVG with abcjs, in the tool image's Chromium.
//
//   node music_render.js <tune.abc> <tune.svg> <puppeteer.json>
//
// abcjs draws into a page, so the tune is engraved in a headless page and its SVG taken out of it.
"use strict";
const fs = require("fs");
const path = require("path");
const puppeteer = require("puppeteer");

async function main() {
  const [input, output, config] = process.argv.slice(2);
  if (!input || !output || !config) {
    console.error("usage: music_render.js <tune.abc> <tune.svg> <puppeteer.json>");
    process.exit(2);
  }
  const abc = fs.readFileSync(input, "utf8");
  const script = fs.readFileSync(require.resolve("abcjs/dist/abcjs-basic-min.js"), "utf8");
  const browser = await puppeteer.launch({ headless: true, ...JSON.parse(fs.readFileSync(config, "utf8")) });
  try {
    const page = await browser.newPage();
    await page.setContent('<!doctype html><html><body><div id="paper"></div></body></html>');
    await page.addScriptTag({ content: script });
    const result = await page.evaluate((tune) => {
      const warnings = [];
      const rendered = ABCJS.renderAbc("paper", tune, { add_classes: false, staffwidth: 700 });
      if (!rendered.length || !rendered[0].lines || !rendered[0].lines.length) warnings.push("no music in the tune");
      (rendered[0] && rendered[0].warnings ? rendered[0].warnings : []).forEach((w) => warnings.push(String(w).replace(/<[^>]+>/g, "")));
      const svg = document.querySelector("#paper svg");
      if (svg) svg.setAttribute("xmlns", "http://www.w3.org/2000/svg");
      return { svg: svg ? svg.outerHTML : "", warnings };
    }, abc);
    if (!result.svg || result.warnings.length) {
      console.error(result.warnings.join("\n") || "abcjs drew nothing");
      process.exit(1);
    }
    fs.writeFileSync(path.resolve(output), result.svg);
  } finally {
    await browser.close();
  }
}

main().catch((error) => {
  console.error(error && error.stack ? error.stack : String(error));
  process.exit(1);
});
