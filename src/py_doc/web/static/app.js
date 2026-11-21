/* py-doc web: the explorer, editor, live preview, jobs and lint report. No build step, no framework. */
"use strict";

const $ = (sel, root = document) => root.querySelector(sel);
const el = (tag, attrs = {}, ...children) => {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (key === "class") node.className = value;
    else if (key.startsWith("on")) node.addEventListener(key.slice(2), value);
    else if (value === true) node.setAttribute(key, "");
    else if (value !== false && value != null) node.setAttribute(key, value);
  }
  for (const child of children.flat()) if (child != null) node.append(child.nodeType ? child : String(child));
  return node;
};
const store = {
  get(key, fallback) { try { const v = localStorage.getItem("py-doc." + key); return v == null ? fallback : JSON.parse(v); } catch { return fallback; } },
  set(key, value) { try { localStorage.setItem("py-doc." + key, JSON.stringify(value)); } catch { /* private window */ } },
};
const parentOf = (path) => path.includes("/") ? path.slice(0, path.lastIndexOf("/")) : "";
const baseName = (path) => path.slice(path.lastIndexOf("/") + 1);
const projectOf = (path) => path.split("/")[0];
const isMarkdown = (path) => /\.(md|markdown)$/i.test(path);
const isImage = (path) => /\.(png|jpe?g|gif|webp|svg|bmp|ico)$/i.test(path);
const TEXT = /\.(md|markdown|txt|ya?ml|json|csv|tsv|py|puml|iuml|plantuml|dot|gv|mmd|dsl|svg|html?|css|js|lua|toml|ini|cfg|xml|bpmn|d2|pikchr|tex|bib|sh|ps1|rst|adoc)$/i;
const isText = (path) => TEXT.test(path) || baseName(path).startsWith(".");
const urlPath = (path) => path.split("/").map(encodeURIComponent).join("/");

// --- server calls ----------------------------------------------------------------------------

async function api(method, url, body) {
  const options = { method, headers: {} };
  if (body instanceof FormData) options.body = body;
  else if (body !== undefined) { options.body = JSON.stringify(body); options.headers["Content-Type"] = "application/json"; }
  const response = await fetch(url, options);
  const kind = response.headers.get("content-type") || "";
  const data = kind.includes("json") ? await response.json() : await response.text();
  if (!response.ok) {
    const message = (data && (data.error || (Array.isArray(data.detail) ? data.detail.map((d) => d.msg).join("; ") : data.detail))) || response.statusText;
    throw new Error(message);
  }
  return data;
}
const q = (params) => "?" + new URLSearchParams(params).toString();

function toast(message, error = false) {
  const box = $("#toast");
  box.textContent = message;
  box.className = "toast" + (error ? " error" : "");
  box.hidden = false;
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => (box.hidden = true), error ? 6000 : 2800);
}
const fail = (error) => toast(error.message || String(error), true);

// --- dialogs ---------------------------------------------------------------------------------

function dialog(title, fields, okLabel = "OK") {
  return new Promise((resolve) => {
    const modal = $("#modal"), body = $("#modal-body");
    $("#modal-title").textContent = title;
    $("#modal-ok").textContent = okLabel;
    body.replaceChildren();
    const inputs = {};
    for (const field of fields) {
      if (field.type === "check") {
        const input = el("input", { type: "checkbox", checked: !!field.value });
        inputs[field.name] = input;
        body.append(el("label", { class: "check" }, input, " " + field.label));
      } else if (field.type === "text-only") {
        body.append(el("p", {}, field.label));
      } else {
        const input = el("input", { type: "text", value: field.value || "", placeholder: field.placeholder || "" });
        inputs[field.name] = input;
        body.append(el("label", {}, field.label), input);
      }
    }
    const close = (result) => { modal.hidden = true; $("#modal-form").onsubmit = null; $("#modal-cancel").onclick = null; resolve(result); };
    $("#modal-form").onsubmit = (event) => {
      event.preventDefault();
      const result = {};
      for (const [name, input] of Object.entries(inputs)) result[name] = input.type === "checkbox" ? input.checked : input.value.trim();
      close(result);
    };
    $("#modal-cancel").onclick = () => close(null);
    modal.hidden = false;
    const first = body.querySelector("input[type=text]");
    if (first) { first.focus(); const dot = first.value.lastIndexOf("."); first.setSelectionRange(0, dot > 0 ? dot : first.value.length); }
    else $("#modal-ok").focus();
  });
}
const ask = (title, label, value) => dialog(title, [{ name: "value", label, value }]).then((r) => r && r.value);
const confirmBox = (title, text, ok = "Delete") => dialog(title, [{ type: "text-only", label: text }], ok).then((r) => !!r);

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") { if (!$("#modal").hidden) $("#modal-cancel").click(); hideMenus(); }
});

// --- the explorer ----------------------------------------------------------------------------

const state = {
  projects: [], trees: {}, open: new Set(store.get("open", [])), selected: null,
  docs: new Map(), active: null, // open files: path -> { path, text, saved, editorDoc, modified }
};

async function loadProjects() {
  state.projects = await api("GET", "/api/projects");
  await Promise.all(state.projects.filter((p) => state.open.has(p.name)).map((p) => loadTree(p.name, false)));
  renderTree();
}

async function loadTree(project, render = true) {
  try { state.trees[project] = await api("GET", "/api/tree" + q({ path: project })); }
  catch (error) { delete state.trees[project]; }
  if (render) renderTree();
}

