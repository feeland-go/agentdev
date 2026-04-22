# Pipeline 3 — Task Tracking & Queue Management

## Tujuan
Menjadi **framework pembungkus** seluruh pekerjaan riset. Pipeline ini mengatur bagaimana 
ratusan task dikelola, diprioritaskan, dieksekusi secara paralel, dan dilaporkan — dari 
setup riset awal via Telegram hingga semua task selesai. Semua pipeline lain (Pipeline 1 & 2) 
berjalan di bawah kendali Pipeline 3.

---

## Siapa Mengerjakan Apa

Setiap bagian dalam Pipeline 3 dikerjakan oleh salah satu dari tiga aktor berikut:

| Simbol | Aktor | Peran |
|---|---|---|
| 🤖 | Hermes Agent | Menerima & mengirim pesan Telegram, mengelola state percakapan |
| 🤖 | AI CLI (`ccs`) | Dipanggil via subprocess Python untuk tugas yang butuh LLM |
| 🐍 | Python/Bash | Semua operasi file, queue, worker, notifikasi, cron |

> **Penting:** Notifikasi Telegram dan cron jobs **tidak menggunakan Hermes cron** — 
> murni Linux crontab + Python script langsung ke Telegram Bot API. Zero token.

---

## Gambaran Besar Alur

```
User kirim pesan ke Telegram
       ↓
🤖 Hermes Agent terima /sst-rx-new [nama-project]
       ↓
🤖 Cek JINA_API_KEY & TELEGRAM_BOT_TOKEN di ~/.hermes/.env
       ↓
🤖 Research Setup Conversation (tanya jawab via Telegram)
       ↓
🐍 Tulis research_config.yaml dari jawaban user
       ↓
🤖 AI CLI generate sub-queries dari topik & pertanyaan riset
       ↓
🐍 Jina Search + arXiv fetch kandidat berdasarkan queries
       ↓
🤖 AI CLI nilai relevansi tiap kandidat (filter < 0.6)
       ↓
🐍 Duplicate check → kandidat lolos masuk queue/pending/
       ↓
🤖 Hermes: "Setup selesai! N task siap. Ketik /sst-rx-start untuk memulai worker."
       ↓
User kirim /sst-rx-start
       ↓
🐍 Sliding Window Worker — 5 task paralel, terus mengalir
    ├─ Pipeline 1: fetch & simpan ke vault/sources/
    └─ Pipeline 2: extract → synthesize → final report
       ↓
🐍 Update task status di queue/
       ↓
🐍 Kirim notifikasi progress ke Telegram
```

---

## Research Setup via Telegram

### Konteks
Setup riset terjadi via percakapan di Telegram antara user dan Hermes Agent.
**Percakapan dijalankan oleh Hermes (AI) berdasarkan instruksi di SKILL.md** —
bukan Python state machine yang menunggu input. Ini penting karena Hermes gateway
tidak dapat bridge pesan Telegram ke proses Python yang sedang berjalan.

Alur yang benar:
```
User ketik /sst-rx-new [nama-project] di Telegram
       ↓
Hermes cek ~/.hermes/.env → ada JINA_API_KEY & TELEGRAM_BOT_TOKEN?
  ├─ Tidak ada → tanya user via Telegram, tulis ke ~/.hermes/.env
  └─ Ada → lanjut
       ↓
Hermes cek TELEGRAM_CHAT_ID di project `.env`
  ├─ Tidak ada → tanya user, tulis ke project `.env`
  └─ Ada → lanjut
       ↓
Hermes load skill sst-research
       ↓
Hermes (AI) menjalankan conversation berdasarkan instruksi SKILL.md
       ↓
Hermes menulis setup_state.json di setiap langkah (untuk crash recovery)
       ↓
Setelah user konfirmasi YES:
Hermes panggil: python orchestrator/setup.py --write-config '{json}'
Hermes panggil: bash run_research.sh fetch
       ↓
Hermes: "Setup selesai! N task siap. Ketik /sst-rx-start untuk memulai worker."
```

### setup_state.json (Crash Recovery)

File ini ditulis oleh Hermes (bukan Python script) di setiap langkah conversation.
Jika percakapan setup terputus, user cukup ketik `/sst-rx-new` lagi — Hermes baca
setup_state.json dan lanjutkan dari pertanyaan yang belum dijawab.
Jika worker yang crash, kirim `/sst-rx-start` untuk resume worker.

