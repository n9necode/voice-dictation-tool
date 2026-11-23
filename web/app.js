"use strict";

/* ---------- storage ---------- */
const store = {
  get(key, fallback = "") {
    try {
      const v = localStorage.getItem(key);
      return v === null ? fallback : v;
    } catch {
      return fallback;
    }
  },
  set(key, value) {
    try { localStorage.setItem(key, value); } catch { /* ignore */ }
  },
};

/* ---------- cleanup providers ---------- */
function cleanupPrompt(text) {
  return (
    "Clean up the following dictated text: fix grammar and punctuation, remove filler words " +
    "(um, uh, like, you know), and keep the original meaning. Reply with only the cleaned text.\n\n" +
    text
  );
}

async function handleHttp(res) {
  if (!res.ok) {
    let msg = res.status + " " + res.statusText;
    try {
      const body = await res.json();
      if (body && body.error && body.error.message) msg = body.error.message;
    } catch { /* ignore */ }
    throw new Error(msg);
  }
  return res.json();
}

async function chatCleanup(url, key, model, label, text) {
  if (!key) throw new Error("Paste your " + label + " API key in Settings.");
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: "Bearer " + key },
    body: JSON.stringify({ model, messages: [{ role: "user", content: cleanupPrompt(text) }] }),
  });
  const data = await handleHttp(res);
  const content = data && data.choices && data.choices[0] && data.choices[0].message && data.choices[0].message.content;
  const out = (typeof content === "string" ? content : "").trim();
  if (!out) throw new Error(label + " returned no text.");
  return out;
}

const PROVIDERS = {
  gemini: {
    label: "Gemini",
    keyField: "apiKey",
    async cleanup(text, key) {
      if (!key) throw new Error("Paste your Gemini API key in Settings.");
      const url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent?key=" + encodeURIComponent(key);
      const data = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ contents: [{ role: "user", parts: [{ text: cleanupPrompt(text) }] }] }),
      }).then(handleHttp);
      const parts = data && data.candidates && data.candidates[0] && data.candidates[0].content && data.candidates[0].content.parts;
      const out = (parts || []).map((p) => p.text).filter(Boolean).join("\n").trim();
      if (!out) throw new Error("Gemini returned no text.");
      return out;
    },
  },
  deepseek: { label: "DeepSeek", keyField: "deepseekApiKey", cleanup: (t, k) => chatCleanup("https://api.deepseek.com/chat/completions", k, "deepseek-chat", "DeepSeek", t) },
  groq: { label: "Groq", keyField: "groqApiKey", cleanup: (t, k) => chatCleanup("https://api.groq.com/openai/v1/chat/completions", k, "openai/gpt-oss-120b", "Groq", t) },
  openrouter: { label: "OpenRouter", keyField: "openrouterApiKey", cleanup: (t, k) => chatCleanup("https://openrouter.ai/api/v1/chat/completions", k, "google/gemma-4-31b-it:free", "OpenRouter", t) },
  none: { label: "None (dictate only)", keyField: null, cleanup: () => Promise.reject(new Error("No cleanup provider selected.")) },
};

/* ---------- DOM ---------- */
const els = {
  listen: document.getElementById("listen"),
  stop: document.getElementById("stop"),
  clean: document.getElementById("clean"),
  copy: document.getElementById("copy"),
  speak: document.getElementById("speak"),
  clear: document.getElementById("clear"),
  output: document.getElementById("output"),
  status: document.getElementById("status"),
  provider: document.getElementById("provider"),
  apiKey: document.getElementById("apiKey"),
  saveKey: document.getElementById("saveKey"),
};

function setStatus(msg, isError) {
  els.status.textContent = msg || "";
  els.status.className = isError ? "err" : "";
}

function currentProvider() {
  return PROVIDERS[els.provider.value] || PROVIDERS.none;
}

function refreshKeyInput() {
  const p = currentProvider();
  els.apiKey.placeholder = p.keyField ? "Paste " + p.label + " API key" : "";
  els.apiKey.value = p.keyField ? store.get(p.keyField) : "";
}

