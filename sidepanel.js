const logEl = document.getElementById("log");
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
let recognition = null;
let recorder = null;
let recordStream = null;
let recordChunks = [];

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function add(who, text, cls) {
  const line = document.createElement("div");
  line.className = cls;
  line.innerHTML = `<strong>${escapeHtml(who)}:</strong> ${escapeHtml(text)}`;
  logEl.appendChild(line);
}

function micSettingsUrl() {
  return (
    "chrome://settings/content/siteDetails?site=" +
    encodeURIComponent("chrome-extension://" + chrome.runtime.id)
  );
}

const history = [];
const PROVIDERS = {
  gemini: { label: "Gemini", keyField: "apiKey", placeholder: "Paste Gemini API key" },
  deepseek: { label: "DeepSeek", keyField: "deepseekApiKey", placeholder: "Paste DeepSeek API key" },
  groq: { label: "Groq", keyField: "groqApiKey", placeholder: "Paste Groq API key" },
  openrouter: { label: "OpenRouter", keyField: "openrouterApiKey", placeholder: "Paste OpenRouter API key" },
};
const KEY_FIELDS = ["provider", "apiKey", "deepseekApiKey", "groqApiKey", "openrouterApiKey"];

async function askGemini(stored) {
  if (!stored.apiKey) {
    throw new Error("Paste your Gemini API key, choose Gemini, and click Save key.");
  }

  const url =
    "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent?key=" +
    encodeURIComponent(stored.apiKey);

  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      contents: history.map((turn) => ({
        role: turn.role === "assistant" ? "model" : "user",
        parts: [{ text: turn.content }],
      })),
    }),
  });

  if (!res.ok) throw new Error(await apiError(res));
  return replyText(await res.json());
}

function choiceText(data) {
  const content = data?.choices?.[0]?.message?.content;
  if (typeof content === "string") return content.trim();
  if (Array.isArray(content)) {
    return content.map((part) => part.text || "").join("\n").trim();
  }
  return "";
}

async function askChat(url, key, model, label) {
  if (!key) throw new Error("Paste your " + label + " API key, choose " + label + ", and click Save key.");

  const res = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: "Bearer " + key,
    },
    body: JSON.stringify({
      model,
      messages: history.map((turn) => ({ role: turn.role, content: turn.content })),
    }),
  });

  if (!res.ok) throw new Error(await apiError(res));
  const text = choiceText(await res.json());
  if (!text) throw new Error(label + " returned no text.");
  return text;
}

async function ask(transcript) {
  const stored = await chrome.storage.local.get(KEY_FIELDS);
  const provider = stored.provider || "gemini";
  history.push({ role: "user", content: transcript });
  try {
    let reply;
    if (provider === "deepseek") {
      reply = await askChat("https://api.deepseek.com/chat/completions", stored.deepseekApiKey, "deepseek-chat", "DeepSeek");
    } else if (provider === "groq") {
      reply = await askChat("https://api.groq.com/openai/v1/chat/completions", stored.groqApiKey, "openai/gpt-oss-120b", "Groq");
    } else if (provider === "openrouter") {
      reply = await askChat("https://openrouter.ai/api/v1/chat/completions", stored.openrouterApiKey, "google/gemma-4-31b-it:free", "OpenRouter");
    } else {
      reply = await askGemini(stored);
    }
    history.push({ role: "assistant", content: reply });
    if (history.length > 20) history.splice(0, history.length - 20);
    return reply;
  } catch (err) {
    history.pop();
    throw err;
  }
}

function arrayBufferToBase64(buffer) {
  const bytes = new Uint8Array(buffer);
  let binary = "";
  for (let i = 0; i < bytes.length; i++) binary += String.fromCharCode(bytes[i]);
  return btoa(binary);
}

