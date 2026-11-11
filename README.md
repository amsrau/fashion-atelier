# Atelier 30 — Fashion Theme Configurator & Tactile Studio

Live menswear lookbook analyzer & interactive outfit configurator synthesized from a 30-day audit (`Oct 12 – Nov 11, 2026`) across 6 menswear X channels (`7` handles: `@MensFits_`, `@MensCanvas`, `@_menstylish`, `@gentelmenoutfit`, `@Mensoutfitpxs`, `@Elegantmanx`, `@manly_talks`).

## Live Hosted Features (Static / GitHub Pages Ready)
- **Interactive Shop & Configure Studio (`index.html`):**
  1. **34 Pre-Shot AI Studio Photos** across all **9 Fashion Theme Buckets** and curated style formulas (`assets/renders/`).
  2. **Instant `0ms` Live Fabric Mixer:** Real-time `<canvas>` compositor layering 7 macro photographed fabrics (`Hopsack Wool`, `Merino Knit`, `Oxford Cotton`, `Selvedge Denim`, `Irish Linen`, `Brushed Suede`, `Burnished Calfskin`).
  3. **Matched Real X Channel Lookbooks:** Instant search across **829** deduplicated X outfit photos & **6** editorial infographics (`assets/looks/` + `data/lookbook_catalog.json`).
  4. **Share / Suggest Look Links (`#look=...`):** Encode any custom outfit, fabric mix, colors, and an optional friend suggestion note directly into a shareable URL link.
  5. **Persistent Fitting Room Shortlist:** Save and compare looks side-by-side in the browser.

## Optional Local Custom AI Render Server
To generate bespoke AI studio photography (`Render Custom AI Shoot (~6s)`) for arbitrary off-preset color/fabric combinations locally, set `GEMINI_API_KEY` in `.env` and start `server.py`:

```bash
python server.py
# Open http://127.0.0.1:8765/
```

## Repository Layout
- `index.html` — Static studio web app (built by `scripts/build_studio_v2.py`).
- `server.py` — Optional local threaded HTTP server & `POST /api/render-look` endpoint.
- `data/fashion_intel.json` — Theme taxonomy, channel duplication breakdown, top formulas, and interactive style matrices.
- `data/lookbook_catalog.json` — Indexed metadata for all `1,218` deduplicated X photos & infographics.
- `assets/looks/` — Deduplicated X outfit photos & infographic guides (`1,218` images).
- `assets/fabrics/` — Macro neutral textile grain plates (`7` weaves).
- `assets/renders/` — Curated Theme & Formula studio boards (`34` pre-rendered looks).
- `AUDIT_REPORT.md` — Written 30-day empirical research audit.
