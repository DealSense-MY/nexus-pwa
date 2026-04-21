---
name: nexus-pwa
description: >
  Sistem pembangunan, deployment, dan penyelenggaraan NEXUS AI PWA milik Aliff (DealSense-MY).
  Guna skill ini bila Aliff minta tambah feature, fix bug, upgrade kod, deploy semula,
  atau tanya pasal mana-mana bahagian sistem NEXUS. Merangkumi chat AI pelbagai mod,
  Perak Kamuniti FB agent, auto-scheduler, password protection, image upload, cache system,
  dan Cloudflare Pages deployment.
---

# NEXUS PWA — Complete System Reference

## PLATFORM & HOSTING

- **Live URL**: `nexus-pwa-enx.pages.dev`
- **GitHub Repo**: `github.com/DealSense-MY/nexus-pwa`
- **Hosting**: Cloudflare Pages (unlimited bandwidth, free)
- **API Proxy**: Cloudflare Pages Function `functions/api/claude.js`
- **Scheduler**: GitHub Actions `generate_post.py` — jam 8 pagi Malaysia (00:00 UTC)
- **Password default**: `nexus2024`

## REPO STRUCTURE

```
nexus-pwa/
├── .github/workflows/generate-post.yml
├── functions/api/claude.js          ← Cloudflare API proxy
├── icons/icon-192.png + icon-512.png
├── index.html                       ← Semua PWA dalam satu file
├── manifest.json
├── sw.js                            ← Service Worker cache v5
├── queue.json                       ← Perak post queue
└── generate_post.py                 ← Scheduler Python script
```

## API SETUP

```javascript
// Cloudflare Function: functions/api/claude.js
// Endpoint: POST /api/claude
// API key dari Cloudflare env var: ANTHROPIC_API_KEY
// JANGAN expose API key dalam index.html

export async function onRequestPost(context) {
  const apiKey = context.env.ANTHROPIC_API_KEY;
  const body = await context.request.json();
  delete body.apiKey;
  const response = await fetch('https://api.anthropic.com/v1/messages', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'x-api-key': apiKey, 'anthropic-version': '2023-06-01' },
    body: JSON.stringify(body)
  });
  const data = await response.json();
  return new Response(JSON.stringify(data), {
    status: response.status,
    headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' }
  });
}

export async function onRequestOptions() {
  return new Response(null, { status: 200, headers: { 'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Methods': 'POST, OPTIONS', 'Access-Control-Allow-Headers': 'Content-Type' }});
}
```

## CHAT SYSTEM

```javascript
// Per-mode history — WAJIB guna ini, JANGAN satu history untuk semua mod
let chatHistory = { general:[], trading:[], social:[], email:[], news:[], agama:[], perak:[] };
let chatMessages = { general:[], trading:[], social:[], email:[], news:[], agama:[], perak:[] };

// Cache FIFO dengan timestamp
const CACHE_KEY = 'nexus_ai_cache';
const CACHE_MAX = 50;
// Format entry: cache[normalizeKey(text)] = { data: reply, time: Date.now() }
// normalizeKey: text.toLowerCase().trim().replace(/\s+/g,' ')
// FIFO: sort by .time, buang oldest bila > 50

// Persist ke localStorage
const HISTORY_KEY = 'nexus_chat_history';
const MESSAGES_KEY = 'nexus_chat_messages';
// Panggil persistChatHistory() setiap kali ada message baru

// Offline fallback
// API fail → check cache → tunjuk "(Cache) {reply}"
// Tiada cache → "⚠️ Offline mode: data tidak tersedia"
```

## MOD CHAT

| Mod | Key | Notes |
|-----|-----|-------|
| 🤖 Umum | `general` | General assistant |
| 📈 Trading | `trading` | Forex/crypto analyst |
| 📱 Sosial | `social` | Social media content |
| ✉️ Emel | `email` | Email writer |
| 🗞️ Berita | `news` | News + web search |
| 🕌 Agama | `agama` | Islamic knowledge |
| 🏔️ Perak | `perak` | FB post generator — web search WAJIB |

## PERAK KAMUNITI AGENT

Format post WAJIB 3 bahagian:
1. **BAHAGIAN 1** — Berita Perak terkini + link sumber berita
2. **BAHAGIAN 2** — Kisah viral Perak + link sumber
3. **BAHAGIAN 3** — Jawatan kosong dalam Perak SAHAJA + link apply (JobStreet/Maukerja/Indeed)