```json
{
  "state": "ASKING_QUESTIONS",
  "answers": {
    "topic": "AI Alignment",
    "research_questions": ["Apa metode alignment terbaik?"],
    "sub_topics": null,
    "date_range": null,
    "arxiv_categories": null
  },
  "started_at": "2026-04-21T14:30:00Z",
  "last_updated": "2026-04-21T14:31:22Z"
}
```

### Alur Percakapan di Telegram

```
USER:  /sst-rx-new ai-alignment

🤖:    Cek API keys di ~/.hermes/.env...
       ✅ JINA_API_KEY ditemukan.
       ✅ TELEGRAM_BOT_TOKEN ditemukan.

       Cek TELEGRAM_CHAT_ID di project .env...
       ✅ TELEGRAM_CHAT_ID ditemukan.

       Membuat project project-rx-ai-alignment...
       ✅ Project dibuat di ~/projects/project-rx-ai-alignment/

       Apa topik utama riset ini?

USER:  AI Alignment

🤖:    Topik: AI Alignment ✅
       Apa pertanyaan riset yang ingin dijawab?
       Ketik satu per pesan, ketik DONE jika selesai.

USER:  Apa metode alignment yang paling efektif saat ini?
🤖:    ✅ Pertanyaan 1 dicatat.

USER:  Bagaimana RLHF dibandingkan Constitutional AI?
🤖:    ✅ Pertanyaan 2 dicatat.

USER:  DONE

🤖:    Ada sub-topik spesifik? (SKIP untuk lewati)
       Contoh: RLHF, Constitutional AI, AI Safety

USER:  RLHF, Constitutional AI, AI Safety

🤖:    Batasan waktu publikasi? (SKIP untuk semua)
       Contoh: 2020-2025

USER:  2020-2025

🤖:    Kategori arXiv? (SKIP untuk semua)
       Contoh: cs.AI, cs.LG, stat.ML

USER:  cs.AI, cs.LG

🤖:    📋 Ringkasan Setup:
       ├─ Topik      : AI Alignment
       ├─ Pertanyaan : 2 pertanyaan
       ├─ Sub-topik  : RLHF, Constitutional AI, AI Safety
       ├─ Rentang    : 2020–2025
       └─ arXiv      : cs.AI, cs.LG
       
       Konfirmasi? (YES / NO)

USER:  YES

🤖:    ✅ Setup selesai! Memulai pencarian kandidat...
       🔍 Generating queries...
       🔍 Fetching candidates via Jina + arXiv...
       🤖 Scoring relevance...
       
       ✅ Setup selesai! 47 task siap di queue/pending/.
       Ketik /sst-rx-start untuk memulai worker.
```

### setup.py — Hanya Menulis Config

`setup.py` di Pipeline 3 tidak lagi mengelola state conversation. Tugasnya hanya
menerima JSON answers dari Hermes dan menulis `research_config.yaml`:

```python
# 🐍 Python — dipanggil oleh Hermes setelah user konfirmasi YES
# python orchestrator/setup.py --write-config '{json_string}'

import json
import sys
import yaml
from pathlib import Path

def write_research_config(answers: dict):
    config = {
        "project": {
            "topic": answers["topic"],
            "research_questions": answers["research_questions"],
            "sub_topics": answers.get("sub_topics") or [],
            "date_range": answers.get("date_range") or None,
            "arxiv_categories": answers.get("arxiv_categories") or [],
        },
        "queue": {
            "min_relevance": 0.6,
            "max_sources": 500,
            "parallel_workers": 5,
            "task_timeout": 180,
            "max_retry": 2,
        }
    }
    Path("research_config.yaml").write_text(
        yaml.dump(config, allow_unicode=True, default_flow_style=False),
        encoding="utf-8"
    )
    print("✅ research_config.yaml ditulis")

if __name__ == "__main__":
    if "--write-config" in sys.argv:
        idx = sys.argv.index("--write-config")
        answers = json.loads(sys.argv[idx + 1])
        write_research_config(answers)
```

---

## Query Generation

### Siapa: 🤖 AI CLI (`ccs`) + 🐍 Python

