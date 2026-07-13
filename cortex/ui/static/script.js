const landing = document.getElementById("landing");
const canvas = document.getElementById("canvas");
const canvasInner = document.getElementById("canvas-inner");
const composer = document.getElementById("composer");
const queryLanding = document.getElementById("query-landing");
const queryChat = document.getElementById("query-chat");
const statusEl = document.getElementById("status");
const greetingEl = document.getElementById("greeting");
const subtextEl = document.getElementById("subtext");

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
  if (h < 5) return "Up late.";
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