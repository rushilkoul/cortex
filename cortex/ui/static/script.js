const landing = document.getElementById("landing");
const canvas = document.getElementById("canvas");
const canvasInner = document.getElementById("canvas-inner");
const composer = document.getElementById("composer");
const queryLanding = document.getElementById("query-landing");
const queryChat = document.getElementById("query-chat");
const statusEl = document.getElementById("status");
const greetingEl = document.getElementById("greeting");
const subtextEl = document.getElementById("subtext");
const themeBtn = document.getElementById("theme-btn");
const themeBtnLabel = document.getElementById("theme-btn-label");

const settingsBtn = document.getElementById("settings-btn");
const settingsOverlay = document.getElementById("settings-overlay");
const settingsClose = document.getElementById("settings-close");
const settingsList = document.getElementById("settings-list");
const settingsError = document.getElementById("settings-error");
const newPathInput = document.getElementById("new-path-input");
const addPathBtn = document.getElementById("add-path-btn");
const browsePathBtn = document.getElementById("browse-path-btn");
const settingsNavItems = document.querySelectorAll(".settings-nav-item");
const settingsSections = document.querySelectorAll(".settings-section");

let ready = false;
let busy = false;
let hasStartedChat = false;
function readThemePreference() {
  try {
    return localStorage.getItem("cortex-theme");
  } catch (e) {
    return null;
  }
}

function writeThemePreference(theme) {
  try {
    localStorage.setItem("cortex-theme", theme);
  } catch (e) {
    // Ignore storage failures in restricted WebView contexts.
  }
}

let themePreference = readThemePreference();
const themeQuery = window.matchMedia("(prefers-color-scheme: light)");

const SUBTEXTS = [
  "Ready to dive in?",
  "What's on your mind?",
  "Search for anything.",
  "What are we finding today?",
];

const THINKING_WORDS = [
  "Pondering",
  "Searching",
  "Recalling",
  "Assimilating",
  "Connecting the dots",
  "Digging through files",
];

function startThinkingCycle(el) {
  let i = 0;
  el.textContent = THINKING_WORDS[0] + "…";
  const interval = setInterval(() => {
    i = (i + 1) % THINKING_WORDS.length;
    el.textContent = THINKING_WORDS[i] + "…";
  }, 1400);
  return () => clearInterval(interval); // returns a stop function
}

function timeGreeting() {
  const h = new Date().getHours();
  if (h < 5) return "Up late";
  if (h < 12) return "Good morning";
  if (h < 18) return "Good afternoon";
  return "Good evening";
}

async function initGreeting() {
  let name = "";
  try {
    name = await window.pywebview.api.whoami();
  } catch (e) {
    name = "";
  }
  const greeting = timeGreeting();
  greetingEl.textContent = name ? `${greeting}, ${name}.` : `${greeting}.`;
  subtextEl.textContent = SUBTEXTS[Math.floor(Math.random() * SUBTEXTS.length)];
}

function setStatus(text, mode) {
  statusEl.textContent = text;
  statusEl.classList.remove("ready", "thinking");
  if (mode) statusEl.classList.add(mode);
}

function getSystemTheme() {
  return themeQuery.matches ? "light" : "dark";
}

function getActiveTheme() {
  return themePreference || getSystemTheme();
}

function applyTheme(theme) {
  const resolved = theme === "light" ? "light" : "dark";
  document.documentElement.dataset.theme = resolved;
  document.documentElement.style.colorScheme = resolved;
  if (themeBtnLabel) {
    themeBtnLabel.textContent = resolved === "dark" ? "light" : "dark";
  }
  if (themeBtn) {
    const nextTheme = resolved === "dark" ? "light" : "dark";
    themeBtn.title = `Switch to ${nextTheme} mode`;
    themeBtn.setAttribute("aria-label", `Switch to ${nextTheme} mode`);
  }
}

function setTheme(theme, persist = true) {
  const resolved = theme === "light" ? "light" : "dark";
  if (persist) {
    themePreference = resolved;
    writeThemePreference(resolved);
  }
  applyTheme(resolved);
}

