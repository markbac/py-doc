#!/usr/bin/env node
/**
 * export-diagrams.js
 * ==================
 * Exports all diagrams (and their legend/key images) from a running
 * Structurizr Local instance as PNG or SVG files.
 *
 * Based on the official structurizr/puppeteer export-diagrams.js, extended
 * with multi-level debug logging, per-view error recovery, file size
 * reporting, failure screenshots, and additional CLI options.
 *
 * Compatible with Structurizr Local (multi-workspace and single-workspace
 * mode) and the on-premises installation. Does NOT require credentials when
 * used with Structurizr Local (localhost-only access).
 *
 * Usage:
 *   node export-diagrams.js <url> <png|svg> [options]
 *
 * Positional arguments:
 *   url                   Full URL to the /diagrams page, e.g.
 *                           http://localhost:8090/workspace/1/diagrams  (multi-ws)
 *                           http://localhost:8090/workspace/diagrams    (single-ws)
 *   png|svg               Output format
 *
 * Options:
 *   --output DIR          Directory to write files into (default: current directory)
 *   --timeout MS          Navigation + per-view render timeout ms (default: 60000)
 *   --delay MS            Extra wait after each view change ms (default: 0)
 *   --no-keys             Skip exporting diagram legend/key images
 *   --no-metadata         Omit embedded element/relationship metadata from
 *                         exported PNG/SVG files (default: metadata included)
 *   --crop                Enable PNG cropping to element bounding box
 *                         (default: crop disabled — full canvas exported)
 *   --view KEY            Export only the named view key instead of all views
 *   --username USER       Username for on-premises/cloud auth
 *   --password PASS       Password for on-premises/cloud auth
 *   --ignore-https-errors Ignore HTTPS certificate errors (on-premises self-signed certs)
 *   --debug LEVEL         Debug verbosity (default: 1)
 *                           0 = silent  — errors only
 *                           1 = info    — progress, counts, filenames
 *                           2 = verbose — timings, file sizes, HTTP errors,
 *                                         browser warnings, per-view detail
 *                           3 = trace   — every browser HTTP request, API
 *                                         call detail, poll ticks, full stacks
 *   --help                Show this help text
 *
 * Environment variables (lower priority than CLI flags):
 *   STRUCTURIZR_DEBUG    Debug level 0-3
 *   STRUCTURIZR_TIMEOUT  Navigation/render timeout in ms
 *
 * Output files written to --output directory:
 *   <viewKey>.png              Diagram PNG
 *   <viewKey>-key.png          Legend/key PNG   (skipped for Image-type views)
 *   <viewKey>.svg              Diagram SVG
 *   <viewKey>-key.svg          Legend/key SVG   (skipped for Image-type views)
 *   _error_<viewKey>.png       Failure screenshot (written at --debug 2+ only)
 *
 * Exit codes:
 *   0   All views exported successfully
 *   1   Fatal error (bad arguments, navigation failure, API unavailable)
 *   2   Partial success (one or more views failed, others succeeded)
 *
 * Upstream compatibility notes (structurizr/puppeteer export-diagrams.js):
 *   - includeMetadata: true  passed to exportCurrentDiagramToPNG/SVG
 *   - crop: false            passed to exportCurrentDiagramToPNG by default
 *   - Image-type view guard  key export skipped for Image views (no legend)
 *   - headless: 'new'        correct for Puppeteer v21+ (upstream uses 'true')
 *   - ignoreHTTPSErrors      supported via --ignore-https-errors flag
 *   - Auth URL derived from workspace URL (same pattern as upstream)
 *   - Per-view error recovery: continues on individual view failure
 *   - page.waitForFunction() used for render polling (upstream pattern)
 *   - Promise-return async pattern replaces upstream exposeFunction/counter
 */

'use strict';

const puppeteer = require('puppeteer');
const fs        = require('fs');
const path      = require('path');

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------
const PNG_FORMAT      = 'png';
const SVG_FORMAT      = 'svg';
const IMAGE_VIEW_TYPE = 'Image'; // Image-type views have no key/legend