async function refreshProject(path) {
  const project = projectOf(path);
  if (!state.projects.some((p) => p.name === project)) return loadProjects();
  await loadTree(project);
}

function toggle(path) {
  if (state.open.has(path)) state.open.delete(path); else state.open.add(path);
  store.set("open", [...state.open]);
  if (!path.includes("/") && state.open.has(path) && !state.trees[path]) return loadTree(path);
  renderTree();
}

function renderTree() {
  const tree = $("#tree");
  const scroll = tree.scrollTop;
  tree.replaceChildren();
  if (!state.projects.length) {
    tree.append(el("div", { class: "welcome" }, el("p", {}, "No projects yet. Make one with ＋, or drop a folder here.")));
  }
  for (const project of state.projects) {
    const open = state.open.has(project.name);
    tree.append(nodeRow({ name: project.name, path: project.name, type: "dir" }, open, true, project.config));
    if (open && state.trees[project.name]) tree.append(childList(state.trees[project.name].children));
  }
  tree.scrollTop = scroll;
}

function childList(children) {
  const box = el("div", { class: "children" });
  for (const child of children) {
    const open = state.open.has(child.path);
    box.append(nodeRow(child, open, false, false));
    if (child.type === "dir" && open) box.append(childList(child.children || []));
  }
  return box;
}

function icon(node, project) {
  if (project) return "📘";
  if (node.type === "dir") return state.open.has(node.path) ? "📂" : "📁";
  if (isMarkdown(node.path)) return "📝";
  if (isImage(node.path)) return "🖼️";
  if (/\.(docx|dotx)$/i.test(node.path)) return "📄";
  if (/\.(pptx|potx)$/i.test(node.path)) return "📊";
  if (/\.pdf$/i.test(node.path)) return "📕";
  if (/\.html?$/i.test(node.path)) return "🌐";
  if (/\.ya?ml$/i.test(node.path)) return "⚙️";
  if (/\.zip$/i.test(node.path)) return "🗜️";
  return "📃";
}

function nodeRow(node, open, project, config) {
  const doc = state.docs.get(node.path);
  const row = el("div", {
    class: "node" + (project ? " project" : "") + (state.selected === node.path ? " selected" : "") + (doc && doc.dirty ? " dirty" : ""),
    draggable: project ? "false" : "true", "data-path": node.path, "data-type": node.type, title: node.path,
  },
    el("span", { class: "twist" }, node.type === "dir" ? (open ? "▾" : "▸") : ""),
    el("span", { class: "ico" }, icon(node, project)),
    el("span", { class: "name" }, node.name),
    config ? el("span", { class: "tag", title: "Has a py-doc.yml: builds as a whole" }, "yml") : null,
    el("span", { class: "more", title: "Actions", onclick: (e) => { e.stopPropagation(); contextMenu(e, node, project); } }, "⋯"),
  );
  row.addEventListener("click", () => {
    state.selected = node.path;
    if (node.type === "dir") toggle(node.path); else { openFile(node.path); renderTree(); }
  });
  row.addEventListener("contextmenu", (e) => { e.preventDefault(); state.selected = node.path; renderTree(); contextMenu(e, node, project); });
  row.addEventListener("dragstart", (e) => { e.dataTransfer.setData("application/x-py-doc-path", node.path); e.dataTransfer.effectAllowed = "move"; });
  const target = node.type === "dir" ? node.path : parentOf(node.path);
  row.addEventListener("dragover", (e) => { e.preventDefault(); e.stopPropagation(); row.classList.add("drop"); e.dataTransfer.dropEffect = e.dataTransfer.types.includes("application/x-py-doc-path") ? "move" : "copy"; });
  row.addEventListener("dragleave", () => row.classList.remove("drop"));
  row.addEventListener("drop", (e) => { e.preventDefault(); e.stopPropagation(); row.classList.remove("drop"); dropOn(e, target); });
  return row;
}

// The tree's empty space: a folder dropped there becomes a new project
const treeBox = $("#tree");
treeBox.addEventListener("dragover", (e) => { if (e.dataTransfer.types.includes("Files")) { e.preventDefault(); treeBox.classList.add("drop-root"); } });
treeBox.addEventListener("dragleave", (e) => { if (e.target === treeBox) treeBox.classList.remove("drop-root"); });
treeBox.addEventListener("drop", (e) => { e.preventDefault(); treeBox.classList.remove("drop-root"); dropOn(e, ""); });

async function dropOn(event, folder) {
  const moved = event.dataTransfer.getData("application/x-py-doc-path");
  if (moved) {
    if (!folder) return toast("Drop it on a project or a folder");
    const target = folder + "/" + baseName(moved);
    if (target === moved || parentOf(moved) === folder) return;
    try { await api("POST", "/api/move", { source: moved, target }); retarget(moved, target); await refreshProject(target); if (projectOf(moved) !== projectOf(target)) await refreshProject(moved); toast(`Moved to ${folder}`); }
    catch (error) { fail(error); }
    return;
  }
  const files = await droppedFiles(event.dataTransfer);
  if (!files.length) return;
  if (!folder) {
    // On empty space: a single folder becomes a project of its name; loose files ask for one
    const tops = new Set(files.map((f) => f.path.split("/")[0]));
    const oneFolder = tops.size === 1 && files.every((f) => f.path.includes("/"));
    const name = await ask("New project", "Name of the project for these files", oneFolder ? [...tops][0] : "");
    if (!name) return;
    try { await api("POST", "/api/projects", { name }); } catch (error) { if (!/exists/.test(error.message)) return fail(error); }
    if (oneFolder) files.forEach((f) => (f.path = f.path.split("/").slice(1).join("/")));
    state.open.add(name); store.set("open", [...state.open]);
    await upload(name, files);
    return loadProjects();
  }
  await upload(folder, files);
}