function scrollToBottom() {
  canvas.scrollTop = canvas.scrollHeight;
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

function fileGlyph(ext) {
  const map = { ".md": "◆", ".markdown": "◆", ".pdf": "▤", ".py": "◇", ".txt": "▢" };
  return map[ext] || "◆";
}

function dedupeByFile(results) {
  const seen = new Map();
  for (const r of results) {
    const existing = seen.get(r.file_path);
    if (!existing || r.score < existing.score) {
      seen.set(r.file_path, r);
    }
  }
  return Array.from(seen.values());
}


function renderFoundStrip(results) {
  if (!results || results.length === 0) return "";

  const deduped = dedupeByFile(results);
  return deduped.map(r => {
    const isImage = r.type === "image";
    const fileName = r.file_path.split(/[\\/]/).pop();

    if (isImage) {
      return `
        <div class="found-card" data-path="${escapeHtmlAttr(r.file_path)}">
          ${r.thumbnail ? `<img src="${r.thumbnail}">` : ""}
          <div class="found-card-path-overlay">${escapeHtml(fileName)}</div>
        </div>
      `;
    }

    const ext = "." + (fileName.split(".").pop() || "");
    return `
      <div class="found-card text-card" data-path="${escapeHtmlAttr(r.file_path)}">
        <div class="file-glyph">${fileGlyph(ext)}</div>
        <div class="file-name">${escapeHtml(fileName)}</div>
      </div>
    `;
  }).join("");
}

function wireFoundCardClicks(container) {
  container.querySelectorAll(".found-card[data-path]").forEach(el => {
    el.addEventListener("click", () => {
      window.pywebview.api.open_file(el.dataset.path);
    });
  });
}

function enterChatMode() {
  if (hasStartedChat) return;
  hasStartedChat = true;
  landing.classList.add("hidden");
  canvas.classList.add("visible");
  composer.classList.add("visible");
  queryChat.focus();
}

async function runQuery(query) {
  if (!query.trim() || busy) return;
  busy = true;

  enterChatMode();

  queryLanding.disabled = true;
  queryChat.disabled = true;
  queryLanding.value = "";
  queryChat.value = "";

  setStatus("searching…", "thinking");

  const turn = document.createElement("div");
  turn.className = "turn";
  turn.innerHTML = `
    <div class="turn-query-row">
      <div class="turn-query">${escapeHtml(query)}</div>
    </div>
    <div class="turn-found" id="found-${Date.now()}" style="display:none;">
      <div class="found-label">Found</div>
      <div class="found-strip"></div>
    </div>
    <div class="turn-answer-row">
      <div class="turn-answer">
        <div class="answer-label"></div>
        <div class="answer-text typing"></div>
      </div>
    </div>
  `;
  canvasInner.appendChild(turn);
  scrollToBottom();

  const answerEl = turn.querySelector(".answer-text");
  const foundEl = turn.querySelector(".turn-found");
  const foundStripEl = turn.querySelector(".found-strip");

  let results = [];
  try {
    // phase 1 — sources appear immediately
    results = await window.pywebview.api.search_only(query);

    if (results && results.length > 0) {
      foundStripEl.innerHTML = renderFoundStrip(results);
      wireFoundCardClicks(foundStripEl);
      foundEl.style.display = "block";
      scrollToBottom();
    }

    setStatus("thinking…", "thinking");
    const stopThinking = startThinkingCycle(answerEl);

    // phase 2 — answer follows
    const answer = await window.pywebview.api.generate_answer(query, results);
    stopThinking();
    answerEl.classList.remove("typing");
    answerEl.innerHTML = marked.parse(answer.answer);

    setStatus("ready", "ready");
  } catch (err) {
    answerEl.classList.remove("typing");
    answerEl.textContent = "Something went wrong reaching Cortex.";
    setStatus("error", null);
    console.error(err);
  } finally {
    busy = false;
    queryLanding.disabled = false;
    queryChat.disabled = false;
    queryChat.focus();
    scrollToBottom();
  }
}

queryLanding.addEventListener("keydown", (e) => {
  if (e.key === "Enter") runQuery(queryLanding.value);
});
queryChat.addEventListener("keydown", (e) => {
  if (e.key === "Enter") runQuery(queryChat.value);
});

document.addEventListener("click", () => {
  if (busy) return;
  if (settingsOverlay.classList.contains("visible")) return;
  if (hasStartedChat) queryChat.focus();
  else queryLanding.focus();
});

window.addEventListener("pywebviewready", () => {
  ready = true;
  setStatus("ready", "ready");
  initGreeting();
  queryLanding.focus();
  window.pywebview.api.warm_up();
});

setTheme(getActiveTheme(), false);

if (!themePreference && themeQuery.addEventListener) {
  themeQuery.addEventListener("change", () => {
    applyTheme(getActiveTheme());
  });
}

if (themeBtn) {
  themeBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    setTheme(getActiveTheme() === "dark" ? "light" : "dark");
  });
}

