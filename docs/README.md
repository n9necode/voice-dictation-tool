# Voice Dictation Tool — Web (Windows + Android)

A cross-platform voice dictation app (PWA). Dictate speech to text, optionally clean it up with an LLM, then copy the result.

Runs on:

- **Windows** — Chrome or Edge (desktop, or installed as an app).
- **Android** — Chrome ("Add to Home screen" installs it as an app).

## Run locally

Speech recognition and the service worker require a secure context (HTTPS) or `localhost`. Serve this folder over HTTP:

```powershell
cd docs
python -m http.server 8000
```

Then open `http://localhost:8000`.

## Use

1. Open **Settings**, choose a cleanup provider (or **None** to dictate only), paste the key, and **Save key**.
2. Tap **Dictate** and speak — text appears live.
3. Tap **Clean up** to fix grammar/punctuation with the selected LLM.
4. **Copy** puts the text on the clipboard; **Speak** reads it aloud.

## Install as an app

- **Windows (Chrome/Edge):** open the URL, click the install icon in the address bar (or ⋮ → "Install Voice Dictation Tool").
- **Android (Chrome):** ⋮ → "Add to Home screen" → "Install".

## Notes

- Speech recognition uses the browser's built-in engine (no key needed). It defaults to `en-US`; change `recognition.lang` in `app.js` for another language.
- Keys are stored only in this browser's `localStorage`. Only the transcript you choose to send is uploaded to a cleanup provider.
- The legacy Chrome extension (`../manifest.json`, `sidepanel.*`) and Python plugin (`../skills/`) remain in the repo but are superseded by this web app for cross-platform use.