async function droppedFiles(transfer) {
  const items = [...(transfer.items || [])].filter((item) => item.kind === "file");
  const entries = items.map((item) => item.webkitGetAsEntry && item.webkitGetAsEntry()).filter(Boolean);
  if (!entries.length) return [...transfer.files].map((file) => ({ file, path: file.name }));
  const found = [];
  const readAll = (reader) => new Promise((resolve, reject) => {
    const all = [];
    const next = () => reader.readEntries((batch) => { if (!batch.length) resolve(all); else { all.push(...batch); next(); } }, reject);
    next();
  });
  async function walk(entry, prefix) {
    if (entry.isFile) {
      const file = await new Promise((resolve, reject) => entry.file(resolve, reject));
      if (!/^(\.DS_Store|Thumbs\.db)$/.test(file.name)) found.push({ file, path: prefix + file.name });
    } else if (entry.isDirectory) {
      if ([".git", "node_modules", "__pycache__", ".venv"].includes(entry.name)) return;
      for (const child of await readAll(entry.createReader())) await walk(child, prefix + entry.name + "/");
    }
  }
  for (const entry of entries) await walk(entry, "");
  return found;
}

async function upload(folder, files, unzip = null) {
  if (unzip === null && files.length === 1 && /\.zip$/i.test(files[0].path)) {
    const choice = await dialog("Upload a zip", [
      { type: "text-only", label: `${files[0].path} will go into ${folder}.` },
      { type: "check", name: "unzip", label: "Unpack it (keep its folders)", value: true },
    ], "Upload");
    if (!choice) return;
    unzip = choice.unzip;
  }
  const bar = el("div", { class: "upload-bar" }, el("div", {}, `Uploading ${files.length} file(s) to ${folder}`), el("div", { class: "bar" }, el("div")));
  $("#sidebar").append(bar);
  const total = files.reduce((sum, f) => sum + f.file.size, 0) || 1;
  let sent = 0, written = 0;
  try {
    // In batches, so a big folder does not become one huge request
    for (let i = 0; i < files.length;) {
      const form = new FormData(), paths = [];
      let size = 0;
      form.append("folder", folder);
      while (i < files.length && (paths.length === 0 || (paths.length < 100 && size + files[i].file.size < 64e6))) {
        form.append("files", files[i].file, baseName(files[i].path));
        paths.push(files[i].path); size += files[i].file.size; i++;
      }
      form.append("paths", JSON.stringify(paths));
      form.append("unzip", unzip ? "true" : "false");
      const result = await api("POST", "/api/upload", form);
      written += result.written.length; sent += size;
      bar.querySelector(".bar div").style.width = Math.round((100 * sent) / total) + "%";
    }
    toast(`${written} file(s) added to ${folder}`);
    state.open.add(folder); store.set("open", [...state.open]);
    for (const doc of state.docs.values()) if (!doc.dirty) reloadIfChanged(doc);
  } catch (error) { fail(error); }
  finally { bar.remove(); await refreshProject(folder); }
}

function pickFiles(folder, directory = false) {
  const input = directory ? $("#folder-input") : $("#file-input");
  input.value = "";
  input.onchange = () => {
    const files = [...input.files].map((file) => ({ file, path: file.webkitRelativePath || file.name }));
    if (files.length) upload(folder, files);
  };
  input.click();
}

// --- menus -----------------------------------------------------------------------------------

function hideMenus() { $("#context").hidden = true; $("#convert-menu").hidden = true; }
document.addEventListener("click", (e) => { if (!e.target.closest(".context, .menu, #convert-button")) hideMenus(); });

function showContext(event, items) {
  const menu = $("#context");
  menu.replaceChildren(...items.map((item) => {
    if (item === "-") return el("hr");
    if (item.label && !item.run) return el("div", { class: "label" }, item.label);
    return el("button", { class: item.danger ? "danger" : "", onclick: () => { hideMenus(); Promise.resolve(item.run()).catch(fail); } }, item.text);
  }));
  menu.hidden = false;
  const { innerWidth: w, innerHeight: h } = window;
  const box = menu.getBoundingClientRect();
  menu.style.left = Math.min(event.clientX, w - box.width - 8) + "px";
  menu.style.top = Math.min(event.clientY, h - box.height - 8) + "px";
}