// ---------------------------------------------------------------------------
// Logger — 4 levels, coloured, timestamped, all output to stderr
// ---------------------------------------------------------------------------
const LEVELS = { SILENT: 0, INFO: 1, VERBOSE: 2, TRACE: 3 };
const LEVEL_LABELS = ['SILENT', 'INFO', 'VERBOSE', 'TRACE'];

const C = {
  reset:   '\x1b[0m',
  bold:    '\x1b[1m',
  dim:     '\x1b[2m',
  red:     '\x1b[31m',
  green:   '\x1b[32m',
  yellow:  '\x1b[33m',
  cyan:    '\x1b[36m',
  magenta: '\x1b[35m',
  white:   '\x1b[37m',
};

class Logger {
  constructor(level) {
    this.level = Number.isInteger(level) ? level : LEVELS.INFO;
  }

  _ts() {
    return new Date().toISOString().slice(11, 23); // HH:MM:SS.mmm
  }

  _emit(minLevel, colour, label, ...args) {
    if (minLevel > this.level) return;
    const ts  = `${C.dim}${this._ts()}${C.reset}`;
    const lbl = `${colour}${label}${C.reset}`;
    console.error(`${ts} ${lbl}`, ...args);
  }

  error(...a)   { this._emit(LEVELS.SILENT,  C.red,     '[ERROR]  ', ...a); } // always
  info(...a)    { this._emit(LEVELS.INFO,    C.cyan,    '[INFO]   ', ...a); }
  success(...a) { this._emit(LEVELS.INFO,    C.green,   '[OK]     ', ...a); }
  warn(...a)    { this._emit(LEVELS.INFO,    C.yellow,  '[WARN]   ', ...a); }
  verbose(...a) { this._emit(LEVELS.VERBOSE, C.white,   '[VERBOSE]', ...a); }
  trace(...a)   { this._emit(LEVELS.TRACE,   C.magenta, '[TRACE]  ', ...a); }

  // Browser console events routed by message type
  browserLog(type, text) {
    const msg = `[BROWSER:${type.toUpperCase()}] ${text}`;
    if      (type === 'error') this._emit(LEVELS.INFO,    C.red,    '[BROWSER]', msg);
    else if (type === 'warn')  this._emit(LEVELS.VERBOSE, C.yellow, '[BROWSER]', msg);
    else                       this._emit(LEVELS.TRACE,   C.dim,    '[BROWSER]', msg);
  }
}

// ---------------------------------------------------------------------------
// Argument parsing
// ---------------------------------------------------------------------------
function parseArgs(argv) {
  const args = argv.slice(2);

  if (args.includes('--help') || args.includes('-h')) {
    printHelp();
    process.exit(0);
  }

  const positional = args.filter(a => !a.startsWith('--'));
  if (positional.length < 2) {
    console.error('Usage: node export-diagrams.js <url> <png|svg> [options]');
    console.error('       node export-diagrams.js --help');
    process.exit(1);
  }

  const opts = {
    url:                positional[0],
    format:             positional[1].toLowerCase(),
    output:             process.cwd(),
    timeout:            parseInt(process.env.STRUCTURIZR_TIMEOUT || '60000', 10),
    delay:              0,
    keys:               true,
    includeMetadata:    true,  // upstream default: includeMetadata: true
    crop:               false, // upstream default: crop: false
    viewKey:            null,
    username:           null,
    password:           null,
    ignoreHTTPSErrors:  false,
    debug:              parseInt(process.env.STRUCTURIZR_DEBUG || '1', 10),
  };

  for (let i = 0; i < args.length; i++) {
    switch (args[i]) {
      case '--output':               opts.output            = args[++i];                break;
      case '--timeout':              opts.timeout           = parseInt(args[++i], 10); break;
      case '--delay':                opts.delay             = parseInt(args[++i], 10); break;
      case '--no-keys':              opts.keys              = false;                   break;
      case '--no-metadata':          opts.includeMetadata   = false;                  break;
      case '--crop':                 opts.crop              = true;                    break;
      case '--view':                 opts.viewKey           = args[++i];              break;
      case '--username':             opts.username          = args[++i];              break;
      case '--password':             opts.password          = args[++i];              break;
      case '--ignore-https-errors':  opts.ignoreHTTPSErrors = true;                   break;
      case '--debug':                opts.debug             = parseInt(args[++i], 10); break;
    }
  }

  if (opts.format !== PNG_FORMAT && opts.format !== SVG_FORMAT) {
    console.error(`Format must be '${PNG_FORMAT}' or '${SVG_FORMAT}', got: '${opts.format}'`);
    process.exit(1);
  }

  if (isNaN(opts.debug) || opts.debug < 0 || opts.debug > 3) {
    opts.debug = 1;
  }

  return opts;
}

