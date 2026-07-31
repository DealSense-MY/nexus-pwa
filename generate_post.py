import urllib.request
import urllib.error
import json
import os
import re
import time
from datetime import datetime
from urllib.parse import urlparse

# ─── CONFIG ───────────────────────────────────────────
API_KEY       = os.environ.get("ANTHROPIC_API_KEY", "")
API_URL       = "https://api.anthropic.com/v1/messages"
MODEL         = "claude-haiku-4-5-20251001"
MAX_TOKENS    = 2000
QUEUE_FILE    = "queue.json"
LOG_FILE      = "log.txt"
MAX_QUEUE     = 30
MAX_RETRIES   = 3
RETRY_DELAY   = 5
MIN_URLS      = 3
MIN_LENGTH    = 200
TRUSTED_JOBS  = ["jobstreet.com", "maukerja.my", "indeed.com"]
REQUIRED_SECTIONS = ["BAHAGIAN 1", "BAHAGIAN 2", "BAHAGIAN 3"]
VACANCY_FIELDS = ["employer", "job_title", "location", "direct_vacancy_url", "checked_date"]
GENERIC_JOB_URL_MARKERS = ["jobsearch", "search", "keyword", "location", "jobs/in-", "-jobs", "q-", "l-"]


class ConfigurationError(Exception):
    """A credential or permission error that must not be retried."""

# ─── LOGGING ──────────────────────────────────────────
def log(message, level="INFO"):
    timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    entry = f"[{timestamp}] [{level}] {message}"
    print(entry)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(entry + "\n")
    except Exception:
        pass

# ─── PROMPT ───────────────────────────────────────────
def build_prompt():
    today = datetime.now().strftime("%A, %d %B %Y")
    return (
        "Hari ini " + today + ". Jana satu post Facebook untuk group Perak Kamuniti Malaysia.\n\n"
        "ARAHAN PENTING:\n"
        "- Gunakan web search untuk mencari maklumat TERKINI dan BENAR\n"
        "- JANGAN cipta atau reka link palsu\n"
        "- Hanya sertakan URL BENAR bermula dengan https://\n"
        "- Jika tiada data dijumpai, tulis: Tiada data dijumpai hari ini\n"
        "- Semua jawatan MESTI dalam Negeri Perak SAHAJA\n"
        "- TOLAK jawatan di luar Perak (KL, Selangor, Johor dll)\n"
        "- Link kerja MESTI dari JobStreet, Maukerja atau Indeed sahaja\n\n"
        "FORMAT POST (ikut TEPAT):\n\n"
        "PERAK KAMUNITI - UPDATE HARI INI\n"
        "================================\n\n"
        "BAHAGIAN 1: BERITA PERAK HARI INI\n"
        "--------------------------------\n"
        "Cari 1 berita TERKINI dan BENAR dari Perak Malaysia hari ini.\n"
        "Tulis ringkasan 3-4 ayat dengan emoji menarik.\n"
        "Wajib: URL artikel BENAR dari portal berita (https://...)\n"
        "Hashtag berkaitan berita.\n\n"
        "BAHAGIAN 2: KISAH VIRAL PERAK\n"
        "--------------------------------\n"
        "Cari 1 kisah viral atau menarik BENAR dari Perak.\n"
        "Tulis gaya santai dan menarik.\n"
        "URL sumber jika ada (https://...)\n"
        "Hashtag berkaitan.\n\n"
        "BAHAGIAN 3: JAWATAN KOSONG DI PERAK\n"
        "--------------------------------\n"
        "Cari 2-3 jawatan TERKINI dalam Negeri Perak SAHAJA.\n"
        "Daerah Perak: Ipoh, Taiping, Teluk Intan, Manjung, Kampar, Kuala Kangsar, Gerik, Lumut, Batu Gajah, Sitiawan, Parit Buntar.\n"
        "Untuk setiap jawatan:\n"
        "Syarikat: [nama]\n"
        "Jawatan: [nama jawatan]\n"
        "Lokasi: [daerah dalam Perak]\n"
        "Gaji: [julat gaji jika ada]\n"
        "Apply: [URL dari JobStreet ATAU Maukerja ATAU Indeed - WAJIB]\n\n"
        "BUKTI JAWATAN (WAJIB untuk SETIAP jawatan, ikut label tepat):\n"
        "Employer: [nama syarikat sebenar]\n"
        "Job title: [nama jawatan sebenar]\n"
        "Location: [daerah, Perak]\n"
        "Direct vacancy URL: [URL terus ke iklan jawatan, bukan halaman carian]\n"
        "Checked date: [YYYY-MM-DD]\n"
        "Jika mana-mana bukti ini tidak lengkap atau URL bukan iklan terus, tulis UNVERIFIED dan jangan reka maklumat.\n\n"
        "HASHTAG AKHIR:\n"
        "#PerakKamuniti #Perak #Malaysia #InfoPerak #KerjaPerak #BeritaPerak + hashtag berkaitan hari ini\n\n"
        "Tulis Bahasa Melayu santai dengan emoji menarik."
    )