function contextMenu(event, node, project) {
  const path = node.path, dir = node.type === "dir";
  const folder = dir ? path : parentOf(path);
  const items = [];
  if (project) {
    const config = (state.projects.find((p) => p.name === path) || {}).config;
    if (config) {
      items.push({ label: "Build" },
        { text: "Build everything", run: () => build(path) },
        { text: "Build Word only", run: () => build(path, "docx") },
        { text: "Build PDF only", run: () => build(path, "pdf") },
        { text: "Build PowerPoint only", run: () => build(path, "pptx") },
        { text: "Build posters only", run: () => build(path, "poster") },
        { text: "Build with lint first", run: () => build(path, null, true) },
        { text: "Build the web site too", run: () => build(path, null, false, true) },
        { text: "Check (no build)", run: () => runJob("/api/check", { path }) }, "-");
    }
    items.push({ text: "Lint the project", run: () => lint(path) }, "-");
  } else if (!dir && isMarkdown(path)) {
    items.push({ text: "Open", run: () => openFile(path) },
      { text: "Preview as document", run: () => openFile(path).then(() => setPreview("document")) },
      { text: "Preview as slides", run: () => openFile(path).then(() => setPreview("deck")) },
      { text: "Preview as poster", run: () => openFile(path).then(() => setPreview("poster")) }, "-",
      { label: "Convert to" },
      ...Object.entries(info.convert).map(([kind, label]) => ({ text: label, run: () => convert(path, kind) })), "-",
      { text: "Lint", run: () => lint(path) }, "-");
  } else if (!dir) {
    items.push({ text: "Open", run: () => openFile(path) });
    if (/\.(html?|pdf|svg|png|jpe?g|gif|webp)$/i.test(path)) items.push({ text: "Open in a new tab", run: () => window.open("/raw/" + urlPath(path), "_blank") });
    items.push("-");
  } else {
    items.push({ text: "Lint this folder", run: () => lint(path) }, "-");
  }
  items.push(
    { text: "New file…", run: () => newFile(folder) },
    { text: "New folder…", run: () => newFolder(folder) },
    { text: "Upload files…", run: () => pickFiles(folder) },
    { text: "Upload a folder…", run: () => pickFiles(folder, true) }, "-",
    { text: dir ? "Download as zip" : "Download", run: () => (window.location.href = "/api/download" + q({ path })) },
    { text: "Rename…", run: () => rename(path) },
    { text: "Delete…", danger: true, run: () => remove(path, dir) },
  );
  showContext(event, items);
}

async function newProject() {
  const result = await dialog("New project", [
    { name: "name", label: "Folder name", placeholder: "pump-controller" },
    { name: "title", label: "Title (for py-doc init)", placeholder: "Pump Controller" },
    { type: "check", name: "init", label: "Start it with py-doc init (py-doc.yml and a first document)", value: true },
  ], "Create");
  if (!result || !result.name) return;
  const made = await api("POST", "/api/projects", { name: result.name, init: result.init, title: result.title || null });
  state.open.add(made.name); store.set("open", [...state.open]);
  if (made.job) { watchJob(made.job.id); showSide("jobs"); }
  await loadProjects();
}

async function newFile(folder) {
  const name = await ask("New file", `Name, in ${folder}`, "untitled.md");
  if (!name) return;
  const path = folder + "/" + name;
  const start = isMarkdown(name) ? `# ${name.replace(/\.(md|markdown)$/i, "").replace(/[-_]/g, " ")}\n\n` : "";
  await api("PUT", "/api/file", { path, text: start });
  state.open.add(folder); store.set("open", [...state.open]);
  await refreshProject(path);
  await openFile(path);
}

async function newFolder(folder) {
  const name = await ask("New folder", `Name, in ${folder}`, "");
  if (!name) return;
  await api("POST", "/api/mkdir", { path: folder + "/" + name });
  state.open.add(folder); store.set("open", [...state.open]);
  await refreshProject(folder);
}

async function rename(path) {
  const name = await ask("Rename", "New name", baseName(path));
  if (!name || name === baseName(path)) return;
  const target = (parentOf(path) ? parentOf(path) + "/" : "") + name;
  await api("POST", "/api/move", { source: path, target });
  retarget(path, target);
  if (!path.includes("/")) { if (state.open.delete(path)) state.open.add(target); store.set("open", [...state.open]); return loadProjects(); }
  await refreshProject(target);
}

async function remove(path, dir) {
  const ok = await confirmBox("Delete", `Delete ${dir ? "the folder" : ""} ${path}${dir ? " and everything in it" : ""}? This cannot be undone.`);
  if (!ok) return;
  await api("DELETE", "/api/path" + q({ path }));
  for (const doc of [...state.docs.values()]) if (doc.path === path || doc.path.startsWith(path + "/")) closeDoc(doc.path, true);
  if (!path.includes("/")) return loadProjects();
  await refreshProject(path);
}

/** A file or folder moved: the open files below it follow it. */
function retarget(from, to) {
  for (const doc of [...state.docs.values()]) {
    if (doc.path === from || doc.path.startsWith(from + "/")) {
      state.docs.delete(doc.path);
      doc.path = to + doc.path.slice(from.length);
      state.docs.set(doc.path, doc);
      if (state.active === from || (state.active && state.active.startsWith(from + "/"))) state.active = to + state.active.slice(from.length);
    }
  }
  renderTabs(); showActive();
}

// --- the editor ------------------------------------------------------------------------------

let editor = null;
const host = $("#editor-host");