function encodeWav(audioBuffer) {
  const length = audioBuffer.length;
  const sampleRate = audioBuffer.sampleRate;
  const samples = new Float32Array(length);
  for (let channel = 0; channel < audioBuffer.numberOfChannels; channel++) {
    const data = audioBuffer.getChannelData(channel);
    for (let i = 0; i < length; i++) samples[i] += data[i] / audioBuffer.numberOfChannels;
  }

  const buffer = new ArrayBuffer(44 + length * 2);
  const view = new DataView(buffer);
  const write = (offset, text) => {
    for (let i = 0; i < text.length; i++) view.setUint8(offset + i, text.charCodeAt(i));
  };
  write(0, "RIFF");
  view.setUint32(4, 36 + length * 2, true);
  write(8, "WAVE");
  write(12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, 1, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  write(36, "data");
  view.setUint32(40, length * 2, true);
  let offset = 44;
  for (let i = 0; i < length; i++) {
    const sample = Math.max(-1, Math.min(1, samples[i]));
    view.setInt16(offset, sample < 0 ? sample * 0x8000 : sample * 0x7fff, true);
    offset += 2;
  }
  return buffer;
}

async function audioToWavBase64(blob) {
  const audioCtx = new AudioContext();
  try {
    const decoded = await audioCtx.decodeAudioData(await blob.arrayBuffer());
    return arrayBufferToBase64(encodeWav(decoded));
  } finally {
    await audioCtx.close();
  }
}

function replyText(data) {
  const parts = data?.candidates?.[0]?.content?.parts || [];
  const text = parts.map((part) => part.text).filter(Boolean).join("\n").trim();
  if (text) return text;
  const reason = data?.candidates?.[0]?.finishReason || data?.promptFeedback?.blockReason;
  throw new Error(reason ? "Gemini did not reply: " + reason : "Gemini returned no text.");
}

async function apiError(res) {
  const raw = await res.text();
  try {
    const body = JSON.parse(raw);
    if (body.error && body.error.message) return body.error.message;
  } catch (err) {
    return raw.slice(0, 300);
  }
  return raw.slice(0, 300);
}

async function askGeminiAudio(blob) {
  const { apiKey } = await chrome.storage.local.get("apiKey");
  if (!apiKey) {
    throw new Error("Paste your Gemini API key and click Save key.");
  }

  const url =
    "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent?key=" +
    encodeURIComponent(apiKey);
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 45000);

  try {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      signal: controller.signal,
      body: JSON.stringify({
        contents: [
          {
            parts: [
              {
                inlineData: {
                  mimeType: "audio/wav",
                  data: await audioToWavBase64(blob),
                },
              },
              {
                text: "The user just spoke this audio. Reply in one or two short sentences that can be read aloud.",
              },
            ],
          },
        ],
      }),
    });

    if (!res.ok) throw new Error(await apiError(res));
    return replyText(await res.json());
  } catch (err) {
    if (err.name === "AbortError") throw new Error("Gemini took too long. Click Listen and try a shorter sentence.");
    throw err;
  } finally {
    clearTimeout(timer);
  }
}

function speak(text) {
  const utter = new SpeechSynthesisUtterance(text);
  utter.lang = "en-US";
  speechSynthesis.cancel();
  speechSynthesis.speak(utter);
}

function ensureRecognition() {
  if (recognition) return recognition;
  if (!SpeechRecognition) {
    throw new Error("Speech recognition is not supported in this browser.");
  }

  recognition = new SpeechRecognition();
  recognition.lang = "en-US";
  recognition.interimResults = false;
  recognition.continuous = false;

  recognition.onresult = async (event) => {
    const transcript = event.results[0][0].transcript;
    add("You", transcript, "you");
    try {
      const reply = await ask(transcript);
      add("AI", reply, "ai");
      speak(reply);
    } catch (err) {
      add("Error", err.message || String(err), "err");
    }
  };

  recognition.onerror = (event) => {
    if (event.error !== "not-allowed") {
      if (event.error !== "aborted") add("Error", event.error || "Speech recognition error", "err");
      return;
    }
    startRecording().catch((err) => {
      add("Error", err.message || String(err), "err");
    });
  };

  return recognition;
}

async function micPermission() {
  try {
    const status = await navigator.permissions.query({ name: "microphone" });
    return status.state;
  } catch (err) {
    return "prompt";
  }
}

function openMicWindow() {
  return chrome.windows.create({
    url: chrome.runtime.getURL("sidepanel.html?mic=1"),
    type: "popup",
    width: 420,
    height: 240,
    focused: true,
  });
}

