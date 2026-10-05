# KaushalSetu — Gemini + Render

A standalone English/Hindi voice career counsellor. The Python server hosts the
webpage and calls Gemini securely. No database or training is required. This is
the chatbot supplied in the original ZIP, not a separate full platform with
accounts or admin panels.

## Deploy step by step

1. Extract this ZIP.
2. Create a GitHub repository and upload the extracted contents. Put
   `voice_model_server.py`, `gemini_backend.py`, and the HTML at the repository
   root. Upload the files, not the ZIP. Hidden `.gitignore` is recommended.
3. Create a Gemini API key at https://aistudio.google.com/apikey . Do not commit
   the key or put it in the HTML.
4. In https://dashboard.render.com select New > Web Service and connect your repo.
5. Choose Python runtime, your branch, and leave Root Directory blank.
6. Build command:
   `python -m compileall -q voice_model_server.py gemini_backend.py`
7. Start command:
   `python voice_model_server.py --host 0.0.0.0 --port $PORT`
8. Set Health Check Path to `/health`.
9. Add environment variable `GEMINI_API_KEY` with your actual key, and
   `GEMINI_MODEL` with `gemini-3.8-flash` (or a supported text model available
   to your key). Pick a Render instance plan that suits your demo.
10. Deploy. Open your service's HTTPS URL. The root `/` opens the chatbot.

Alternative: Render New > Blueprint can use the included `render.yaml` from
your GitHub repository. Supply GEMINI_API_KEY when requested and review the
instance plan before creation.

Render does not deploy a raw ZIP directly. Extract, upload to GitHub, then connect
that repository. No npm, pip packages, FastAPI, or Uvicorn is required.

## Verify the deployment

- `/health` returns healthy and `gemini_configured: true` after adding a key.
  This checks configuration, not key validity or Google availability.
- Ask: "I passed class 10. Suggest vocational careers." Then ask "Which one
  should I choose?" The latest 12 successful messages provide follow-up context.
- Switch to Hindi and ask a Hindi question. Switching language starts fresh
  conversation context, as does reloading the page.
- Allow microphone permission in a compatible browser. Try text input if speech
  recognition is unavailable. Hindi playback needs an available Hindi voice.
- Default mode calls Gemini. Errors remain visible and do not silently return
  preset answers. Demo mode can be selected explicitly; it uses old sample data.

## How it works

Browser speech recognition -> editable text -> POST /api/counsellor/chat ->
Gemini text response -> browser speech synthesis. Gemini handles reasoning and
answers; this package does not use Gemini Live audio or cloud TTS.

API request example:

```json
{"message":"Suggest ITI trades after class 10","language":"English","history":[]}
```

API key stays in server environment. History stays in page memory and is sent
to Gemini with requests, not stored by this server. Google and the hosting
provider handle requests under their own policies. The supplied career catalogue
is reference context only, not a live verified NQR database. No live search or
verified career-video retrieval is connected to Gemini.

## Local optional test

Python 3.10+ is recommended. No external libraries are required.

macOS/Linux:

```bash
export GEMINI_API_KEY='YOUR_KEY'
export GEMINI_MODEL='gemini-3.8-flash'
python3 voice_model_server.py --port 8000
```

Windows PowerShell:

```powershell
$env:GEMINI_API_KEY="YOUR_KEY"
$env:GEMINI_MODEL="gemini-3.8-flash"
python voice_model_server.py --port 8000
```

Open http://localhost:8000 . `.env.example` is documentation; the server does
not automatically load `.env` files. Windows launchers inherit environment
variables from the terminal that launches them.

## Troubleshooting

- API key required: Add GEMINI_API_KEY in Render and restart/redeploy.
- Gemini access denied: Check the key's project, permissions and API access.
- Model unavailable: Change GEMINI_MODEL to a model available to your key.
- Quota reached: Wait or review AI Studio quota and billing.
- Port deployment failure: Use exactly the start command above.
- No module named gemini_backend: Both Python files must be in the same folder.
- HTML missing: Keep the supplied HTML beside voice_model_server.py.
- Microphone unavailable: Use HTTPS, allow permission, and try Chrome/Edge.
- No Hindi voice: Install/enable a Hindi voice, or continue with text.

## Capacity and limitations

Threaded HTTP requests keep health/UI responsive during Gemini calls. At most
8 Gemini calls run concurrently in this process; excess calls receive a clear
busy response. Message size is capped at 4000 characters and request bodies at
64 KiB. Calls time out after 45 seconds. This is a demo deployment with no
login, database, per-user rate limits or distributed queue. Before broad public
use, add authentication and rate limiting to control paid API usage. Same-origin
checks alone are not access control. Browser voice support varies by device.

## Validation

Python syntax, JavaScript syntax and local HTTP integration have been checked.
Mock Gemini tests cover successful answers, history, missing key, invalid input,
upstream quota errors, and busy responses. A real Gemini call has not been tested
because no user API key was supplied. Health does not claim successful AI access.

Official documentation:
- https://ai.google.dev/gemini-api/docs/api-key
- https://ai.google.dev/gemini-api/docs/models
- https://ai.google.dev/gemini-api/docs/generate-content/text-generation
- https://render.com/docs/web-services
