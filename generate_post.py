import urllib.request
import urllib.error
import json
import os
from datetime import datetime

api_key = os.environ.get('ANTHROPIC_API_KEY', '')
if not api_key:
    print("ERROR: Tiada API key!")
    exit(1)

today = datetime.now().strftime("%A, %d %B %Y")

prompt = (
    "Hari ini " + today + ". Jana satu post Facebook lengkap untuk group Perak Kamuniti Malaysia.\n\n"
    "WAJIB ikut susunan dan format ini:\n\n"
    "=============================\n"
    "BAHAGIAN 1 - BERITA PERAK HARI INI\n"
    "=============================\n"
    "Cari 1 berita paling penting hari ini dari Perak Malaysia.\n"
    "Tulis ringkasan berita dengan emoji menarik.\n"
    "Sertakan: Sumber berita dan link artikel asal.\n"
    "Sertakan hashtag berkaitan berita ini sahaja.\n\n"
    "=============================\n"
    "BAHAGIAN 2 - KISAH VIRAL PERAK\n"
    "=============================\n"
    "Cari 1 kisah viral atau menarik yang berlaku di Perak.\n"
    "Tulis dengan gaya santai dan menarik.\n"
    "Sertakan link sumber jika ada.\n"
    "Sertakan hashtag berkaitan kisah ini sahaja.\n\n"
    "=============================\n"
    "BAHAGIAN 3 - JAWATAN KOSONG DI PERAK\n"
    "=============================\n"
    "Cari 2 atau 3 jawatan kosong terkini di Perak.\n"
    "Untuk setiap jawatan WAJIB tulis dalam format ini:\n"
    "Nama Syarikat: [nama syarikat]\n"
    "Jawatan: [nama jawatan]\n"
    "Lokasi: [daerah di Perak]\n"
    "Link Apply: [link dari JobStreet atau Maukerja atau Indeed]\n\n"
    "=============================\n"
    "HASHTAG KESELURUHAN\n"
    "=============================\n"
    "Tulis hashtag yang berkaitan dengan semua bahagian di atas.\n"
    "Wajib masukkan: #PerakKamuniti #Perak #Malaysia #InfoPerak #KerjaPerak #BeritaPerak\n\n"
    "Tulis dalam Bahasa Melayu yang santai. Gunakan emoji yang menarik di setiap bahagian."
)

payload = {
    "model": "claude-haiku-4-5-20251001",
    "max_tokens": 2000,
    "system": (
        "Anda adalah NEXUS Perak Kamuniti Agent. "
        "Jana post Facebook menarik untuk group Perak Kamuniti. "
        "Ikut format yang diberikan dengan tepat. "
        "Sertakan link sumber berita dan link apply kerja yang betul."
    ),
    "messages": [{"role": "user", "content": prompt}]
}

req = urllib.request.Request(
    "https://api.anthropic.com/v1/messages",
    data=json.dumps(payload).encode(),
    headers={
        "Content-Type": "application/json",
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01"
    },
    method="POST"
)

try:
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read())
        reply = " ".join(i["text"] for i in data.get("content", []) if i.get("type") == "text")

    try:
        with open("queue.json", "r", encoding="utf-8") as f:
            queue = json.load(f)
    except Exception:
        queue = []

    new_post = {
        "id": int(datetime.now().timestamp() * 1000),
        "content": reply,
        "type": "daily",
        "date": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "done": False
    }
    queue.insert(0, new_post)
    queue = queue[:30]

    with open("queue.json", "w", encoding="utf-8") as f:
        json.dump(queue, f, ensure_ascii=False, indent=2)

    print("Post berjaya dijana: " + str(len(reply)) + " chars")
    print(reply[:300])

except urllib.error.HTTPError as e:
    body = e.read().decode()
    print("HTTP Error " + str(e.code) + ": " + body)
    exit(1)
except Exception as e:
    print("Error: " + str(e))
    exit(1)