async function startRecording() {
  if (recorder && recorder.state === "recording") return;

  const perm = await micPermission();
  if (perm === "denied") {
    add(
      "Error",
      "Microphone is still blocked. Open this address in a new tab, set Microphone to Allow, then click Listen again: " +
        micSettingsUrl(),
      "err"
    );
    return;
  }
  if (perm !== "granted") {
    add("Saved", "Click Allow in the small microphone window, then click Listen again.", "ai");
    await openMicWindow();
    return;
  }

  const { apiKey } = await chrome.storage.local.get("apiKey");
  if (!apiKey) {
    add("Error", "Paste your Gemini API key and click Save key.", "err");
    return;
  }

  recordStream = await navigator.mediaDevices.getUserMedia({ audio: true });
  recordChunks = [];
  const activeRecorder = new MediaRecorder(recordStream);
  recorder = activeRecorder;
  const chunks = recordChunks;
  const stream = recordStream;
  activeRecorder.ondataavailable = (event) => {
    if (event.data.size) chunks.push(event.data);
  };
  activeRecorder.onstop = async () => {
    const blob = new Blob(chunks, { type: activeRecorder.mimeType || "audio/webm" });
    stream.getTracks().forEach((track) => track.stop());
    if (recordStream === stream) recordStream = null;
    if (!blob.size) {
      add("Error", "No speech was recorded. Click Listen and speak, then click Stop.", "err");
      return;
    }
    add("Saved", "Waiting for Gemini...", "ai");
    try {
      const reply = await askGeminiAudio(blob);
      add("AI", reply, "ai");
      speak(reply);
    } catch (err) {
      add("Error", err.message || String(err), "err");
    }
  };
  recorder.start();
  add("Saved", "Listening. Speak, then click Stop.", "ai");
}

function setupMicWindow() {
  document.body.replaceChildren();
  const note = document.createElement("p");
  note.textContent = "Click Allow when Chrome asks for the microphone.";
  document.body.appendChild(note);

  navigator.mediaDevices
    .getUserMedia({ audio: true })
    .then((stream) => {
      stream.getTracks().forEach((track) => track.stop());
      note.textContent = "Microphone allowed. You can close this window.";
      chrome.runtime.sendMessage({ type: "mic-granted" });
      window.close();
    })
    .catch(() => {
      note.textContent =
        "Chrome did not show Allow. Open this address in a new tab and set Microphone to Allow: " +
        micSettingsUrl();
    });
}

function setupPanel() {
  const keyInput = document.getElementById("apiKey");
  const providerEl = document.getElementById("provider");

  function showKey(stored) {
    const provider = PROVIDERS[providerEl.value] || PROVIDERS.gemini;
    keyInput.placeholder = provider.placeholder;
    keyInput.value = stored[provider.keyField] || "";
  }

  chrome.storage.local.get(KEY_FIELDS, (stored) => {
    providerEl.value = PROVIDERS[stored.provider] ? stored.provider : "gemini";
    showKey(stored);
  });

  providerEl.addEventListener("change", async () => {
    const stored = await chrome.storage.local.get(KEY_FIELDS);
    await chrome.storage.local.set({ provider: providerEl.value });
    history.length = 0;
    showKey(stored);
    const provider = PROVIDERS[providerEl.value] || PROVIDERS.gemini;
    add("Saved", provider.label + " selected.", "ai");
  });

  chrome.runtime.onMessage.addListener((msg) => {
    if (msg && msg.type === "mic-granted") {
      add("Saved", "Microphone allowed. Click Listen, speak, then click Stop.", "ai");
    }
  });

  document.getElementById("saveKey").addEventListener("click", async () => {
    const apiKey = keyInput.value.trim();
    const provider = PROVIDERS[providerEl.value] || PROVIDERS.gemini;
    if (!apiKey) {
      add("Error", "Paste your " + provider.label + " API key first.", "err");
      return;
    }
    await chrome.storage.local.set({ provider: providerEl.value, [provider.keyField]: apiKey });
    add("Saved", "API key saved.", "ai");
  });

  document.getElementById("listen").addEventListener("click", () => {
    try {
      ensureRecognition().start();
    } catch (err) {
      startRecording().catch((recordErr) => {
        add("Error", recordErr.message || err.message || String(recordErr), "err");
      });
    }
  });

  document.getElementById("stop").addEventListener("click", () => {
    if (recognition) recognition.stop();
    if (recorder && recorder.state === "recording") recorder.stop();
    speechSynthesis.cancel();
  });
}

if (new URLSearchParams(location.search).get("mic") === "1") {
  setupMicWindow();
} else {
  setupPanel();
}
