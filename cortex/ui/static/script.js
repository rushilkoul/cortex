const landing = document.getElementById("landing");
const canvas = document.getElementById("canvas");
const canvasInner = document.getElementById("canvas-inner");
const composer = document.getElementById("composer");
const queryLanding = document.getElementById("query-landing");
const queryChat = document.getElementById("query-chat");
const statusEl = document.getElementById("status");
const greetingEl = document.getElementById("greeting");
const subtextEl = document.getElementById("subtext");

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

function scrollToBottom() {
  canvas.scrollTop = canvas.scrollHeight;
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

function renderResultsHtml(results) {
  if (!results || results.length === 0) return "";
  return results.map(r => {
    const isImage = r.type === "image";
    const thumb = isImage
      ? `<div class="result-thumb"><img src="file://${r.file_path}" loading="lazy"></div>`
      : `<div class="result-thumb text-icon">◆</div>`;
    const snippet = isImage
      ? ""
      : `<div class="result-snippet">${escapeHtml((r.content || "").slice(0, 140))}</div>`;
    return `
      <div class="result">
        ${thumb}
        <div class="result-body">
          <div class="result-path">${escapeHtml(r.file_path)}</div>
          ${snippet}
        </div>
      </div>
    `;
  }).join("");
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

  setStatus("thinking…", "thinking");

  const turn = document.createElement("div");
  turn.className = "turn";
  turn.innerHTML = `
    <div class="turn-query-row">
      <div class="turn-query">${escapeHtml(query)}</div>
    </div>
    <div class="turn-answer-row">
      <div class="turn-answer">
        <div class="answer-text typing"></div>
        <button class="results-toggle" style="display:none;">
          <span class="chevron">▸</span>
          <span class="toggle-label"></span>
        </button>
        <div class="turn-results"></div>
      </div>
    </div>
  `;
  canvasInner.appendChild(turn);
  scrollToBottom();

  const answerEl = turn.querySelector(".answer-text");
  const resultsEl = turn.querySelector(".turn-results");
  const toggleEl = turn.querySelector(".results-toggle");
  const stopThinking = startThinkingCycle(answerEl);

  toggleEl.addEventListener("click", () => {
    const expanded = resultsEl.classList.toggle("expanded");
    toggleEl.classList.toggle("expanded", expanded);
  });

  try {
    const { answer, results } = await window.pywebview.api.ask(query);
    stopThinking();
    answerEl.classList.remove("typing");
    answerEl.innerHTML = marked.parse(answer);
    resultsEl.innerHTML = renderResultsHtml(results);

    if (results && results.length > 0) {
      toggleEl.style.display = "inline-flex";
      toggleEl.querySelector(".toggle-label").textContent =
        `${results.length} source${results.length > 1 ? "s" : ""}`;
    }

    setStatus("ready", "ready");
  } catch (err) {
    stopThinking();
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