# ─── API CALL ─────────────────────────────────────────
def call_claude(prompt):
    payload = {
        "model": MODEL,
        "max_tokens": MAX_TOKENS,
        "system": (
            "Anda adalah NEXUS Perak Kamuniti Agent. "
            "Cari maklumat TERKINI menggunakan web search dan jana post Facebook menarik. "
            "WAJIB: URL benar sahaja. "
            "WAJIB: Jawatan dalam Perak sahaja. "
            "WAJIB: Link kerja dari JobStreet, Maukerja atau Indeed sahaja. "
            "WAJIB: Ikut format BAHAGIAN 1, 2, 3 dengan tepat. "
            "Bahasa Melayu santai dengan emoji."
        ),
        "messages": [{"role": "user", "content": prompt}],
        "tools": [{"type": "web_search_20250305", "name": "web_search"}],
        "tool_choice": {"type": "auto"}
    }
    req = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode(),
        headers={
            "Content-Type": "application/json",
            "x-api-key": API_KEY,
            "anthropic-version": "2023-06-01"
        },
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=90) as resp:
        return json.loads(resp.read())

# ─── RETRY WRAPPER ────────────────────────────────────
def call_claude_with_retry(prompt):
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            log(f"API call cuba #{attempt}...")
            return call_claude(prompt)
        except urllib.error.HTTPError as e:
            body = e.read().decode()
            log(f"HTTP Error {e.code} pada cuba #{attempt}: {body}", "ERROR")
            if e.code in (401, 403):
                raise ConfigurationError(
                    "Anthropic credential was rejected or lacks permission; "
                    "do not retry until the GitHub secret is corrected."
                ) from e
        except urllib.error.URLError as e:
            log(f"URL Error pada cuba #{attempt}: {e.reason}", "ERROR")
        except Exception as e:
            log(f"Error pada cuba #{attempt}: {str(e)}", "ERROR")

        if attempt < MAX_RETRIES:
            log(f"Tunggu {RETRY_DELAY}s sebelum cuba semula...")
            time.sleep(RETRY_DELAY)

    log(f"Gagal selepas {MAX_RETRIES} percubaan.", "ERROR")
    return None

# ─── EXTRACT TEXT ─────────────────────────────────────
def extract_text(response):
    if not response:
        return ""
    # Ambil SEMUA text blocks
    text_blocks = [
        block["text"]
        for block in response.get("content", [])
        if block.get("type") == "text" and block.get("text", "").strip()
    ]
    if not text_blocks:
        return ""
    # Gabungkan semua blocks
    full_text = "\n".join(text_blocks).strip()
    # Strip thinking text — cari mana post sebenar bermula
    markers = ["PERAK KAMUNITI", "## 📱 PERAK", "📢 PERAK", "BAHAGIAN 1"]
    for marker in markers:
        idx = full_text.find(marker)
        if idx > 0:
            log(f"Strip {idx} chars thinking text sebelum post sebenar.")
            return full_text[idx:].strip()
    return full_text

# ─── VALIDATE ─────────────────────────────────────────
def is_direct_vacancy_url(url):
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    host = parsed.netloc.lower().removeprefix("www.")
    if not parsed.scheme == "https" or not any(host.endswith(platform) for platform in TRUSTED_JOBS):
        return False
    candidate = f"{parsed.path}?{parsed.query}".lower()
    return bool(parsed.path.strip("/")) and not any(marker in candidate for marker in GENERIC_JOB_URL_MARKERS)