setTimeout(() => {
  if (!ready) {
    setStatus("ready", "ready");
    initGreeting();
    queryLanding.focus();
    window.pywebview.api.warm_up();
  }
}, 3000);

// ============ SETTINGS PANEL ============

function escapeHtmlAttr(str) {
  return str.replace(/"/g, "&quot;");
}

async function loadDirectories() {
  settingsList.innerHTML = `<div class="settings-empty">loading…</div>`;
  try {
    const dirs = await window.pywebview.api.list_directories();
    renderDirectories(dirs);
  } catch (err) {
    settingsList.innerHTML = `<div class="settings-empty">couldn't load folders</div>`;
    console.error(err);
  }
}

function renderDirectories(dirs) {
  if (!dirs || dirs.length === 0) {
    settingsList.innerHTML = `<div class="settings-empty">no folders tracked yet</div>`;
    return;
  }
  settingsList.innerHTML = dirs.map(d => `
    <div class="settings-list-item">
      <span class="settings-list-path">${escapeHtml(d)}</span>
      <button class="settings-list-remove" data-path="${escapeHtmlAttr(d)}">remove</button>
    </div>
  `).join("");

  settingsList.querySelectorAll(".settings-list-remove").forEach(btn => {
    btn.addEventListener("click", async () => {
      const path = btn.dataset.path;
      btn.disabled = true;
      btn.textContent = "…";
      try {
        const res = await window.pywebview.api.remove_directory(path);
        if (res.ok) {
          loadDirectories();
        } else {
          settingsError.textContent = res.error;
        }
      } catch (err) {
        settingsError.textContent = "Failed to remove folder.";
        console.error(err);
      }
    });
  });
}

async function addDirectory() {
  const path = newPathInput.value.trim();
  if (!path) return;

  settingsError.textContent = "";
  addPathBtn.disabled = true;

  try {
    const res = await window.pywebview.api.add_directory(path);
    if (res.ok) {
      newPathInput.value = "";
      loadDirectories();
    } else {
      settingsError.textContent = res.error;
    }
  } catch (err) {
    settingsError.textContent = "Failed to add folder.";
    console.error(err);
  } finally {
    addPathBtn.disabled = false;
  }
}

function openSettings() {
  settingsOverlay.classList.add("visible");
  settingsError.textContent = "";
  loadDirectories();
  setTimeout(() => newPathInput.focus(), 50);
}

function closeSettings() {
  settingsOverlay.classList.remove("visible");
  if (hasStartedChat) queryChat.focus();
  else queryLanding.focus();
}

settingsBtn.addEventListener("click", (e) => {
  e.stopPropagation();
  openSettings();
});

settingsClose.addEventListener("click", (e) => {
  e.stopPropagation();
  closeSettings();
});

settingsOverlay.addEventListener("click", (e) => {
  if (e.target === settingsOverlay) closeSettings();
});

addPathBtn.addEventListener("click", (e) => {
  e.stopPropagation();
  addDirectory();
});

newPathInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") addDirectory();
});

browsePathBtn.addEventListener("click", async (e) => {
  e.stopPropagation();
  try {
    const path = await window.pywebview.api.pick_folder();
    if (path) {
      newPathInput.value = path;
      addDirectory();
    }
  } catch (err) {
    settingsError.textContent = "Couldn't open folder picker.";
    console.error(err);
  }
});

settingsNavItems.forEach(item => {
  item.addEventListener("click", (e) => {
    e.stopPropagation();
    const target = item.dataset.section;

    settingsNavItems.forEach(i => i.classList.remove("active"));
    item.classList.add("active");

    settingsSections.forEach(s => s.classList.remove("active"));
    document.getElementById(`section-${target}`).classList.add("active");
  });
});