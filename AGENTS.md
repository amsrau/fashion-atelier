# Atelier 30 Project Instructions

Canonical **Atelier 30 Menswear Lookbook & E-Tailer Studio** workspace synthesized from a 30-day X bookmarks audit (`Oct 12 – Nov 11, 2026`).

## Core Entrypoints
- **Static Web App:** [`index.html`](index.html) works directly on GitHub Pages and any static HTTP server (`34` pre-rendered studio boards, `0ms` macro fabric mixer, `829` searchable X looks, `#look=...` share links).
- **Local Server + Live Custom AI Renderer:** [`server.py`](server.py) serves static assets, `GET /api/health`, and `POST /api/render-look`.
- **HTML Build Generator:** [`scripts/build_studio_v2.py`](scripts/build_studio_v2.py) compiles data bundles into [`index.html`](index.html) (and optionally `ATELIER_ARTIFACT_OUT`).

## Engineering & Security Conventions
- **Keep API keys server-side only:** [`server.py`](server.py) reads `GEMINI_API_KEY` from `.env` or environment variables. Never commit `.env` or embed keys in client JS.
- **Rebuild workflow:** Edit [`scripts/build_studio_v2.py`](scripts/build_studio_v2.py) cleanly and run it rather than hand-patching generated output in [`index.html`](index.html).