Daerah Perak yang diterima: Ipoh, Taiping, Teluk Intan, Manjung, Kampar, Kuala Kangsar, Gerik, Lumut, Batu Gajah, Sitiawan, Parit Buntar.
TOLAK jawatan luar Perak (KL, Selangor, Johor dll).

Approval dashboard auto-popup bila post dijana.
Queue disimpan dalam `queue.json` GitHub, diambil via raw.githubusercontent.com.
FAB button 📅 muncul dalam Mod Perak sahaja.

## GITHUB ACTIONS SCHEDULER

```yaml
# .github/workflows/generate-post.yml
on:
  schedule:
    - cron: '0 0 * * *'   # 8am Malaysia
  workflow_dispatch:
jobs:
  generate:
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v4
      - env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: python3 generate_post.py
      - run: |
          git config user.name "NEXUS Bot"
          git config user.email "nexus@dealsense.my"
          git add queue.json
          git diff --staged --quiet || git commit -m "Auto post Perak $(date +'%d/%m/%Y')"
          git push
```

## GENERATE_POST.PY FEATURES

- Model: `claude-haiku-4-5-20251001`
- Web search tool: `{"type": "web_search_20250305", "name": "web_search"}`
- Retry 3x, delay 5 saat
- Validasi: min 3 URL, semua BAHAGIAN 1/2/3 ada, link kerja dari trusted platforms
- Trusted platforms: `jobstreet.com`, `maukerja.my`, `indeed.com`
- Duplicate detection: compare 100 chars pertama dengan post terbaru
- Log ke `log.txt`
- Queue max 30 posts dalam `queue.json`

## PASSWORD SYSTEM

```javascript
const DEFAULT_PW = 'nexus2024';
// Simpan: localStorage.setItem('nexus_pw', newPassword)
// Auth: localStorage.setItem('nexus_auth', '1')
// Tukar dalam ⚙️ Settings → Password lama + baru
// Log keluar: localStorage.removeItem('nexus_auth')
```

## IMAGE/FILE UPLOAD

```javascript
// Butang 📎 → upload JPG/PNG/PDF
// Butang 📷 → camera capture
// Drag & drop ke textarea
// Convert ke base64, hantar dalam API
// Image: { type:'image', source:{ type:'base64', media_type, data } }
// PDF: { type:'document', source:{ type:'base64', media_type:'application/pdf', data } }
```

## DESIGN SYSTEM

```css
:root {
  --bg: #080c10;
  --surface: #0d1117;
  --surface2: #131920;
  --border: #1e2d3d;
  --accent: #00e5ff;    /* Cyan — warna utama */
  --accent2: #7c3aed;
  --accent3: #10b981;
  --danger: #ef4444;
  --text: #e2e8f0;
  --muted: #4a5568;
}
/* Fonts: Syne (heading), DM Mono (body) */
/* Grid background: subtle cyan pattern */
```

## MODEL YANG DIGUNAKAN

| Tujuan | Model |
|--------|-------|
| Chat dalam app | `claude-sonnet-4-20250514` |
| Scheduler (generate_post.py) | `claude-haiku-4-5-20251001` |

## CARA DEPLOY SEMULA

1. Edit fail dalam GitHub
2. Cloudflare auto-deploy dalam 1-2 minit
3. Manual: Cloudflare → nexus-pwa-enx → Deployments → Retry

## CARA TAMBAH FEATURE BARU

1. Edit `index.html` — semua CSS/JS/HTML dalam satu fail
2. Endpoint baru → tambah fail dalam `functions/api/`
3. Commit ke GitHub → Cloudflare auto-deploy

## ISSUES & FIXES (RUJUKAN)

| Issue | Fix |
|-------|-----|
| CORS error / "Tiada sambungan" | Update `sw.js` cache version, guna Cloudflare function proxy |
| "API key tidak dijumpai" | Redeploy selepas tambah env var dalam Cloudflare |
| Chat mix antara mod | Guna per-mode `chatHistory` dan `chatMessages` |
| Netlify bandwidth habis | Migrate ke Cloudflare Pages (unlimited free) |
| GitHub Actions YAML error | Pisahkan prompt ke `generate_post.py` berasingan |
| Job vacancy luar Perak | Ketatkan prompt dengan senarai daerah Perak |
| Service worker cache lama | Naikkan CACHE_NAME version (nexus-v5) |