function printHelp() {
  const src   = fs.readFileSync(__filename, 'utf8');
  const match = src.match(/\/\*\*([\s\S]*?)\*\//);
  if (match) console.log(match[1].replace(/^ \* ?/gm, '').trim());
}

// ---------------------------------------------------------------------------
// File I/O helpers
// ---------------------------------------------------------------------------
function sanitiseFilename(name) {
  return name.replace(/[/\\:*?"<>|]/g, '_').replace(/\s+/g, '-');
}

function formatBytes(n) {
  if (n < 1024)    return `${n} B`;
  if (n < 1048576) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / 1048576).toFixed(1)} MB`;
}

/**
 * Write a file from a base64 data URI string or plain text string.
 * Returns the resolved filepath.
 */
function writeFile(outDir, filename, data, log) {
  const filepath = path.join(outDir, filename);
  if (typeof data === 'string' && data.startsWith('data:')) {
    const b64 = data.split(',')[1];
    fs.writeFileSync(filepath, Buffer.from(b64, 'base64'));
  } else {
    fs.writeFileSync(filepath, data, 'utf8');
  }
  const size = fs.statSync(filepath).size;
  log.verbose(`  Written: ${filepath} (${formatBytes(size)})`);
  return filepath;
}

// ---------------------------------------------------------------------------
// Structurizr scripting API wrappers
// ---------------------------------------------------------------------------

/**
 * Wait until structurizr.scripting.isDiagramRendered() returns true.
 * Uses page.waitForFunction (Puppeteer built-in polling) which correctly
 * applies the timeout and avoids a manual loop.
 */
async function waitForDiagramRendered(page, timeout, log) {
  log.trace('waitForFunction: isDiagramRendered()...');
  const t0 = Date.now();
  await page.waitForFunction(
    'typeof structurizr !== "undefined" &&' +
    'typeof structurizr.scripting !== "undefined" &&' +
    'structurizr.scripting.isDiagramRendered() === true',
    { timeout }
  );
  log.trace(`  isDiagramRendered() true after ${Date.now() - t0}ms`);
}

/** Return array of all view descriptors via structurizr.scripting.getViews(). */
async function getViews(page, log) {
  log.trace('getViews()...');
  const views = await page.evaluate(() => structurizr.scripting.getViews());
  log.verbose(`  getViews() -> ${views.length} view(s)`);
  views.forEach((v, i) =>
    log.trace(`    [${i}] key=${v.key}  type=${v.type}  name=${v.name || '(unnamed)'}`)
  );
  return views;
}

/**
 * Switch to a named view and wait for it to render.
 * Mirrors upstream: evaluate changeView, optional delay, then waitForFunction.
 */
async function changeView(page, viewKey, delay, timeout, log) {
  log.trace(`changeView('${viewKey}')...`);
  await page.evaluate((key) => structurizr.scripting.changeView(key), viewKey);
  if (delay > 0) {
    log.trace(`  Post-change delay: ${delay}ms`);
    await sleep(delay);
  }
  await waitForDiagramRendered(page, timeout, log);
  const activeKey = await page.evaluate(() => structurizr.scripting.getViewKey());
  log.trace(`  Active view key after changeView: ${activeKey}`);
  if (activeKey !== viewKey) {
    throw new Error(
      `changeView('${viewKey}') failed — active view is '${activeKey}'`
    );
  }
}

/**
 * Export the current diagram to PNG.
 * Passes { includeMetadata, crop } — matches upstream options.
 */
async function exportDiagramToPNG(page, includeMetadata, crop, log) {
  const exportOpts = { includeMetadata, crop };
  log.trace(`exportCurrentDiagramToPNG(${JSON.stringify(exportOpts)})...`);
  const data = await page.evaluate((opts) => {
    return new Promise((resolve) => {
      structurizr.scripting.exportCurrentDiagramToPNG(opts, (png) => resolve(png));
    });
  }, exportOpts);
  log.trace(`  PNG data URI length: ${data ? data.length : 0}`);
  if (!data) throw new Error('exportCurrentDiagramToPNG returned null/undefined');
  return data;
}

/** Export the current diagram key/legend to PNG. */
async function exportDiagramKeyToPNG(page, log) {
  log.trace('exportCurrentDiagramKeyToPNG()...');
  const data = await page.evaluate(() => {
    return new Promise((resolve) => {
      structurizr.scripting.exportCurrentDiagramKeyToPNG((png) => resolve(png));
    });
  });
  log.trace(`  Key PNG data URI length: ${data ? data.length : 0}`);
  return data; // null/undefined if view has no key — caller handles
}

/**
 * Export the current diagram to SVG.
 * Passes { includeMetadata } — matches upstream.
 */
async function exportDiagramToSVG(page, includeMetadata, log) {
  const exportOpts = { includeMetadata };
  log.trace(`exportCurrentDiagramToSVG(${JSON.stringify(exportOpts)})...`);
  const svg = await page.evaluate(
    (opts) => structurizr.scripting.exportCurrentDiagramToSVG(opts),
    exportOpts
  );
  log.trace(`  SVG string length: ${svg ? svg.length : 0}`);
  if (!svg) throw new Error('exportCurrentDiagramToSVG returned null/undefined');
  return svg;
}

/** Export the current diagram key/legend to SVG. */
async function exportDiagramKeyToSVG(page, log) {
  log.trace('exportCurrentDiagramKeyToSVG()...');
  const svg = await page.evaluate(
    () => structurizr.scripting.exportCurrentDiagramKeyToSVG()
  );
  log.trace(`  Key SVG string length: ${svg ? svg.length : 0}`);
  return svg; // null/undefined if view has no key — caller handles
}

// ---------------------------------------------------------------------------
// Auth helper (on-premises / cloud — not needed for Local)
// Derives the /dashboard URL from the workspace URL (same as upstream).
// ---------------------------------------------------------------------------
async function login(page, url, username, password, timeout, log) {
  const parts  = url.split('://');
  const origin = parts[1].substring(0, parts[1].indexOf('/'));
  const signIn = `${parts[0]}://${origin}/dashboard`;

  log.info(`Signing in via: ${signIn}`);
  log.verbose(`  Username: ${username}`);

  await page.goto(signIn, { waitUntil: 'networkidle2', timeout });
  log.trace('  Waiting for #username...');
  await page.waitForSelector('#username', { timeout });

  await page.type('#username', username);
  await page.type('#password', password);

  log.trace('  Submitting credentials...');
  await page.keyboard.press('Enter');
  await page.waitForSelector('div#dashboard', { timeout });

  log.success('Signed in');
  log.trace(`  Post-login URL: ${page.url()}`);
}

// ---------------------------------------------------------------------------
// Utility
// ---------------------------------------------------------------------------
function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

// ---------------------------------------------------------------------------
// Main export routine
// ---------------------------------------------------------------------------
async function run(opts, log) {
  fs.mkdirSync(opts.output, { recursive: true });
  log.verbose(`Output directory: ${path.resolve(opts.output)}`);

  log.info('Launching headless Chrome...');
  const browser = await puppeteer.launch({
    headless: true,                         // the new headless mode, the only one in Puppeteer 22 and later
    acceptInsecureCerts: opts.ignoreHTTPSErrors, // ignoreHTTPSErrors was removed from Puppeteer
    args: [
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--disable-dev-shm-usage',
      '--disable-gpu',
    ],
  });

  if (log.level >= LEVELS.VERBOSE) {
    const pv = (() => {
      try { return require('puppeteer/package.json').version; } catch { return 'unknown'; }
    })();
    log.verbose(`Puppeteer v${pv}`);
    log.verbose(`Chrome: ${browser.process()?.spawnfile || 'bundled'}`);
  }

  const page = await browser.newPage();

  // Wire browser events to logger
  page.on('console',      (msg) => log.browserLog(msg.type(), msg.text()));
  page.on('pageerror',    (err) => log.error(`[PAGE ERROR] ${err.message}`));
  page.on('requestfailed', (req) =>
    log.verbose(`[REQ FAILED] ${req.failure()?.errorText} — ${req.url()}`)
  );
  page.on('response', (resp) => {
    if (resp.status() >= 400) log.verbose(`[HTTP ${resp.status()}] ${resp.url()}`);
  });
  if (log.level >= LEVELS.TRACE) {
    page.on('request', (req) => log.trace(`[REQ] ${req.method()} ${req.url()}`));
  }

  await page.setViewport({ width: 1920, height: 1080 });
  log.verbose('Viewport: 1920x1080');

  try {
    if (opts.username && opts.password) {
      await login(page, opts.url, opts.username, opts.password, opts.timeout, log);
    }

    log.info(`Navigating to: ${opts.url}`);
    const navStart = Date.now();
    const res = await page.goto(opts.url, {
      waitUntil: 'networkidle2',
      timeout:   opts.timeout,
    });
    log.verbose(`  Navigation: ${Date.now() - navStart}ms  HTTP ${res?.status()}`);

    // Verify the scripting API surface exists on this page
    log.trace('Checking structurizr.scripting...');
    const apiPresent = await page.evaluate(() =>
      typeof structurizr !== 'undefined' &&
      typeof structurizr.scripting !== 'undefined'
    );
    if (!apiPresent) {
      throw new Error(
        'structurizr.scripting is not available on this page. ' +
        'Ensure the URL ends in /diagrams and Structurizr Local is running.'
      );
    }
    log.verbose('structurizr.scripting API confirmed');

    await waitForDiagramRendered(page, opts.timeout, log);

    let views = await getViews(page, log);

    if (opts.viewKey) {
      log.info(`Filtering to single view: '${opts.viewKey}'`);
      views = views.filter((v) => v.key === opts.viewKey);
      if (views.length === 0) {
        const available = (await getViews(page, log)).map((v) => v.key).join(', ');
        throw new Error(
          `View '${opts.viewKey}' not found. Available: ${available}`
        );
      }
    }

    log.info(`Exporting ${views.length} view(s) as ${opts.format.toUpperCase()}...`);
    log.verbose(
      `  includeMetadata=${opts.includeMetadata}  crop=${opts.crop}` +
      `  keys=${opts.keys}  delay=${opts.delay}ms`
    );

    const results    = { ok: 0, failed: 0 };
    const failedKeys = [];

    for (let i = 0; i < views.length; i++) {
      const view    = views[i];
      const n       = `[${i + 1}/${views.length}]`;
      const isImage = view.type === IMAGE_VIEW_TYPE;

      log.info(`${n} ${view.key}  (${view.type})`);
      log.verbose(`  Name: ${view.name || '(unnamed)'}  isImageView: ${isImage}`);

      try {
        await changeView(page, view.key, opts.delay, opts.timeout, log);

        const safe = sanitiseFilename(view.key);
        const t1   = Date.now();

        if (opts.format === PNG_FORMAT) {

          // Diagram PNG
          const pngData     = await exportDiagramToPNG(page, opts.includeMetadata, opts.crop, log);
          const diagramFile = writeFile(opts.output, `${safe}.png`, pngData, log);
          log.success(
            `  ${n} ${path.basename(diagramFile)}` +
            ` (${formatBytes(fs.statSync(diagramFile).size)}, ${Date.now() - t1}ms)`
          );

          // Key PNG — skip for Image-type views (they have no legend)
          if (opts.keys && !isImage) {
            log.verbose('  Exporting key PNG...');
            try {
              const keyData = await exportDiagramKeyToPNG(page, log);
              if (keyData) {
                const kf = writeFile(opts.output, `${safe}-key.png`, keyData, log);
                log.verbose(`  Key: ${path.basename(kf)} (${formatBytes(fs.statSync(kf).size)})`);
              } else {
                log.verbose(`  No key data returned (view has no legend)`);
              }
            } catch (ke) {
              log.warn(`  Key PNG failed for ${view.key}: ${ke.message}`);
              log.trace(`  ${ke.stack}`);
            }
          } else if (isImage) {
            log.verbose(`  Skipping key — Image-type view has no legend`);
          }

        } else {

          // Diagram SVG
          const svgData     = await exportDiagramToSVG(page, opts.includeMetadata, log);
          const diagramFile = writeFile(opts.output, `${safe}.svg`, svgData, log);
          log.success(
            `  ${n} ${path.basename(diagramFile)}` +
            ` (${formatBytes(fs.statSync(diagramFile).size)}, ${Date.now() - t1}ms)`
          );

          // Key SVG — skip for Image-type views
          if (opts.keys && !isImage) {
            log.verbose('  Exporting key SVG...');
            try {
              const keySvg = await exportDiagramKeyToSVG(page, log);
              if (keySvg) {
                const kf = writeFile(opts.output, `${safe}-key.svg`, keySvg, log);
                log.verbose(`  Key: ${path.basename(kf)} (${formatBytes(fs.statSync(kf).size)})`);
              } else {
                log.verbose(`  No key data returned (view has no legend)`);
              }
            } catch (ke) {
              log.warn(`  Key SVG failed for ${view.key}: ${ke.message}`);
              log.trace(`  ${ke.stack}`);
            }
          } else if (isImage) {
            log.verbose(`  Skipping key — Image-type view has no legend`);
          }
        }

        results.ok++;

      } catch (viewErr) {
        log.error(`  ${n} FAILED: ${view.key} — ${viewErr.message}`);
        log.verbose(`  Stack: ${viewErr.stack}`);
        results.failed++;
        failedKeys.push(view.key);

        // Save a browser screenshot of the failure state at verbose+
        if (log.level >= LEVELS.VERBOSE) {
          try {
            const sp = path.join(opts.output, `_error_${sanitiseFilename(view.key)}.png`);
            await page.screenshot({ path: sp, fullPage: true });
            log.verbose(`  Failure screenshot: ${sp}`);
          } catch (_) { /* don't mask the real error */ }
        }
      }
    }

    log.info('');
    log.info(
      `Export complete: ${results.ok} ok` +
      (results.failed > 0 ? `, ${results.failed} failed` : '')
    );
    if (failedKeys.length > 0) log.warn(`Failed views: ${failedKeys.join(', ')}`);
    log.info(`Output: ${path.resolve(opts.output)}`);

    return results.failed === 0 ? 0 : 2;

  } finally {
    log.verbose('Closing browser...');
    await browser.close();
    log.trace('Browser closed.');
  }
}

// ---------------------------------------------------------------------------
// Entry point
// ---------------------------------------------------------------------------
(async () => {
  const opts = parseArgs(process.argv);
  const log  = new Logger(opts.debug);

  log.info('Structurizr Diagram Exporter');
  log.verbose(`Node.js ${process.version}  PID ${process.pid}`);
  log.verbose(
    `Options: ${JSON.stringify(
      { ...opts, password: opts.password ? '***' : null }, null, 2
    )}`
  );
  log.verbose(`Debug level: ${opts.debug} (${LEVEL_LABELS[opts.debug]})`);

  try {
    const exitCode = await run(opts, log);
    process.exit(exitCode);
  } catch (err) {
    log.error(`Fatal: ${err.message}`);
    log.verbose(`Stack:\n${err.stack}`);
    process.exit(1);
  }
})();