function makeEditor() {
  if (window.CodeMirror) {
    editor = CodeMirror(host, {
      lineNumbers: true, lineWrapping: true, indentUnit: 2, tabSize: 4, indentWithTabs: false,
      extraKeys: {
        "Ctrl-S": () => saveActive(), "Cmd-S": () => saveActive(),
        Enter: "newlineAndIndentContinueMarkdownList",
        Tab: (cm) => cm.somethingSelected() ? cm.indentSelection("add") : cm.replaceSelection("  "),
      },
    });
    editor.on("change", (_cm, change) => { if (change.origin !== "setValue") edited(); });
    // Hover a directive to see what it does; one py-doc does not know says so
    editor.getWrapperElement().addEventListener("mouseover", (event) => {
      const span = event.target;
      if (!span.className || !/cm-pydoc-(directive|condition|unknown)/.test(span.className)) return;
      const tips = window.PYDOC_TOOLTIPS || {};
      span.title = tips[span.textContent] || `[[${span.textContent}]] is not a py-doc directive`;
    });
  } else {
    // The editor scripts come from a CDN; without them a plain text box still works
    const area = el("textarea", { class: "plain", spellcheck: "false" });
    host.append(area);
    editor = {
      plain: area, docs: new Map(),
      getValue: () => area.value, setValue: (v) => (area.value = v), focus: () => area.focus(),
      swapDoc: () => {}, setCursor: (line) => { const lines = area.value.split("\n").slice(0, line); area.focus(); area.selectionStart = area.selectionEnd = lines.join("\n").length; },
      getWrapperElement: () => area, refresh: () => {},
    };
    area.addEventListener("input", edited);
    area.addEventListener("keydown", (e) => { if ((e.ctrlKey || e.metaKey) && e.key === "s") { e.preventDefault(); saveActive(); } });
  }
  editor.getWrapperElement().hidden = true;
}

function modeFor(path) {
  if (isMarkdown(path)) {
    return CodeMirror.modes["pydoc-markdown"] ? "pydoc-markdown" : { name: "gfm", highlightFormatting: true, fencedCodeBlockHighlighting: true };
  }
  if (/\.ya?ml$/i.test(path)) return "yaml";
  if (/\.(json|js)$/i.test(path)) return { name: "javascript", json: /\.json$/i.test(path) };
  if (/\.py$/i.test(path)) return "python";
  if (/\.(svg|xml|html?|bpmn)$/i.test(path)) return "xml";
  return "text/plain";
}

async function openFile(path, line = null) {
  hideMenus();
  let doc = state.docs.get(path);
  if (!doc) {
    doc = { path, dirty: false, kind: isText(path) ? "text" : isImage(path) ? "image" : "binary" };
    if (doc.kind === "text") {
      try {
        const data = await api("GET", "/api/file" + q({ path }));
        doc.text = data.text; doc.modified = data.modified;
      } catch (error) {
        if (/not a text|too large/.test(error.message)) doc.kind = "binary"; else return fail(error);
      }
      if (doc.kind === "text" && window.CodeMirror) doc.editorDoc = CodeMirror.Doc(doc.text, modeFor(path));
    }
    state.docs.set(path, doc);
  }
  state.active = path;
  store.set("active", path);
  renderTabs();
  showActive();
  if (line && doc.kind === "text") jumpTo(line);
}

function showActive() {
  const doc = state.docs.get(state.active);
  const wrapper = editor.getWrapperElement();
  $("#welcome").hidden = !!doc;
  $("#editor-bar").hidden = !doc;
  const viewer = $("#viewer");
  viewer.hidden = true; wrapper.hidden = true;
  if (!doc) { stopPreview(); return; }
  $("#file-path").textContent = doc.path;
  const markdown = isMarkdown(doc.path) && doc.kind === "text";
  $("#preview-kind").disabled = !markdown;
  $("#convert-button").disabled = !markdown;
  $("#lint-file").disabled = !markdown;
  if (doc.kind === "text") {
    wrapper.hidden = false;
    if (doc.editorDoc) editor.swapDoc(doc.editorDoc); else { editor.plain && (editor.plain.value = doc.text); }
    editor.refresh();
    editor.focus();
  } else {
    viewer.hidden = false;
    const raw = "/raw/" + urlPath(doc.path);
    viewer.replaceChildren(
      doc.kind === "image" ? el("img", { src: raw + "?t=" + Date.now(), alt: doc.path }) : el("p", { class: "facts" }, "This file is not shown here."),
      el("div", {}, el("a", { href: "/api/download" + q({ path: doc.path }) }, el("button", {}, "Download")), " ",
        /\.(html?|pdf|svg)$/i.test(doc.path) ? el("a", { href: raw, target: "_blank" }, el("button", {}, "Open in a new tab")) : null),
    );
  }
  updateSaveState();
  const kind = markdown ? store.get("preview:" + doc.path, store.get("preview-default", "")) : "";
  $("#preview-kind").value = kind;
  if (kind) startPreview(doc.path, kind); else stopPreview();
}

function renderTabs() {
  const tabs = $("#tabs");
  tabs.replaceChildren(...[...state.docs.values()].map((doc) => el("div", {
    class: "tab" + (doc.path === state.active ? " active" : "") + (doc.dirty ? " dirty" : ""),
    title: doc.path, onclick: () => openFile(doc.path),
    onauxclick: (e) => { if (e.button === 1) closeDoc(doc.path); },
  }, baseName(doc.path), el("button", { class: "x", title: "Close", onclick: (e) => { e.stopPropagation(); closeDoc(doc.path); } }, el("span", {}, "×")))));
  store.set("tabs", [...state.docs.keys()]);
}

async function closeDoc(path, force = false) {
  const doc = state.docs.get(path);
  if (!doc) return;
  if (doc.dirty && !force) {
    await saveDoc(doc);
    if (doc.dirty) return;
  }
  state.docs.delete(path);
  if (state.active === path) state.active = [...state.docs.keys()].pop() || null;
  renderTabs();
  showActive();
  renderTree();
}