def validate_vacancy_evidence(content):
    section = content.split("BAHAGIAN 3", 1)[-1]
    blocks = re.split(r"(?im)^\s*(?=(?:\d+[.)]\s*)?Employer\s*:)", section)
    vacancies = []

    for block in blocks:
        fields = {}
        for label, key in [
            ("Employer", "employer"),
            ("Job title", "job_title"),
            ("Location", "location"),
            ("Direct vacancy URL", "direct_vacancy_url"),
            ("Checked date", "checked_date"),
        ]:
            match = re.search(rf"(?im)^\s*{re.escape(label)}\s*:\s*(.+?)\s*$", block)
            if match:
                fields[key] = match.group(1).strip()

        if not fields:
            continue

        missing = [key for key in VACANCY_FIELDS if not fields.get(key) or fields[key].upper() == "UNVERIFIED"]
        url = fields.get("direct_vacancy_url", "")
        direct_url = is_direct_vacancy_url(url)
        checked_date = fields.get("checked_date", "")
        valid_date = bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", checked_date))
        reasons = []
        if missing:
            reasons.append("missing: " + ", ".join(missing))
        if url and not direct_url:
            reasons.append("direct_vacancy_url is not a trusted direct listing")
        if checked_date and not valid_date:
            reasons.append("checked_date must be YYYY-MM-DD")

        vacancies.append({
            **{key: fields.get(key, "UNVERIFIED") for key in VACANCY_FIELDS},
            "status": "PASS" if not reasons else "UNVERIFIED",
            "reasons": reasons,
        })

    status = "PASS" if vacancies and all(vacancy["status"] == "PASS" for vacancy in vacancies) else "UNVERIFIED"
    return {
        "status": status,
        "checked_at": datetime.now().strftime("%Y-%m-%d"),
        "vacancies": vacancies,
    }


def validate_output(content):
    passed = True

    if len(content) < MIN_LENGTH:
        log(f"AMARAN: Content terlalu pendek ({len(content)} chars)", "WARN")
        passed = False

    for section in REQUIRED_SECTIONS:
        if section not in content:
            log(f"AMARAN: {section} tidak dijumpai dalam post!", "WARN")
            passed = False

    urls = re.findall(r'https?://[^\s\)\"]+', content)
    if len(urls) < MIN_URLS:
        log(f"AMARAN: Hanya {len(urls)} URL dijumpai (minimum {MIN_URLS})", "WARN")
        passed = False

    validation = validate_vacancy_evidence(content)
    if validation["status"] != "PASS":
        log("AMARAN: Bukti jawatan tidak lengkap atau tidak dapat disahkan — UNVERIFIED.", "WARN")
        passed = False

    if passed:
        log(f"Validasi lulus. {len(urls)} URL dijumpai, semua bahagian ada.")

    return passed, validation

# ─── DUPLICATE CHECK ──────────────────────────────────
def is_duplicate(content):
    try:
        with open(QUEUE_FILE, "r", encoding="utf-8") as f:
            queue = json.load(f)
        if queue:
            latest = queue[0].get("content", "")
            if latest[:100].strip() == content[:100].strip():
                log("Duplicate content detected — skip saving.", "WARN")
                return True
    except Exception:
        pass
    return False

# ─── SAVE QUEUE ───────────────────────────────────────
def save_to_queue(content, validation):
    try:
        with open(QUEUE_FILE, "r", encoding="utf-8") as f:
            queue = json.load(f)
    except Exception:
        queue = []

    queue.insert(0, {
        "id": int(datetime.now().timestamp() * 1000),
        "content": content,
        "type": "daily",
        "date": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "done": False,
        "validation": validation,
        "review_required": validation["status"] != "PASS",
    })
    queue = queue[:MAX_QUEUE]

    with open(QUEUE_FILE, "w", encoding="utf-8") as f:
        json.dump(queue, f, ensure_ascii=False, indent=2)

    log(f"Disimpan ke {QUEUE_FILE}. Total: {len(queue)} post(s).")

# ─── MAIN ─────────────────────────────────────────────
def main():
    log("=" * 50)
    log("NEXUS Perak Kamuniti — Post Generator")
    log("=" * 50)

    if not API_KEY:
        log("ANTHROPIC_API_KEY tidak dijumpai dalam environment!", "ERROR")
        exit(1)

    try:
        response = call_claude_with_retry(build_prompt())
    except ConfigurationError as e:
        log(str(e), "ERROR")
        exit(1)
    if not response:
        log("Gagal mendapat response dari API.", "ERROR")
        exit(1)

    content = extract_text(response)
    if not content:
        log("Tiada content dijana oleh API!", "ERROR")
        exit(1)

    log(f"Content dijana: {len(content)} characters")
    log("-" * 50)
    log(content[:400] + "..." if len(content) > 400 else content)
    log("-" * 50)

    is_valid, validation = validate_output(content)
    if not is_valid:
        log("Post tidak lulus validasi penuh — disimpan untuk semak manual.", "WARN")

    if is_duplicate(content):
        exit(0)

    save_to_queue(content, validation)
    log("Selesai! Post berjaya dijana dan disimpan.")
    log("=" * 50)

if __name__ == "__main__":
    main()