AI CLI (`ccs`) menerima topik, pertanyaan riset, **dan memory riset yang sudah ada**,
lalu menghasilkan sub-queries yang spesifik dan targeted. Python memanggil `ccs` via
subprocess dan mem-parsing hasilnya.

**Memory membuat query generation jauh lebih efektif:**
- Tanpa memory → query generik dari topik saja: `"RLHF reinforcement learning"`
- Dengan memory → query targeted dari gap spesifik: `"RLHF pada model skala >100B params"`

Query generation membaca `vault/memory/research.md` sebelum generate — sehingga query
baru selalu mengisi gap yang belum terjawab, bukan mengulang coverage yang sudah ada.

### Prompt Template (🤖 AI CLI)

```python
QUERY_GEN_PROMPT = """
Kamu adalah research strategist. Berdasarkan topik, pertanyaan riset, dan
peta riset yang sudah ada, buat daftar search queries yang spesifik dan targeted.

TOPIK: {topic}
SUB-TOPIK: {sub_topics}
PERTANYAAN RISET: {research_questions}
RENTANG WAKTU: {date_range}

PETA RISET SAAT INI (dari memory):
{research_map}

Prioritaskan queries yang:
1. Mengisi GAP yang belum terjawab — lihat bagian "Gap Terbuka" di peta riset
2. Menjawab pertanyaan riset yang masih OPEN atau PARTIALLY ANSWERED
3. Hindari topik yang coverage-nya sudah HIGH di peta riset

Kembalikan HANYA JSON berikut, tanpa preamble:
{{
  "queries": [
    {{
      "query": "teks query",
      "source": "jina | arxiv | both",
      "priority": "high | medium | low",
      "targets_gap": "gap spesifik yang ingin diisi, atau null"
    }}
  ]
}}
""".strip()
```

### Implementasi (🐍 Python)

```python
def generate_queries(config: dict) -> list[dict]:
    """
    Generate sub-queries dari topik + research memory.
    Putaran pertama: research_map kosong, query masih generik.
    Putaran berikutnya: query jauh lebih targeted karena baca gap dari memory.
    """
    from pathlib import Path
    from llm_client import call_llm

    research_map_path = Path("vault/memory/research.md")
    research_map = (
        research_map_path.read_text(encoding="utf-8")
        if research_map_path.exists()
        else "Belum ada — ini adalah putaran riset pertama."
    )

    prompt = QUERY_GEN_PROMPT.format(
        topic=config["project"]["topic"],
        sub_topics=", ".join(config["project"].get("sub_topics", [])),
        research_questions="\n".join(config["project"]["research_questions"]),
        date_range=config["project"].get("date_range", "semua waktu"),
        research_map=research_map[:3000],
    )

    raw = call_llm(prompt)
    result = parse_json_response(raw)
    return result.get("queries", [])
```

### Contoh Output — Putaran Pertama (tanpa memory)

```json
{
  "queries": [
    {"query": "RLHF reinforcement learning human feedback alignment", "source": "both", "priority": "high", "targets_gap": null},
    {"query": "constitutional AI Anthropic safety", "source": "both", "priority": "high", "targets_gap": null},
    {"query": "AI alignment survey 2024", "source": "arxiv", "priority": "medium", "targets_gap": null}
  ]
}
```

### Contoh Output — Putaran Kedua (dengan memory, gap sudah terdeteksi)

```json
{
  "queries": [
    {"query": "RLHF large language models 100B parameters scale", "source": "arxiv", "priority": "high", "targets_gap": "RLHF pada model skala >100B params"},
    {"query": "RLHF constitutional AI empirical comparison benchmark", "source": "both", "priority": "high", "targets_gap": "perbandingan empiris RLHF vs Constitutional AI"},
    {"query": "alignment evaluation benchmark dataset 2024", "source": "arxiv", "priority": "medium", "targets_gap": "dataset benchmark untuk alignment evaluation"}
  ]
}
```

---

## Relevance Scoring (Pre-Queue Filter)

### Siapa: 🤖 AI CLI (`ccs`) + 🐍 Python

Setiap kandidat dinilai relevansinya **sebelum masuk queue**. Hanya membaca title + 
abstract/snippet — belum fetch full content, sehingga murah dan cepat. Python memanggil 
`ccs` per kandidat dan memutuskan apakah masuk queue berdasarkan skor.

### Prompt Template (🤖 AI CLI)
Nilai relevansi dokumen berikut terhadap topik riset.