function jumpTo(line) {
  if (!editor.addLineClass) return editor.setCursor(line);
  const index = Math.max(0, line - 1);
  editor.setCursor({ line: index, ch: 0 });
  editor.scrollIntoView({ line: index, ch: 0 }, 120);
  const handle = editor.addLineClass(index, "background", "lint-line");
  setTimeout(() => editor.removeLineClass(handle, "background", "lint-line"), 2500);
  editor.focus();
}

let saveTimer = null;
function edited() {
  const doc = state.docs.get(state.active);
  if (!doc) return;
  if (!doc.dirty) { doc.dirty = true; renderTabs(); renderTree(); }
  updateSaveState();
  clearTimeout(saveTimer);
  if ($("#autosave").checked) saveTimer = setTimeout(() => saveDoc(doc), 900);
}

function updateSaveState() {
  const doc = state.docs.get(state.active), box = $("#save-state");
  if (!doc || doc.kind !== "text") { box.textContent = ""; return; }
  box.className = "save-state" + (doc.error ? " error" : doc.dirty ? " unsaved" : "");
  box.textContent = doc.error ? "Not saved: " + doc.error : doc.saving ? "Saving…" : doc.dirty ? "Unsaved" : "Saved";
}

const saveActive = () => { const doc = state.docs.get(state.active); if (doc) saveDoc(doc); };

async function saveDoc(doc) {
  if (doc.kind !== "text" || doc.saving) return;
  const text = doc.editorDoc ? doc.editorDoc.getValue() : (doc.path === state.active ? editor.getValue() : doc.text);
  doc.saving = true; updateSaveState();
  try {
    const result = await api("PUT", "/api/file", { path: doc.path, text });
    doc.text = text; doc.modified = result.modified; doc.error = null;
    const now = doc.editorDoc ? doc.editorDoc.getValue() : editor.getValue();
    doc.dirty = now !== text;
    if (doc.dirty && $("#autosave").checked) { clearTimeout(saveTimer); saveTimer = setTimeout(() => saveDoc(doc), 900); }
  } catch (error) { doc.error = error.message; }
  doc.saving = false;
  updateSaveState(); renderTabs(); renderTree();
}

/** After an upload or a build, a file open but not edited is read again if it changed on the server. */
async function reloadIfChanged(doc) {
  if (doc.kind !== "text" || doc.dirty) return;
  try {
    const data = await api("GET", "/api/file" + q({ path: doc.path }));
    if (data.modified !== doc.modified && data.text !== doc.text) {
      doc.text = data.text; doc.modified = data.modified;
      if (doc.editorDoc) doc.editorDoc.setValue(data.text); else if (doc.path === state.active) editor.setValue(data.text);
    }
  } catch { /* gone: left as it is */ }
}

window.addEventListener("beforeunload", (e) => { if ([...state.docs.values()].some((d) => d.dirty)) { e.preventDefault(); e.returnValue = ""; } });

$("#autosave").checked = store.get("autosave", true);
$("#autosave").addEventListener("change", () => { store.set("autosave", $("#autosave").checked); if ($("#autosave").checked) saveActive(); });

// --- the live preview ------------------------------------------------------------------------

const preview = { id: null, version: -1, timer: null, path: null, scroll: 0 };

$("#preview-kind").addEventListener("change", () => setPreview($("#preview-kind").value));

function setPreview(kind) {
  const doc = state.docs.get(state.active);
  if (!doc) return;
  $("#preview-kind").value = kind;
  store.set("preview:" + doc.path, kind);
  store.set("preview-default", kind);
  if (kind) { startPreview(doc.path, kind); showSide("preview"); } else stopPreview();
}

async function startPreview(path, kind) {
  if (state.docs.get(path)?.dirty) await saveDoc(state.docs.get(path));
  stopPreview(false);
  preview.path = path;
  try {
    const status = await api("POST", "/api/preview", { path, kind });
    if (preview.path !== path) return;
    preview.id = status.id; preview.version = -1; preview.scroll = store.get("scroll:" + status.id, 0);
    pollPreview();
  } catch (error) { showPreviewState(null, error.message); }
}

function stopPreview(clear = true) {
  clearTimeout(preview.timer);
  preview.id = null; preview.path = null;
  if (clear) {
    $("#preview-frame").src = "about:blank";
    $("#preview-error").hidden = true;
    $("#preview-state").textContent = "Choose a preview for a Markdown file.";
  }
}

async function pollPreview() {
  const id = preview.id;
  if (!id) return;
  try {
    const status = await api("GET", "/api/preview/" + id);
    if (preview.id !== id) return;
    if (status.version !== preview.version && status.ready) {
      preview.version = status.version;
      $("#preview-frame").src = `/preview/${id}?v=${status.version}#y=${preview.scroll}`;
    }
    showPreviewState(status, status.error);
  } catch (error) {
    if (preview.id !== id) return;
    if (/ended/.test(error.message) && preview.path) return startPreview(preview.path, $("#preview-kind").value);
    showPreviewState(null, error.message);
  }
  preview.timer = setTimeout(pollPreview, 900);
}

function showPreviewState(status, error) {
  const line = $("#preview-state");
  line.replaceChildren();
  if (status && status.building) line.append(el("span", { class: "spin" }), " Building…");
  else if (status) line.append(status.ready ? `Up to date · ${baseName(preview.path || "")}` : "Waiting for the first build…");
  const box = $("#preview-error");
  box.hidden = !error;
  if (error) box.textContent = error;
}

