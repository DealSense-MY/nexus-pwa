import urllib.request
import urllib.error
import json
import os
import re
from datetime import datetime

# ─── CONFIG ───────────────────────────────────────────
API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
API_URL = "https://api.anthropic.com/v1/messages"
MODEL = "claude-haiku-4-5-20251001"
MAX_TOKENS = 2000
QUEUE_FILE = "queue.json"
MAX_QUEUE = 30

# ─── PROMPT ───────────────────────────────────────────
def build_prompt():
    today = datetime.now().strftime("%A, %d %B %Y")
    return (
        "Hari ini " + today + ". Jana satu post Facebook untuk group Perak Kamuniti Malaysia.\n\n"
        "ARAHAN PENTING:\n"
        "- Gunakan web search untuk mencari maklumat TERKINI dan BENAR\n"
        "- JANGAN cipta atau reka link palsu\n"
        "- Hanya sertakan URL yang BENAR dan boleh diklik (bermula dengan https://)\n"
        "- Jika tiada data dijumpai, tulis: Tiada data dijumpai hari ini\n"
        "- Semua jawatan kosong MESTI berlokasi dalam Negeri Perak SAHAJA\n"
        "- TOLAK mana-mana jawatan di luar Perak (KL, Selangor, Johor dll)\n\n"
        "FORMAT POST (ikut TEPAT):\n\n"
        "PERAK KAMUNITI - UPDATE HARI INI\n"
        "================================\n\n"
        "BAHAGIAN 1: BERITA PERAK HARI INI\n"
        "--------------------------------\n"
        "Cari 1 berita TERKINI dan BENAR dari Perak Malaysia hari ini.\n"
        "Tulis ringkasan 3-4 ayat dengan emoji menarik.\n"
        "Wajib sertakan: Sumber dan URL artikel BENAR.\n"
        "Sertakan hashtag berkaitan berita ini.\n\n"
        "BAHAGIAN 2: KISAH VIRAL PERAK\n"
        "--------------------------------\n"
        "Cari 1 kisah viral atau menarik BENAR dari Perak.\n"
        "Tulis dengan gaya santai dan menarik.\n"
        "Sertakan URL sumber jika ada.\n"
        "Sertakan hashtag berkaitan.\n\n"
        "BAHAGIAN 3: JAWATAN KOSONG DI PERAK\n"
        "--------------------------------\n"
        "Cari 2-3 jawatan kosong TERKINI dalam Negeri Perak SAHAJA.\n"
        "Daerah Perak yang diterima: Ipoh, Taiping, Teluk Intan, Manjung, Kampar, Kuala Kangsar, Gerik, Lumut, Batu Gajah, Sitiawan, Parit Buntar.\n"
        "Untuk setiap jawatan tulis:\n"
        "Syarikat: [nama]\n"
        "Jawatan: [nama jawatan]\n"
        "Lokasi: [daerah dalam Perak]\n"
        "Gaji: [julat gaji jika ada]\n"
        "Apply: [URL BENAR dari JobStreet ATAU Maukerja ATAU Indeed - WAJIB]\n\n"
        "HASHTAG AKHIR:\n"
        "#PerakKamuniti #Perak #Malaysia #InfoPerak #KerjaPerak #BeritaPerak ditambah hashtag lain berkaitan content hari ini.\n\n"
        "Tulis dalam Bahasa Melayu santai dengan emoji menarik dan format yang jelas."
    )

# ─── API CALL ─────────────────────────────────────────
def call_claude(prompt):
    payload = {
        "model": MODEL,
        "max_tokens": MAX_TOKENS,
        "system": (
            "Anda adalah NEXUS Perak Kamuniti Agent. "
            "Cari maklumat TERKINI menggunakan web search dan jana post Facebook yang menarik. "
            "WAJIB: Hanya URL yang benar dan boleh diklik. "
            "WAJIB: Jawatan kosong dalam Negeri Perak sahaja. "
            "WAJIB: Ikut format yang diberikan. "
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

    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read())

# ─── EXTRACT TEXT ─────────────────────────────────────
def extract_text(response):
    texts = []
    for block in response.get("content", []):
        if block.get("type") == "text":
            texts.append(block["text"])
    return "\n".join(texts).strip()

# ─── VALIDATE ─────────────────────────────────────────
def validate_output(content):
    issues = []
    if not re.findall(r'https?://\S+', content):
        issues.append("AMARAN: Tiada URL ditemui dalam post!")
    if len(content) < 200:
        issues.append("AMARAN: Content terlalu pendek!")
    if "BAHAGIAN 1" not in content:
        issues.append("AMARAN: Bahagian 1 (Berita) tidak dijumpai!")
    if "BAHAGIAN 2" not in content:
        issues.append("AMARAN: Bahagian 2 (Viral) tidak dijumpai!")
    if "BAHAGIAN 3" not in content:
        issues.append("AMARAN: Bahagian 3 (Jawatan) tidak dijumpai!")
    for issue in issues:
        print(issue)
    return len(issues) == 0

# ─── SAVE QUEUE ───────────────────────────────────────
def save_to_queue(content):
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
        "done": False
    })
    queue = queue[:MAX_QUEUE]

    with open(QUEUE_FILE, "w", encoding="utf-8") as f:
        json.dump(queue, f, ensure_ascii=False, indent=2)

    print("Queue disimpan: " + str(len(queue)) + " post(s)")

# ─── MAIN ─────────────────────────────────────────────
def main():
    if not API_KEY:
        print("ERROR: ANTHROPIC_API_KEY tidak dijumpai!")
        exit(1)

    print("[" + datetime.now().strftime("%d/%m/%Y %H:%M") + "] Jana post Perak Kamuniti...")

    try:
        print("Memanggil Claude API dengan web search...")
        response = call_claude(build_prompt())
        content = extract_text(response)

        if not content:
            print("ERROR: Tiada content dijana!")
            exit(1)

        print("Content dijana: " + str(len(content)) + " characters")
        print("-" * 60)
        print(content[:500] + "..." if len(content) > 500 else content)
        print("-" * 60)

        if not validate_output(content):
            print("AMARAN: Post tidak lengkap - sila semak manual.")

        save_to_queue(content)
        print("Selesai! Post berjaya dijana.")

    except urllib.error.HTTPError as e:
        print("HTTP Error " + str(e.code) + ": " + e.read().decode())
        exit(1)
    except urllib.error.URLError as e:
        print("URL Error: " + str(e.reason))
        exit(1)
    except Exception as e:
        print("Error: " + str(e))
        exit(1)

if __name__ == "__main__":
    main()