TOPIK RISET: {topic}
PERTANYAAN RISET: {research_questions}

DOKUMEN:
- Title: {title}
- Snippet: {snippet}

Kembalikan HANYA JSON berikut, tanpa preamble:
{{
  "score": 0.0,
  "reason": "alasan singkat 1 kalimat",
  "relevant": true
}}

Score: 0.0 (tidak relevan) hingga 1.0 (sangat relevan).
relevant: true jika score >= 0.6
""".strip()
```

### Filter Logic (🐍 Python)

```python
def filter_candidates(candidates: list[dict], config: dict) -> list[dict]:
    """
    Filter kandidat berdasarkan relevansi dan duplikasi.
    Hanya kandidat lolos yang akan dibuatkan task file.
    """
    approved = []
    existing_urls = get_existing_urls()   # scan vault/ dan queue/

    for candidate in candidates:
        # Cek duplikasi dulu — gratis, tidak perlu LLM
        if candidate["url"] in existing_urls:
            print(f"[FILTER] Skip duplikat: {candidate['title'][:50]}")
            continue

        # Relevance scoring via AI CLI
        prompt = RELEVANCE_PROMPT.format(
            topic=config["project"]["topic"],
            research_questions="\n".join(config["project"]["research_questions"]),
            title=candidate["title"],
            snippet=candidate.get("description", candidate.get("abstract", "")),
        )
        result = parse_json_response(call_llm(prompt))
        score = result.get("score", 0.0)

        if score >= 0.6:
            candidate["relevance_score"] = score
            approved.append(candidate)
            print(f"[FILTER] ✓ {score:.2f} — {candidate['title'][:50]}")
        else:
            print(f"[FILTER] ✗ {score:.2f} — {candidate['title'][:50]} ({result.get('reason', '')})")

    return approved
```

---

## Queue Structure (File-based)

### Siapa: 🐍 Python/Bash

```
queue/
├── pending/     ← task menunggu diproses
├── active/      ← max 5 task sedang berjalan
├── done/        ← task selesai sukses
├── failed/      ← gagal, menunggu retry (max 2x)
└── dead/        ← gagal permanent
```

**Kenapa file-based:**
- Zero dependency — tidak butuh database eksternal
- Crash-safe — kalau agent mati mendadak, state tidak hilang
- Audit cukup `ls queue/pending/ | wc -l`
- Bisa di-inspect dan di-edit manual kapanpun

### Format Task File (🐍 Python)

```json
{
  "task_id": "fetch_20260421_143201_001",
  "stage": "fetch",
  "source_type": "arxiv",
  "url": "http://arxiv.org/abs/1706.03762v5",
  "title": "Attention Is All You Need",
  "relevance_score": 0.91,
  "retry_count": 0,
  "max_retry": 2,
  "created_at": "2026-04-21T14:32:01Z",
  "started_at": null,
  "finished_at": null,
  "error": null
}
```

### Stage Progression

Task progression menggunakan granularitas campuran:
- **Per dokumen:** `fetch` → `extract`
- **Per topik:** `synthesize`

```
fetch_doc_XXXX.json   → selesai → buat extract_doc_XXXX.json → masuk pending/
extract_doc_XXXX.json → selesai → update status kesiapan topik
semua extract untuk topik selesai → buat synthesize_topic_{slug}.json → masuk pending/
synthesize_topic_{slug}.json → selesai → final report di-trigger jika semua topik selesai
```

### Naming Convention

```
{stage}_{YYYYMMDD}_{HHMMSS}_{index:03d}.json

Contoh:
fetch_20260421_143201_001.json
extract_20260421_150034_047.json
synthesize_20260421_160000_001.json
```

---

## Sliding Window Worker

### Siapa: 🐍 Python

### Cara Kerja

```
PENDING: [T1, T2, T3, T4, T5, T6, T7 ... T500]
ACTIVE:  [slot1, slot2, slot3, slot4, slot5]  ← selalu penuh

→ T1 selesai ✓  → mv ke done/ → ambil T6 langsung
→ T2 selesai ✓  → mv ke done/ → ambil T7 langsung
→ T3 timeout ✗  → mv ke failed/ → ambil T8 langsung
→ Slot tidak pernah idle menunggu task lambat
→ Setelah semua pending habis → jalankan failed/ sebagai retry
→ Setelah retry habis → selesai, kirim notif final
```

### Implementasi

```python
import json
import time
import threading
from pathlib import Path
from datetime import datetime, timezone

QUEUE_DIR = Path("queue")
MAX_WORKERS = 5
TASK_TIMEOUT = 180
MAX_RETRY = 2


def worker(task_file: Path):
    """
    🐍 Eksekusi satu task.
    Dispatch ke Pipeline 1 atau 2 tergantung stage.
    """
    task = json.loads(task_file.read_text())
    task["started_at"] = datetime.now(timezone.utc).isoformat()
    task_file.write_text(json.dumps(task, indent=2))

    try:
        if task["stage"] == "fetch":
            run_fetch(task)           # 🐍 Pipeline 1
            enqueue_next(task, "extract")  # otomatis buat task extract

        elif task["stage"] == "extract":
            run_extract(task)         # 🤖 AI CLI via Pipeline 2 Stage 1
            maybe_enqueue_topic_synthesis(task)

        elif task["stage"] == "synthesize":
            run_synthesize(task)      # 🤖 AI CLI via Pipeline 2 Stage 2
            check_trigger_final_report()  # cek apakah semua topik sudah selesai

        # Sukses
        task["finished_at"] = datetime.now(timezone.utc).isoformat()
        task["error"] = None
        task_file.write_text(json.dumps(task, indent=2))
        move_task(task_file, QUEUE_DIR / "done")
        notify_task_done(task)        # 🤖 kirim notif Telegram

    except Exception as e:
        task["error"] = str(e)
        task["retry_count"] = task.get("retry_count", 0) + 1
        task_file.write_text(json.dumps(task, indent=2))

        if task["retry_count"] >= MAX_RETRY:
            move_task(task_file, QUEUE_DIR / "dead")
            notify_task_dead(task)    # 🤖 kirim notif Telegram
        else:
            move_task(task_file, QUEUE_DIR / "failed")


def enqueue_next(task: dict, next_stage: str):
    """🐍 Buat task file untuk stage berikutnya dan masukkan ke pending."""
    next_task = {
        "task_id": f"{next_stage}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{task['task_id'].split('_')[-1]}",
        "stage": next_stage,
        "source_type": task["source_type"],
        "url": task["url"],
        "title": task["title"],
        "relevance_score": task["relevance_score"],
        "retry_count": 0,
        "max_retry": MAX_RETRY,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "started_at": None,
        "finished_at": None,
        "error": None,
    }
    path = QUEUE_DIR / "pending" / f"{next_task['task_id']}.json"
    path.write_text(json.dumps(next_task, indent=2))


def sliding_window_runner():
    """🐍 Jaga selalu 5 worker aktif. Main loop."""
    active_threads = []

    while True:
        active_threads = [t for t in active_threads if t.is_alive()]

        while len(active_threads) < MAX_WORKERS:
            next_task = get_next_pending()
            if not next_task:
                break

            move_task(next_task, QUEUE_DIR / "active")
            t = threading.Thread(
                target=worker,
                args=(QUEUE_DIR / "active" / next_task.name,),
                daemon=True,
            )
            t.start()
            active_threads.append(t)

        # Semua pending habis dan tidak ada yang aktif
        if not active_threads and not list((QUEUE_DIR / "pending").glob("*.json")):
            failed = list((QUEUE_DIR / "failed").glob("*.json"))
            if failed:
                print(f"[WORKER] Memproses {len(failed)} task retry...")
                for f in failed:
                    move_task(f, QUEUE_DIR / "pending")
                continue
            # Benar-benar selesai
            notify_all_done()         # 🤖 kirim notif final ke Telegram
            break

        time.sleep(2)


def get_next_pending() -> Path | None:
    """🐍 Ambil task pending paling awal (FIFO berdasarkan nama file)."""
    tasks = sorted((QUEUE_DIR / "pending").glob("*.json"))
    return tasks[0] if tasks else None


def move_task(task_file: Path, destination: Path):
    """🐍 Pindah task file ke folder tujuan."""
    destination.mkdir(parents=True, exist_ok=True)
    task_file.rename(destination / task_file.name)
```

---

## Notifikasi Telegram

### Siapa: 🐍 Python (kirim) + 🤖 Hermes Agent (terima & route)

### Setup Telegram Bot Token

Kita **tidak perlu bot Telegram terpisah**. Script Python menggunakan token yang sama 
dengan yang sudah dikonfigurasi di Hermes.

**1. Hermes master `.env` (`~/.hermes/.env`) — shared across all projects:**
```env
TELEGRAM_BOT_TOKEN=your_bot_token_here
JINA_API_KEY=your_jina_api_key_here
```

**2. Hermes config (`~/.hermes/config.yaml`):**
```yaml
telegram:
  bot_token: "your_bot_token_here"
  home_channel: "your_chat_id_here"
```

**3. Project `.env` (hanya berisi project-specific config):**
```env
TELEGRAM_CHAT_ID=your_chat_id_here
```

> **Penting:** `TELEGRAM_BOT_TOKEN` dan `JINA_API_KEY` dibaca dari `~/.hermes/.env`,
> bukan dari project `.env`. Project `.env` hanya berisi `TELEGRAM_CHAT_ID`.
> Saat `/sst-rx-new`, Hermes akan cek `~/.hermes/.env` dan tanya user jika key belum ada.

**Cara dapat Bot Token & Chat ID:**
- Bot Token: buat bot baru via [@BotFather](https://t.me/BotFather) → `/newbot`
- Chat ID: kirim pesan ke bot kamu, lalu buka `https://api.telegram.org/bot{TOKEN}/getUpdates`

### Implementasi (🐍 Python — zero token, tidak memanggil AI)

```python
import requests
import os
from dotenv import load_dotenv

# Load project .env for CHAT_ID
load_dotenv()
# Load Hermes .env for BOT_TOKEN and JINA_API_KEY
load_dotenv(os.path.expanduser("~/.hermes/.env"), override=False)

def send_telegram(message: str):
    """
    🐍 Kirim pesan ke Telegram via Bot API langsung.
    Tidak menggunakan Hermes cron — zero token, zero overhead.
    BOT_TOKEN dari ~/.hermes/.env, CHAT_ID dari project .env.
    """
    token   = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not token:
        print("[TELEGRAM] ⚠ TELEGRAM_BOT_TOKEN tidak ditemukan di ~/.hermes/.env")
        return
    if not chat_id:
        print("[TELEGRAM] ⚠ TELEGRAM_CHAT_ID tidak ditemukan di project .env")
        return

    response = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML",
        },
        timeout=10,
    )

    if not response.ok:
        print(f"[TELEGRAM] ⚠ Gagal kirim: {response.text}")
```

---

### Notif 1 — Per Task Selesai (🐍 dipanggil setiap `done`)

```
✅ Task Selesai
📄 Attention Is All You Need
🔧 Stage: Fetch
⏱ Durasi: 23s
📊 Progress: 47/500 (9.4%)
🔄 Antrian sisa: 453 task
```

```python
def notify_task_done(task: dict):
    """🐍 Dipanggil worker setiap task berhasil."""
    total   = count_all_tasks()
    done    = count_tasks("done")
    pending = count_tasks("pending")
    duration = calculate_duration(task)

    send_telegram(
        f"✅ <b>Task Selesai</b>\n"
        f"📄 {task['title'][:50]}\n"
        f"🔧 Stage: {task['stage'].capitalize()}\n"
        f"⏱ Durasi: {duration}s\n"
        f"📊 Progress: {done}/{total} ({done/total*100:.1f}%)\n"
        f"🔄 Antrian sisa: {pending} task"
    )
```

---

### Notif 2 — Summary Per 5 Menit (🐍 dipanggil cron)

```
📊 Research Progress Update
🕐 21 Apr 2026, 14:35

PIPELINE STATUS
├─ 🔍 Fetch     : 142/500 ✓  |  3 ❌  |  5 🔄
├─ 🤖 Extract   :  89/500 ✓  |  1 ❌  |  5 🔄
└─ 🔗 Synthesis :  12/142 ✓  |  0 ❌  |  0 🔄

QUEUE
├─ Active slots : 5/5
├─ Retry queue  : 4 task
└─ Dead         : 0 task

⏱ Estimasi selesai: ~2j 14m
```

```python
def notify_progress_summary():
    """🐍 Dipanggil cron setiap 5 menit."""
    fetch_done   = count_tasks_by_stage("done", "fetch")
    extract_done = count_tasks_by_stage("done", "extract")
    synth_done   = count_tasks_by_stage("done", "synthesize")
    total        = count_all_tasks()
    active       = count_tasks("active")
    retry        = count_tasks("failed")
    dead         = count_tasks("dead")
    eta          = estimate_eta()

    send_telegram(
        f"📊 <b>Research Progress Update</b>\n"
        f"🕐 {datetime.now().strftime('%d %b %Y, %H:%M')}\n\n"
        f"<b>PIPELINE STATUS</b>\n"
        f"├─ 🔍 Fetch     : {fetch_done}/{total} ✓\n"
        f"├─ 🤖 Extract   : {extract_done}/{total} ✓\n"
        f"└─ 🔗 Synthesis : {synth_done}/{fetch_done} ✓\n\n"
        f"<b>QUEUE</b>\n"
        f"├─ Active slots : {active}/5\n"
        f"├─ Retry queue  : {retry} task\n"
        f"└─ Dead         : {dead} task\n\n"
        f"⏱ Estimasi selesai: {eta}"
    )
```

---

### Notif 3 — Stage Selesai (🐍 dipanggil worker saat stage habis)

```
🎉 Stage Selesai: EXTRACT
⏱ Durasi total: 1j 23m
✅ Berhasil : 487 task
❌ Gagal    : 11 task
💀 Dead     : 2 task

📋 Dead tasks:
- "Paper XYZ..." (timeout 2x)
- "Blog ABC..." (Jina error)

▶️ Melanjutkan ke: SYNTHESIS
```

---

### Notif 4 — Semua Selesai (🐍 dipanggil worker saat queue benar-benar kosong)

```
🏁 Riset Selesai!
📋 Topik: AI Alignment
⏱ Total durasi: 4j 12m

HASIL AKHIR
├─ ✅ Berhasil   : 487/500
├─ 💀 Dead       : 13 task
└─ 📄 Final report: vault/output/final-report.md

Ketik /report untuk melihat ringkasan laporan.
```

---

## Watchdog

### Siapa: 🐍 Python (dipanggil cron setiap 2 menit)

Memastikan worker tidak mati diam-diam. Jika `queue/active/` berisi task tapi 
tidak ada thread aktif, worker direstart otomatis.

```python
def watchdog():
    """
    🐍 Cek apakah ada task stuck di active/ tanpa worker.
    Jika ya, kembalikan ke pending/ dan restart worker.
    """
    active_tasks = list((QUEUE_DIR / "active").glob("*.json"))

    for task_file in active_tasks:
        task = json.loads(task_file.read_text())
        started = datetime.fromisoformat(task["started_at"]) if task["started_at"] else None

        if started:
            elapsed = (datetime.now(timezone.utc) - started).seconds
            if elapsed > TASK_TIMEOUT + 30:   # grace period 30 detik
                print(f"[WATCHDOG] Task stuck ditemukan: {task_file.name}, kembalikan ke pending")
                task["started_at"] = None
                task_file.write_text(json.dumps(task, indent=2))
                move_task(task_file, QUEUE_DIR / "pending")
```

---

## Master Index (`vault/_index.md`)

### Siapa: 🐍 Python (di-rebuild cron setiap jam)

Fungsinya sebagai **katalog dokumen vault untuk manusia** — bukan sistem tracking. 
Tracking ada di `queue/`.

```markdown
# Research Index
**Project:** AI Alignment
**Last updated:** 2026-04-21 14:35
**Total documents:** 487

## Sources (142)
| Title | Type | Date | Credibility | Status |
|---|---|---|---|---|
| Attention Is All You Need | arxiv | 2017-06-12 | 0.91 | ✅ extracted |

## Extracted (89)
...

## Synthesis (12)
...
```

---

## Cron Jobs

### Siapa: ⚙️ Linux Crontab (bukan Hermes cron)

Semua scheduled task di sini menggunakan **Linux crontab biasa** — bukan Hermes cron.

**Alasan:**
- Hermes cron membuka fresh agent session setiap tick = narik token = boros
- Notifikasi & watchdog tidak butuh AI thinking sama sekali
- Linux crontab: zero token, zero overhead, murni Python script

**Hermes cron** hanya dipakai jika task memang butuh LLM — tidak ada di bagian ini.

```cron
# Edit crontab dengan: crontab -e

# Progress summary setiap 5 menit (zero token — murni Python)
*/5 * * * * cd /path/to/project && python notify.py --summary

# Watchdog: cek worker stuck setiap 2 menit (zero token — murni Python)
*/2 * * * * cd /path/to/project && python watchdog.py

# Rebuild vault/_index.md setiap jam (zero token — murni Python)
0 * * * * cd /path/to/project && python indexer.py --rebuild
```

---

## Audit Cepat via Bash

### Siapa: ⚙️ Bash

```bash
# Berapa task pending?
ls queue/pending/ | wc -l

# Berapa yang sudah selesai?
ls queue/done/ | wc -l

# Siapa yang dead?
ls queue/dead/

# Status keseluruhan
python audit.py --summary

# Reset stuck tasks dari active ke pending (manual recovery)
mv queue/active/*.json queue/pending/
```

---

## Config (config.yaml — Bagian Pipeline 3)

```yaml
queue:
  min_relevance: 0.6
  max_sources: 500
  parallel_workers: 5
  task_timeout: 180       # detik per task sebelum watchdog anggap stuck
  max_retry: 2            # retry sebelum task dianggap dead

notifications:
  telegram: true
  summary_interval_minutes: 5
  notify_per_task: true
  notify_per_stage: true
  notify_on_complete: true

cron:
  summary_every: "*/5 * * * *"
  watchdog_every: "*/2 * * * *"
  index_rebuild_every: "0 * * * *"
```

---

## Ringkasan: Siapa Mengerjakan Apa

| Komponen | 🤖 Hermes Agent | 🤖 AI CLI (`ccs`) | 🐍 Python/Bash |
|---|---|---|---|
| Terima /sst-rx-new dari user | ✅ | | |
| Cek & tulis ~/.hermes/.env (JINA_API_KEY, BOT_TOKEN) | ✅ | | |
| Buat project dari template | ✅ | | ✅ |
| Tanya jawab setup riset via Telegram | ✅ | | |
| Tulis research_config.yaml | | | ✅ |
| Generate sub-queries | | ✅ | |
| Fetch kandidat (Jina + arXiv) | | | ✅ |
| Nilai relevansi kandidat | | ✅ | |
| Filter & duplicate check | | | ✅ |
| Buat task file di pending/ | | | ✅ |
| Sliding window worker (/sst-rx-start) | ✅ | | ✅ |
| Stop worker (/sst-rx-stop) | ✅ | | |
| Eksekusi Pipeline 1 (fetch) | | | ✅ |
| Eksekusi Pipeline 2 (extract) | | ✅ | |
| Eksekusi Pipeline 2 (synthesize) | | ✅ | |
| Move task antar folder queue | | | ✅ |
| Kirim notifikasi Telegram | | | ✅ |
| Watchdog | | | ✅ |
| Rebuild _index.md | | | ✅ |
| Cron jobs (Linux crontab) | | | ✅ |

---

## Catatan Penting

- **Setup via Telegram** — user tidak perlu akses terminal sama sekali setelah repo di-clone. Semua dimulai dari `/sst-rx-new` di Telegram.
- **`/sst-rx-new` = create project + setup riset + generate queries + fetch candidates + create task files** — TIDAK start worker.
- **`/sst-rx-start` = start worker, `/sst-rx-stop` = stop worker** — simple dan langsung.
- **`~/.hermes/.env`** menyimpan `TELEGRAM_BOT_TOKEN` dan `JINA_API_KEY` (global, shared).
- **Project `.env`** menyimpan `TELEGRAM_CHAT_ID` (project-specific, bisa disalin dari master `.env`).
- **Sliding window** memastikan selalu ada 5 task berjalan — tidak ada idle menunggu task lambat.
- **Stage progression otomatis** — setelah fetch selesai, task extract langsung dibuat dan masuk pending tanpa intervensi manual.
- **Retry dijalankan di akhir** — setelah semua task utama habis, baru failed/ diproses ulang.
- **Dead task dilaporkan** di notif stage selesai — tidak ada yang hilang diam-diam.
- **Crash recovery** — setup crash: kirim `/sst-rx-new` lagi (Hermes baca setup_state.json, lanjut dari langkah terakhir). Worker crash: `mv queue/active/*.json queue/pending/` lalu `/sst-rx-start`.