window.addEventListener("message", (event) => {
  if (event.source !== $("#preview-frame").contentWindow || !event.data) return;
  if (typeof event.data.pydocLoaded === "string") preview.loaded = { version: preview.version, title: event.data.pydocLoaded };
  if (typeof event.data.pydocScroll === "number") {
    preview.scroll = event.data.pydocScroll;
    if (preview.id) store.set("scroll:" + preview.id, preview.scroll);
  }
});

// --- converting, building, linting and jobs --------------------------------------------------

let info = { convert: {} };
const watching = new Map(); // job id -> { length, open }

function buildConvertMenu() {
  const menu = $("#convert-menu");
  menu.replaceChildren(...Object.entries(info.convert).map(([kind, label]) => el("button", { onclick: () => { hideMenus(); convert(state.active, kind); } }, label)));
}
$("#convert-button").addEventListener("click", () => { $("#convert-menu").hidden = !$("#convert-menu").hidden; });
$("#lint-file").addEventListener("click", () => state.active && lint(state.active));

async function saveAll(project) {
  for (const doc of state.docs.values()) if (doc.dirty && (!project || projectOf(doc.path) === project)) await saveDoc(doc);
}

async function convert(path, kind) {
  await saveAll(projectOf(path));
  const job = await api("POST", "/api/convert", { path, kind });
  watchJob(job.id, true);
  showSide("jobs");
  toast(`Converting ${baseName(path)} to ${info.convert[kind]}`);
}

async function build(project, format = null, lintFirst = false, site = false) {
  await saveAll(project);
  const job = await api("POST", "/api/build", { project, format, lint: lintFirst, site });
  watchJob(job.id, true);
  showSide("jobs");
}

async function runJob(url, body) {
  await saveAll(projectOf(body.path));
  const job = await api("POST", url, body);
  watchJob(job.id, true);
  showSide("jobs");
}

async function lint(path) {
  await saveAll(projectOf(path));
  const job = await api("POST", "/api/lint", { path });
  watchJob(job.id, false);
  $("#lint-summary").replaceChildren(el("span", { class: "spin" }), ` Linting ${path}…`);
  $("#lint-list").replaceChildren();
  showSide("lint");
}

function watchJob(id, open = false) {
  if (!watching.has(id)) watching.set(id, { length: 0, open });
  else if (open) watching.get(id).open = true;
  pollJobs(true);
}

let jobsTimer = null, jobsList = [];
async function pollJobs(now = false) {
  clearTimeout(jobsTimer);
  if (!now) { /* scheduled */ }
  try {
    jobsList = await api("GET", "/api/jobs");
    for (const job of jobsList) {
      const watched = watching.get(job.id);
      if (!watched) continue;
      const detail = await api("GET", `/api/jobs/${job.id}?since=${watched.length}`);
      watched.log = (watched.log || "") + detail.log;
      watched.length = detail.length;
      if (!["queued", "running"].includes(detail.state) && !watched.done) {
        watched.done = true;
        jobDone(detail);
      }
    }
    renderJobs();
  } catch { /* the server restarts: try again */ }
  const busy = jobsList.some((j) => ["queued", "running"].includes(j.state));
  const count = jobsList.filter((j) => ["queued", "running"].includes(j.state)).length;
  $("#jobs-running").hidden = !count; $("#jobs-running").textContent = count;
  jobsTimer = setTimeout(pollJobs, busy ? 1000 : 8000);
}

function jobDone(job) {
  const good = job.state === "ok";
  if (job.result && job.result.lint) showLint(job.result.lint, job);
  else if (/^Lint /.test(job.title) && !job.result) {
    $("#lint-summary").textContent = "The lint did not run: see Jobs.";
  }
  if (!(job.result && job.result.lint)) toast(`${job.title}: ${good ? "done" : job.state}`, !good);
  refreshProject(job.project);
  if (/^New project/.test(job.title)) loadProjects();
  for (const doc of state.docs.values()) if (projectOf(doc.path) === job.project) reloadIfChanged(doc);
}

function ago(seconds) {
  const s = Math.max(0, Date.now() / 1000 - seconds);
  if (s < 60) return Math.round(s) + " s ago";
  if (s < 3600) return Math.round(s / 60) + " min ago";
  return Math.round(s / 3600) + " h ago";
}

function renderJobs() {
  const box = $("#jobs");
  if (!jobsList.length) { box.replaceChildren(el("div", { class: "lint-summary" }, "No jobs yet. Build, convert or lint something.")); return; }
  const scrolls = new Map([...box.querySelectorAll("pre")].map((pre) => [pre.dataset.id, { top: pre.scrollTop, end: pre.scrollTop + pre.clientHeight >= pre.scrollHeight - 4 }]));
  box.replaceChildren(...jobsList.map((job) => {
    const watched = watching.get(job.id);
    const running = ["queued", "running"].includes(job.state);
    const took = job.started ? ((job.finished || Date.now() / 1000) - job.started).toFixed(0) + " s" : "";
    const head = el("div", { class: "job-head", onclick: () => { if (!watching.has(job.id)) watching.set(job.id, { length: 0, open: true }); else watching.get(job.id).open = !watching.get(job.id).open; pollJobs(true); } },
      el("span", { class: "state " + job.state }, running ? el("span", { class: "spin" }) : null, running ? "" : job.state),
      el("span", { class: "title", title: job.title }, job.title),
      el("span", { class: "time" }, took || ago(job.created)),
      running ? el("button", { class: "ghost", onclick: (e) => { e.stopPropagation(); api("POST", `/api/jobs/${job.id}/stop`).then(() => pollJobs(true)); } }, "Stop") : null);
    const node = el("div", { class: "job" }, head);
    const outputs = job.result && job.result.outputs;
    if (outputs) node.append(el("div", { class: "outputs" }, ...outputs.map((path) => el("span", {},
      el("a", { href: "/api/download" + q({ path }) }, "⬇ " + baseName(path)),
      /\.(html|pdf)$/i.test(path) ? el("a", { href: "/raw/" + urlPath(path), target: "_blank" }, " ↗ open") : null))));
    if (watched && watched.open) {
      const pre = el("pre", { "data-id": job.id }, watched.log || "");
      node.append(pre);
      const was = scrolls.get(job.id);
      requestAnimationFrame(() => { pre.scrollTop = !was || was.end ? pre.scrollHeight : was.top; });
    }
    return node;
  }));
}