function populateProviders() {
  for (const id of Object.keys(PROVIDERS)) {
    const opt = document.createElement("option");
    opt.value = id;
    opt.textContent = PROVIDERS[id].label;
    els.provider.appendChild(opt);
  }
  const saved = store.get("provider");
  els.provider.value = PROVIDERS[saved] ? saved : "none";
  refreshKeyInput();
}

els.provider.addEventListener("change", () => {
  store.set("provider", els.provider.value);
  refreshKeyInput();
  setStatus("");
});

els.saveKey.addEventListener("click", () => {
  const p = currentProvider();
  if (!p.keyField) { setStatus("Select a provider first.", true); return; }
  store.set(p.keyField, els.apiKey.value.trim());
  setStatus(p.label + " key saved.");
});

/* ---------- speech recognition (STT) ---------- */
const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
let recognition = null;

function ensureRecognition() {
  if (recognition) return recognition;
  if (!SR) throw new Error("Speech recognition is not supported in this browser. Use Chrome or Edge.");
  recognition = new SR();
  recognition.lang = "en-US";
  recognition.interimResults = true;
  recognition.continuous = true;
  recognition.onresult = (event) => {
    let final = "";
    let interim = "";
    for (let i = event.resultIndex; i < event.results.length; i++) {
      const r = event.results[i];
      if (r.isFinal) final += r[0].transcript;
      else interim += r[0].transcript;
    }
    if (final) els.output.value = (els.output.value + " " + final).trim().replace(/\s+/g, " ");
    setStatus(interim ? "Listening… " + interim : "Listening…");
  };
  recognition.onerror = (event) => {
    if (event.error === "not-allowed") setStatus("Microphone blocked. Allow access, then retry.", true);
    else if (event.error !== "aborted") setStatus("Speech error: " + event.error, true);
  };
  recognition.onend = () => setStatus("");
  return recognition;
}

els.listen.addEventListener("click", () => {
  try {
    ensureRecognition().start();
    setStatus("Listening…");
  } catch (err) {
    setStatus(err.message || String(err), true);
  }
});

els.stop.addEventListener("click", () => {
  if (recognition) recognition.stop();
  speechSynthesis.cancel();
  setStatus("");
});

/* ---------- speak (TTS) ---------- */
els.speak.addEventListener("click", () => {
  const text = els.output.value.trim();
  if (!text) { setStatus("Nothing to speak.", true); return; }
  speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(text);
  u.lang = "en-US";
  speechSynthesis.speak(u);
});

/* ---------- copy ---------- */
async function copyText(text) {
  if (navigator.clipboard && window.isSecureContext) {
    await navigator.clipboard.writeText(text);
    return;
  }
  const ta = document.createElement("textarea");
  ta.value = text;
  document.body.appendChild(ta);
  ta.select();
  document.execCommand("copy");
  ta.remove();
}

els.copy.addEventListener("click", async () => {
  const text = els.output.value.trim();
  if (!text) { setStatus("Nothing to copy.", true); return; }
  try {
    await copyText(text);
    setStatus("Copied.");
  } catch (err) {
    setStatus("Copy failed: " + (err.message || err), true);
  }
});

/* ---------- clean up (LLM) ---------- */
els.clean.addEventListener("click", async () => {
  const text = els.output.value.trim();
  if (!text) { setStatus("Dictate something first.", true); return; }
  const p = currentProvider();
  const key = p.keyField ? store.get(p.keyField) : "";
  setStatus("Cleaning up…");
  els.clean.disabled = true;
  try {
    const cleaned = await p.cleanup(text, key);
    els.output.value = cleaned;
    setStatus("Done.");
  } catch (err) {
    setStatus("Cleanup failed: " + (err.message || err), true);
  } finally {
    els.clean.disabled = false;
  }
});

/* ---------- clear ---------- */
els.clear.addEventListener("click", () => {
  els.output.value = "";
  setStatus("");
});

/* ---------- init ---------- */
populateProviders();

if ("serviceWorker" in navigator && location.protocol !== "file:") {
  navigator.serviceWorker.register("sw.js").catch(() => {});
}