function showLint(report, job) {
  const summary = report.summary || {};
  const issues = report.issues || [];
  $("#lint-summary").textContent = `${job.title.replace(/^Lint /, "")}: ${summary.files_scanned ?? "?"} file(s), ` +
    `${summary.error || 0} error(s), ${summary.warning || 0} warning(s), ${summary.info || 0} note(s)` +
    (summary.files_failed ? `, ${summary.files_failed} could not be read` : "");
  const order = { error: 0, warning: 1, info: 2 };
  issues.sort((a, b) => (order[a.severity] - order[b.severity]) || String(a.path).localeCompare(String(b.path)) || a.line - b.line);
  $("#lint-list").replaceChildren(...issues.map((issue) => el("div", { class: "issue", onclick: () => issue.path && openFile(issue.path, issue.line) },
    el("div", {}, el("span", { class: "sev " + issue.severity }, issue.severity), issue.message),
    issue.suggestion ? el("div", { class: "hint" }, "→ " + issue.suggestion) : null,
    el("div", { class: "where" }, `${issue.path || issue.file}:${issue.line}${issue.column ? ":" + issue.column : ""} · ${issue.rule}`))),
    ...(report.errors || []).map((e) => el("div", { class: "issue" }, el("span", { class: "sev error" }, "failed"), `${e.path || e.file}: ${e.message}`)));
  if (!issues.length && !(report.errors || []).length) $("#lint-list").append(el("div", { class: "lint-summary" }, "No issues. ✓"));
  showSide("lint");
}

// --- layout ----------------------------------------------------------------------------------

function showSide(name) {
  document.querySelectorAll(".side-tabs button").forEach((b) => b.classList.toggle("active", b.dataset.side === name));
  document.querySelectorAll(".side-body").forEach((b) => (b.hidden = b.dataset.body !== name));
  store.set("side", name);
}
document.querySelectorAll(".side-tabs button").forEach((b) => b.addEventListener("click", () => showSide(b.dataset.side)));
$("#jobs-badge").addEventListener("click", () => showSide("jobs"));

function splitters() {
  const layout = $("#layout");
  const widths = store.get("widths", {});
  if (widths.sidebar) layout.style.setProperty("--w-sidebar", widths.sidebar + "px");
  if (widths.side) layout.style.setProperty("--w-side", widths.side + "px");
  document.querySelectorAll(".splitter").forEach((bar) => {
    bar.addEventListener("pointerdown", (event) => {
      bar.setPointerCapture(event.pointerId);
      bar.classList.add("dragging");
      $("#preview-frame").style.pointerEvents = "none";
      const move = (e) => {
        if (bar.dataset.split === "sidebar") widths.sidebar = Math.max(180, Math.min(600, e.clientX));
        else widths.side = Math.max(260, Math.min(window.innerWidth - 400, window.innerWidth - e.clientX));
        layout.style.setProperty("--w-sidebar", (widths.sidebar || 280) + "px");
        if (widths.side) layout.style.setProperty("--w-side", widths.side + "px");
        editor && editor.refresh();
      };
      const up = () => { bar.classList.remove("dragging"); $("#preview-frame").style.pointerEvents = ""; bar.removeEventListener("pointermove", move); store.set("widths", widths); };
      bar.addEventListener("pointermove", move);
      bar.addEventListener("pointerup", up, { once: true });
    });
  });
}

function theme() {
  const apply = (value) => { if (value) document.documentElement.dataset.theme = value; else delete document.documentElement.dataset.theme; };
  apply(store.get("theme", null));
  $("#theme-toggle").addEventListener("click", () => {
    const dark = document.documentElement.dataset.theme ? document.documentElement.dataset.theme === "dark" : matchMedia("(prefers-color-scheme: dark)").matches;
    const next = dark ? "light" : "dark";
    store.set("theme", next); apply(next);
  });
}

// --- start -----------------------------------------------------------------------------------

$("#new-project").addEventListener("click", () => newProject().catch(fail));
$("#refresh").addEventListener("click", () => loadProjects().catch(fail));

(async function start() {
  theme();
  splitters();
  makeEditor();
  showSide(store.get("side", "preview"));
  try {
    info = await api("GET", "/api/info");
    $("#version").textContent = "v" + info.version;
    buildConvertMenu();
    await loadProjects();
    for (const path of store.get("tabs", [])) { try { await openFile(path); } catch { /* gone */ } }
    const active = store.get("active", null);
    if (active && state.docs.has(active)) await openFile(active);
  } catch (error) { fail(error); }
  pollJobs(true);
})();
