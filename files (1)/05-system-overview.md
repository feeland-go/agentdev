# Dokumen 5 — Sistem Secara Menyeluruh

## Tujuan
Dokumen ini menjelaskan bagaimana seluruh komponen bekerja bersama sebagai satu sistem 
yang utuh — dari user mengirim pesan pertama di Telegram hingga laporan final tersimpan 
di vault. Semua pipeline, memory, queue, dan notifikasi dijelaskan dalam satu gambaran 
besar yang kohesif.

---

## Peta Komponen

```
┌─────────────────────────────────────────────────────────────┐
│                     USER (Telegram)                          │
└─────────────────────────┬───────────────────────────────────┘
                          │ /sst-rx-new, /sst-rx-start, /sst-rx-memory, dll
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    HERMES AGENT                              │
│  • Menerima & routing pesan Telegram                        │
│  • Menjalankan state machine setup riset                    │
│  • Merespons semua command /sst-*                           │
└──────────┬──────────────────────────────┬───────────────────┘
           │ trigger                       │ baca
           ▼                              ▼
┌─────────────────────┐      ┌───────────────────────────────┐
│  run_research.sh    │      │   PIPELINE 4                  │
│  (Orchestrator)     │      │   Memory System               │
│                     │      │                               │
│  • Preflight check  │      │   vault/memory/               │
│  • Activate venv    │◄────►│   ├── working.md              │
│  • Step dispatch    │      │   ├── research.md             │
│  • Logging          │      │   └── meta.md                 │
└──────────┬──────────┘      └───────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────┐
│                    PIPELINE 3                                │
│           Task Orchestrator (Python)                         │
│                                                             │
│  setup.py → query_gen.py → relevance.py → worker.py        │
└──────────┬──────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────┐
│                       QUEUE                                  │
│        pending/ → active/ → done/ / failed/ → dead/         │
└──────────┬──────────────────────────────────────────────────┘
           │
     ┌─────┴──────┐
     ▼            ▼
┌──────────┐  ┌──────────────────────────────────────────────┐
│PIPELINE 1│  │ PIPELINE 2                                    │
│  Fetch   │  │                                               │
│          │  │  Stage 1: Extract  → vault/extracted/         │
│ • Jina   │  │  Stage 2: Synthesize → vault/synthesis/       │
│ • arXiv  │  │  Stage 3: Report   → vault/output/            │
└────┬─────┘  └──────────────────────────────────────────────┘
     │
     ▼
vault/sources/
```

---

## Fase 1 — Setup Riset

### Urutan Task (Skenario: Mulai Project Baru)

```
1. User clone master repo → jalankan new-project.sh "ai-alignment-research"
2. User kirim /sst-rx-new ai-alignment-research ke Telegram
3. Hermes Agent cek ~/.hermes/.env untuk JINA_API_KEY
   → Jika tidak ada, Hermes tanya user via Telegram dan tulis ke ~/.hermes/.env
4. Hermes Agent cek TELEGRAM_CHAT_ID di project `.env`
   → Jika tidak ada, Hermes tanya user via Telegram lalu tulis ke project `.env`
4. Hermes Agent load setup_state.json → state: IDLE
5. Agent tanya 5 pertanyaan setup satu per satu via Telegram
6. User jawab semua pertanyaan
7. Agent tulis research_config.yaml
8. Agent panggil memory.init_memory() → buat vault/memory/*.md kosong
9. AI CLI dipanggil → generate sub-queries dari topik + research_config
10. Jina Search + arXiv fetch kandidat URL/paper berdasarkan queries
11. AI CLI nilai relevansi tiap kandidat (filter score < 0.6)
12. Python duplicate check → buang yang sudah ada di vault/queue
13. Task files dibuat → masuk queue/pending/
14. Agent kirim notif: "✅ 487 task siap. Ketik /sst-rx-start untuk memulai worker"
```

### Flowchart

```
/sst-rx-new [nama] dikirim
      │
      ▼
cek ~/.hermes/.env untuk JINA_API_KEY
      │
  ADA? ──── YES ──── lanjut
      │
      NO
      │
  Hermes tanya user via Telegram → tulis ke ~/.hermes/.env
      │
      ▼
buat project folder (new-project.sh)
      │
      ▼
load setup_state.json
      │
   IDLE? ──── YES ──── mulai dari pertanyaan 1
      │
      NO
      │
   lanjut dari state terakhir (crash recovery)
      │
      ▼
[ASKING_TOPIC] → [ASKING_QUESTIONS] → [ASKING_SUBTOPICS]
      │
      ▼
[ASKING_DATE_RANGE] → [ASKING_ARXIV_CATEGORIES] → [CONFIRMING]
      │
   User: YES
      │
      ▼
tulis research_config.yaml
init vault/memory/
      │
      ▼
AI CLI: generate_queries()
  └── baca research.md (kosong di putaran pertama)
  └── output: list sub-queries dengan priority
      │
      ▼
Jina Search + arXiv → list kandidat
      │
      ▼
AI CLI: relevance_scoring() per kandidat
  ├── score >= 0.6 → lanjut ke duplicate check
  └── score < 0.6  → buang
      │
      ▼
duplicate_check()
  ├── sudah ada di vault/ atau queue/ → buang
  └── belum ada → buat task file
      │
      ▼
queue/pending/ terisi N task
      │
      ▼
notif Telegram: "✅ N task siap. Ketik /sst-rx-start untuk memulai worker"
```

---

## Fase 2 — Eksekusi Task

### Urutan Task (Skenario: 3 Task Berjalan, 1 Timeout)

```
Kondisi awal: queue/pending/ berisi 487 task

1. sliding_window_runner() start → ambil T1, T2, T3, T4, T5 ke active/
2. T1 (fetch) mulai → Jina Reader fetch URL
3. T2 (fetch) mulai → arXiv fetch paper
4. T3 (fetch) mulai → Jina Reader fetch URL
5. T4 (fetch) mulai → Jina Reader fetch URL
6. T5 (fetch) mulai → Jina Reader fetch URL — LAMBAT

7. T1 selesai ✓
   → tulis vault/sources/2026-04-21--attention-is-all.md
   → append working.md (zero AI)
   → buat task baru: extract_T1 → masuk pending/
   → mv T1 ke done/
   → ambil T6 dari pending/ → slot terisi kembali
   → kirim notif Telegram "✅ Task Selesai: Fetch..."

8. T2 selesai ✓ → proses sama seperti T1, ambil T7
9. T3 selesai ✓ → ambil T8
10. T4 selesai ✓ → ambil T9

11. T5 TIMEOUT (180s terlewat)
    → retry_count +1 (sekarang 1/2)
    → mv T5 ke failed/
    → ambil T10 dari pending/ — slot tidak menunggu T5!

12. Sementara itu extract_T1 sudah masuk pending/
    → worker ambil extract_T1
    → AI CLI ekstrak klaim dari vault/sources/2026-04-21--attention-is-all.md
    → tulis vault/extracted/2026-04-21--attention-is-all.md
    → buat task: synthesize_topic_rlhf → masuk pending/
    → mv extract_T1 ke done/

13. Proses berlanjut sampai pending/ kosong
14. Setelah pending/ kosong → proses failed/ sebagai retry
15. T5 retry → berhasil ✓ atau dead (retry ke-2 gagal)
```

### Flowchart

```
sliding_window_runner() START
          │
          ▼
    active_threads < 5?
    ├── YES → ambil task dari pending/
    │         mv ke active/
    │         spawn thread → worker(task)
    │         kembali cek slot
    └── NO  → tunggu 2 detik → cek lagi
          │
          ▼
    worker(task) running:
    ├── stage: "fetch"
    │     └── Pipeline 1: Jina/arXiv fetch
    │           ├── SUKSES → tulis vault/sources/
    │           │            append working.md
    │           │            enqueue_next("extract")
    │           │            mv ke done/
    │           │            notif Telegram ✅
    │           └── GAGAL  → retry_count +1
    │                         retry < 2 → mv ke failed/
    │                         retry = 2 → mv ke dead/
    │                                     notif Telegram 💀
    │
    ├── stage: "extract"
    │     └── Pipeline 2 Stage 1: AI CLI ekstrak klaim
    │           ├── SUKSES → tulis vault/extracted/
    │           │            append working.md
    │           │            update_research_map() → tulis research.md
    │           │            enqueue_next("synthesize")
    │           │            mv ke done/
    │           └── GAGAL  → retry logic sama
    │
    └── stage: "synthesize"
          └── Pipeline 2 Stage 2: AI CLI sintesis per topik
                ├── SUKSES → tulis vault/synthesis/
                │            append working.md
                │            check_trigger_final_report()
                │            mv ke done/
                └── GAGAL  → retry logic sama
          │
          ▼
    pending/ kosong + active/ kosong?
    ├── ada failed/? → mv semua ke pending/ → ulang
    └── semua kosong → FASE 3
```

---

## Fase 3 — Sintesis & Final Report

> Fase 3 terjadi **setelah semua task synthesize selesai**, bukan setelah extract.
> Namun `update_research_map()` dipanggil **setelah setiap stage Extract selesai**, bukan setelah Synthesize.

### Urutan Task (Skenario: 3 Topik Tersintesis, Generate Final Report)

```
Kondisi awal: vault/synthesis/ berisi rlhf.md, constitutional-ai.md, ai-safety.md
(research.md sudah ter-update selama Extract berlangsung)

1. check_trigger_final_report() deteksi semua topik sudah tersintesis
2. notify_stage_done("SYNTHESIZE", stats) → kirim notif Telegram
3. Cek research.md: ada pertanyaan masih OPEN?
   ├── YA → gap masuk kandidat query putaran berikutnya (self-improving loop)
   └── TIDAK → lanjut ke final report
4. Pipeline 2 Stage 3: AI CLI baca semua vault/synthesis/ + research.md
   → jawab semua pertanyaan riset
   → tulis vault/output/final-report.md
5. write_meta_memory(config)
   → AI CLI analisis working.md + dead tasks
   → tulis vault/memory/meta.md
6. indexer.py --rebuild → rebuild vault/_index.md
7. notify_all_done() → kirim notif final ke Telegram

Catatan: update_research_map() dipanggil per Extract task selesai:
   → AI CLI baca vault/extracted/ terbaru
   → update status pertanyaan riset (OPEN/PARTIAL/ANSWERED)
   → tulis vault/memory/research.md
   → Synthesize menggunakan info dari research.md
```

### Flowchart

```
Per task "extract" selesai
          │
          ▼
update_research_map()
  └── AI CLI baca vault/extracted/ terbaru
  └── tulis vault/memory/research.md
          │
          ▼
(Synthesize menggunakan research.md yang sudah ter-update)
          │
          ▼
Semua task "synthesize" selesai
          │
          ▼
notify_stage_done("SYNTHESIZE")
          │
          ▼
cek research.md: ada pertanyaan OPEN atau PARTIALLY ANSWERED?
    │                         │
   YES                        NO
    │                         │
    ▼                         ▼
gap → kandidat          Pipeline 2 Stage 3:
query putaran           AI CLI baca vault/synthesis/ + research.md
berikutnya              → tulis vault/output/final-report.md
(self-improving)              │
                              ▼
                        write_meta_memory()
                        AI CLI → vault/memory/meta.md
                              │
                              ▼
                        indexer.py --rebuild
                        → vault/_index.md
                              │
                              ▼
                        notify_all_done() → Telegram
                        "🏁 Riset selesai!"
```

---

## Lifecycle Satu Task (End-to-End)

### Skenario: Paper "Attention Is All You Need" dari arXiv

```
─── LAHIR ────────────────────────────────────────────────────

arXiv query "RLHF alignment" → kandidat ditemukan
  title: "Attention Is All You Need"
  url:   http://arxiv.org/abs/1706.03762

AI CLI relevance score → 0.91 (lolos)
Duplicate check → belum ada → buat task file

FILE: queue/pending/fetch_20260421_143201_001.json
{
  "task_id": "fetch_20260421_143201_001",
  "stage": "fetch",
  "title": "Attention Is All You Need",
  "url": "http://arxiv.org/abs/1706.03762",
  "relevance_score": 0.91,
  "retry_count": 0
}

─── STAGE 1: FETCH ───────────────────────────────────────────

Worker ambil task → mv ke active/
Pipeline 1: Jina Reader fetch PDF → konten bersih Markdown
Tulis: vault/sources/2026-04-21--attention-is-all-you-need.md

working.md append:
  [14:32] FETCH ✓ "Attention Is All You Need" | arxiv | 0.91 | 23s

Task mv ke done/
Task baru dibuat: queue/pending/extract_20260421_143224_001.json

─── STAGE 2: EXTRACT ─────────────────────────────────────────

Worker ambil extract task
AI CLI baca Raw Content dari vault/sources/...
Ekstrak: summary, key_points, key_entities, gaps
Tulis: vault/extracted/2026-04-21--attention-is-all-you-need.md

working.md append:
  [14:35] EXTRACT ✓ "Attention Is All You Need" | 5 key points | 2 gaps

update_research_map() → update vault/memory/research.md

Task mv ke done/
Task baru dibuat: queue/pending/synthesize_20260421_143501_001.json

─── STAGE 3: SYNTHESIZE ──────────────────────────────────────

(Ditunggu sampai semua extract task untuk topik "transformer-architecture" selesai)
Worker ambil synthesize task
AI CLI baca semua vault/extracted/ yang bertopik sama
Sintesis lintas dokumen → consensus, contradiction, key findings
Tulis: vault/synthesis/transformer-architecture.md

working.md append:
  [15:10] SYNTHESIZE ✓ "transformer-architecture" | 12 dokumen | 3 gap baru

Task mv ke done/
check_trigger_final_report() → belum semua topik selesai, tunggu

─── FINAL REPORT (setelah semua topik selesai) ───────────────

Pipeline 2 Stage 3: AI CLI jawab pertanyaan riset
Tulis: vault/output/final-report.md

─── SELESAI ──────────────────────────────────────────────────
```

---

## Self-Improving Loop

```
                    ┌─────────────────────┐
                    │  research_config    │
                    │  .yaml              │
                    └──────────┬──────────┘
                               │
                               ▼
              ┌────────────────────────────────┐
         ┌───►│   QUERY GENERATION             │
         │    │   baca research.md + config    │
         │    │   AI CLI → targeted queries    │
         │    └────────────────┬───────────────┘
         │                     │
         │                     ▼
         │    ┌────────────────────────────────┐
         │    │   FETCH                        │
         │    │   Pipeline 1                   │
         │    └────────────────┬───────────────┘
         │                     │
         │                     ▼
         │    ┌────────────────────────────────┐
         │    │   EXTRACT                      │
         │    │   Pipeline 2 Stage 1           │
         │    └────────────────┬───────────────┘
         │                     │
         │                     ▼
         │    ┌────────────────────────────────┐
         │    │   UPDATE RESEARCH MAP          │
         │    │   AI CLI → perbarui research.md│
         │    │   (dipanggil per Extract done) │
         │    │   • gap baru ditemukan?        │
         │    │   • pertanyaan terjawab?       │
         │    └────────────────┬───────────────┘
         │                     │
         │                     ▼
         │    ┌────────────────────────────────┐
         │    │   SYNTHESIZE                   │
         │    │   Pipeline 2 Stage 2           │
         │    │   (menggunakan research.md)    │
         │    └────────────────┬───────────────┘
         │                     │
         │          ┌──────────┴──────────┐
         │          │                     │
         │    ada OPEN gap?         semua ANSWERED?
         │          │                     │
         └──────────┘                     ▼
          (putaran baru)          FINAL REPORT
```

---

## Routing Telegram Commands

```
Pesan masuk ke Hermes Agent (topic Research)
          │
          ├── /sst-rx-new [nama]       → buat project baru + setup conversation
          │                               cek JINA_API_KEY di ~/.hermes/.env
          │                               + 5 pertanyaan riset + query gen
          │                               + fetch candidates + create tasks
          │                               (TIDAK start worker)
          │
          ├── /sst-rx-start            → start/resume worker saja
          │
          ├── /sst-rx-stop             → stop worker
          │
          ├── /sst-rx-status           → baca queue/ folder counts (zero token)
          │
          ├── /sst-rx-memory           → baca working.md + research.md → ringkasan
          │
          ├── /sst-rx-memory-gaps      → baca research.md → gap terbuka
          │
          ├── /sst-rx-memory-status    → baca working.md → 20 entry terakhir
          │
          ├── /sst-rx-memory-summarize → panggil AI CLI → kompres memory
          │
          ├── /sst-rx-report           → baca vault/output/final-report.md
          │
          ├── /sst-rx-list             → scan ~/projects/project-rx-*/research_config.yaml
          │                               tampilkan semua project + status
          │
          └── /sst-rx-archive          → zip vault/ + kirim file ke Telegram chat
```

---

## Orchestrator: `run_research.sh`

### Siapa: ⚙️ Bash — Entry point utama sistem

Terinspirasi dari pattern `run_pipeline.sh` yang sudah terbukti. Ini yang mengikat 
semua komponen menjadi satu alur yang bisa dijalankan dengan satu command.

```bash
bash run_research.sh                  # full pipeline
bash run_research.sh setup            # inisialisasi project baru
bash run_research.sh fetch            # hanya fetch kandidat
bash run_research.sh worker           # jalankan sliding window worker
bash run_research.sh report           # generate final report
bash run_research.sh status           # cek status queue
bash run_research.sh memory-summarize # kompres & rapikan memory
```

### Implementasi

```bash
#!/usr/bin/env bash
# =============================================================================
# run_research.sh — SST Research Agent Pipeline Launcher
# Jalankan: bash run_research.sh [step]
# Steps   : all | setup | fetch | worker | report | status | memory-summarize
# =============================================================================

set -euo pipefail

REPO="$(cd "$(dirname "$0")" && pwd)"
VENV="$REPO/.venv/bin/python"
TODAY=$(date +%Y%m%d)
LOG_DIR="$REPO/logs"
STEP="${1:-all}"

# ── Colors ────────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; NC='\033[0m'

log_ok()   { echo -e "${GREEN}✓${NC} $1"; }
log_err()  { echo -e "${RED}✗${NC} $1"; }
log_info() { echo -e "${CYAN}→${NC} $1"; }
log_warn() { echo -e "${YELLOW}⚠${NC} $1"; }
log_head() { echo -e "\n${BLUE}═══ $1 ═══${NC}"; }

# ── Preflight ─────────────────────────────────────────────────────────────────
preflight() {
  log_head "PREFLIGHT CHECK"

  # Repo
  [ -d "$REPO" ] && log_ok "Repo: $REPO" \
    || { log_err "Repo tidak ditemukan"; exit 1; }

  # venv
  [ -f "$VENV" ] && log_ok "Python venv: $VENV" \
    || { log_err "venv tidak ditemukan — jalankan: python -m venv .venv && .venv/bin/pip install -r requirements.txt"; exit 1; }

  # .env (project — hanya TELEGRAM_CHAT_ID)
  [ -f "$REPO/.env" ] && log_ok ".env ditemukan (TELEGRAM_CHAT_ID)" \
    || { log_err ".env tidak ditemukan — copy dari .env.example dan isi TELEGRAM_CHAT_ID"; exit 1; }

  # ~/.hermes/.env (API keys: JINA_API_KEY, TELEGRAM_BOT_TOKEN)
  [ -f "$HOME/.hermes/.env" ] && log_ok "~/.hermes/.env ditemukan (API keys)" \
    || log_warn "~/.hermes/.env tidak ditemukan — gunakan /sst-rx-new untuk setup API keys"

  # ccs CLI
  command -v ccs &>/dev/null && log_ok "ccs CLI tersedia" \
    || { log_err "ccs CLI tidak ditemukan — pastikan sudah terinstall"; exit 1; }

  # Hermes gateway
  hermes gateway status &>/dev/null && log_ok "Hermes gateway running" \
    || log_warn "Hermes gateway tidak berjalan — jalankan: hermes gateway install"

  # Queue & vault folders
  for dir in queue/pending queue/active queue/done queue/failed queue/dead \
             vault/sources vault/extracted vault/synthesis vault/output vault/memory; do
    mkdir -p "$REPO/$dir"
  done
  log_ok "Queue & vault folders ready"

  mkdir -p "$LOG_DIR"
  cd "$REPO"
}

# ── Steps ─────────────────────────────────────────────────────────────────────
step_setup() {
  log_head "SETUP — Inisialisasi Project"
  "$VENV" "$REPO/orchestrator/setup.py" --init 2>&1 | tee "$LOG_DIR/setup_$TODAY.log"

  # Register cron jobs otomatis
  log_info "Mendaftarkan cron jobs..."
  CRON_NOTIFY="*/5 * * * * cd $REPO && $VENV orchestrator/notify.py --summary >> $LOG_DIR/notify.log 2>&1"
  CRON_WATCHDOG="*/2 * * * * cd $REPO && $VENV orchestrator/watchdog.py >> $LOG_DIR/watchdog.log 2>&1"
  CRON_INDEXER="0 * * * * cd $REPO && $VENV scripts/indexer.py --rebuild >> $LOG_DIR/indexer.log 2>&1"

  # Tambahkan hanya jika belum ada
  (crontab -l 2>/dev/null | grep -v "$REPO"; \
   echo "$CRON_NOTIFY"; \
   echo "$CRON_WATCHDOG"; \
   echo "$CRON_INDEXER") | crontab -

  log_ok "Cron jobs terdaftar:"
  log_info "  notify.py   → setiap 5 menit"
  log_info "  watchdog.py → setiap 2 menit"
  log_info "  indexer.py  → setiap jam"

  log_ok "Setup selesai — kirim /sst-rx-start di Telegram untuk mulai"
}

step_fetch() {
  log_head "FETCH — Generate Queries & Kandidat"
  "$VENV" "$REPO/orchestrator/query_gen.py" 2>&1 | tee "$LOG_DIR/fetch_$TODAY.log"
  "$VENV" "$REPO/orchestrator/relevance.py" 2>&1 | tee -a "$LOG_DIR/fetch_$TODAY.log"
  PENDING=$(ls queue/pending/ | wc -l | tr -d ' ')
  log_ok "Fetch selesai → $PENDING task di queue/pending/"
}

step_worker() {
  log_head "WORKER — Sliding Window Executor"

  # Cek apakah worker sudah running
  if [ -f "$LOG_DIR/worker.pid" ]; then
    OLD_PID=$(cat "$LOG_DIR/worker.pid")
    if ps -p "$OLD_PID" > /dev/null 2>&1; then
      log_warn "Worker sudah running (PID: $OLD_PID)"
      log_info "Untuk restart: kill $OLD_PID && bash run_research.sh worker"
      return 0
    fi
  fi

  log_info "Starting worker (background)..."
  nohup "$VENV" "$REPO/orchestrator/worker.py" \
    > "$LOG_DIR/worker_$TODAY.log" 2>&1 &
  WORKER_PID=$!
  echo "$WORKER_PID" > "$LOG_DIR/worker.pid"
  log_ok "Worker started — PID: $WORKER_PID"
  log_info "Log: $LOG_DIR/worker_$TODAY.log"

  sleep 3
  if ps -p "$WORKER_PID" > /dev/null 2>&1; then
    log_ok "Worker berjalan ✓"
    tail -5 "$LOG_DIR/worker_$TODAY.log"
  else
    log_err "Worker exit setelah start — cek log!"
    tail -20 "$LOG_DIR/worker_$TODAY.log"
  fi
}

step_report() {
  log_head "REPORT — Generate Final Report"
  "$VENV" "$REPO/synthesis/reporter.py" 2>&1 | tee "$LOG_DIR/report_$TODAY.log"
  REPORT="$REPO/vault/output/final-report.md"
  [ -f "$REPORT" ] && log_ok "Report: $REPORT" \
    || log_err "Report tidak ditemukan"
}

step_status() {
  log_head "STATUS — Queue Overview"
  PENDING=$(ls queue/pending/ 2>/dev/null | wc -l | tr -d ' ')
  ACTIVE=$(ls queue/active/  2>/dev/null | wc -l | tr -d ' ')
  DONE=$(ls queue/done/      2>/dev/null | wc -l | tr -d ' ')
  FAILED=$(ls queue/failed/  2>/dev/null | wc -l | tr -d ' ')
  DEAD=$(ls queue/dead/      2>/dev/null | wc -l | tr -d ' ')
  TOTAL=$((PENDING + ACTIVE + DONE + FAILED + DEAD))

  echo ""
  echo -e "  📊 Queue Status"
  echo -e "  ├─ Pending  : ${CYAN}$PENDING${NC}"
  echo -e "  ├─ Active   : ${CYAN}$ACTIVE${NC}/5"
  echo -e "  ├─ Done     : ${GREEN}$DONE${NC}"
  echo -e "  ├─ Failed   : ${YELLOW}$FAILED${NC}"
  echo -e "  └─ Dead     : ${RED}$DEAD${NC}"
  echo -e "  Total       : $TOTAL task"
  echo ""

  if [ -f "vault/memory/research.md" ]; then
    log_info "research.md ditemukan — memory aktif"
  else
    log_warn "research.md belum ada — belum ada extract yang selesai"
  fi
}

step_memory_summarize() {
  log_head "MEMORY — Kompres & Rapikan"
  "$VENV" "$REPO/memory/memory.py" --summarize 2>&1 | tee "$LOG_DIR/memory_$TODAY.log"
  log_ok "Memory summarize selesai"
}

# ── Main ──────────────────────────────────────────────────────────────────────
main() {
  echo ""
  echo -e "${BLUE}╔══════════════════════════════════════════╗${NC}"
  echo -e "${BLUE}║   SST Research Agent — Pipeline Launcher ║${NC}"
  echo -e "${BLUE}║   $(date '+%Y-%m-%d %H:%M:%S')                  ║${NC}"
  echo -e "${BLUE}╚══════════════════════════════════════════╝${NC}"

  preflight

  case "$STEP" in
    all)
      step_fetch
      step_worker
      ;;
    setup)             step_setup  ;;
    fetch)             step_fetch  ;;
    worker)            step_worker ;;
    report)            step_report ;;
    status)            step_status ;;
    memory-summarize)  step_memory_summarize ;;
    *)
      echo "Usage: bash run_research.sh [all|setup|fetch|worker|report|status|memory-summarize]"
      exit 1
      ;;
  esac

  log_head "SELESAI"
  echo -e "${GREEN}Pipeline selesai — $(date '+%H:%M:%S')${NC}"
  echo ""
}

main "$@"
```

---

## Kepemilikan Vault (Territory Map)

```
vault/
├── _index.md           ← 🐍 indexer.py (rebuild tiap jam)
├── _topics/            ← 🐍 Pipeline 3 (saat setup)
│
├── sources/            ← 🐍 Pipeline 1 SAJA yang menulis
├── extracted/          ← 🤖 Pipeline 2 Stage 1 SAJA yang menulis
├── synthesis/          ← 🤖 Pipeline 2 Stage 2 SAJA yang menulis
├── output/             ← 🤖 Pipeline 2 Stage 3 SAJA yang menulis
└── memory/             ← 🐍🤖 Pipeline 4 SAJA yang menulis
    ├── working.md      ← 🐍 append otomatis per task (zero AI)
    ├── research.md     ← 🤖 AI CLI per stage Extract selesai
    └── meta.md         ← 🤖 AI CLI saat project selesai
```

**Aturan besi:** Setiap pipeline hanya boleh **menulis** ke folder miliknya.
Semua pipeline boleh **membaca** folder manapun.

---

## Token Usage Map

```
SETUP RISET
├── Tanya jawab Telegram     → Hermes Agent (zero AI CLI token)
├── Tulis config             → Python (zero token)
├── Generate queries         → AI CLI × 1
└── Relevance scoring        → AI CLI × N kandidat

PER TASK FETCH (× jumlah sumber)
├── Jina Reader / arXiv      → zero AI CLI token (HTTP request)
└── Append working.md        → zero token

PER TASK EXTRACT (× jumlah dokumen)
└── AI CLI ekstrak klaim     → AI CLI × 1 per dokumen

PER STAGE EXTRACT SELESAI (batch)
└── Update research.md       → AI CLI × 1 per stage Extract selesai

PER TOPIK SYNTHESIZE (× jumlah topik)
└── AI CLI sintesis          → AI CLI × 1 per topik

PROJECT SELESAI (× 1)
├── Final Report             → AI CLI × 1
└── Write meta.md            → AI CLI × 1

NOTIFIKASI (Linux crontab, zero token)
├── Per task done            → Python → Telegram Bot API
├── Summary per 5 menit      → Python → Telegram Bot API
└── Stage selesai            → Python → Telegram Bot API
```

---

## File & Folder Structure Lengkap

```
master-repo/                          ← yang ada di GitHub
│
├── new-project.sh                    ← clone & init project baru
├── archive-project.sh                ← arsipkan project lama
├── README.md
│
└── project-template/                 ← template yang di-copy tiap project baru
    │
    ├── run_research.sh               ← orchestrator utama
    ├── requirements.txt
    ├── .env.example
    ├── config.yaml                   ← konfigurasi terpusat
    │
    ├── connectors/                   ← Pipeline 1
    │   ├── core/
    │   │   ├── jina_search.py
    │   │   ├── jina_reader.py
    │   │   └── arxiv.py
    │   ├── plugins/
    │   ├── base_connector.py
    │   └── pipeline.py
    │
    ├── synthesis/                    ← Pipeline 2
    │   ├── extractor.py
    │   ├── synthesizer.py
    │   ├── reporter.py
    │   ├── llm_client.py
    │   ├── citation.py
    │   └── utils.py
    │
    ├── orchestrator/                 ← Pipeline 3
    │   ├── setup.py
    │   ├── query_gen.py
    │   ├── relevance.py
    │   ├── worker.py
    │   ├── notify.py
    │   └── watchdog.py
    │
    ├── memory/                       ← Pipeline 4
    │   └── memory.py
    │
    └── scripts/
        ├── audit.py
        └── indexer.py

─────────────────────────────────────── ← .gitignore boundary

project-rx-ai-alignment/              ← di-gitignore, local only
├── (copy dari project-template/)
├── .env                              ← gitignored (hanya TELEGRAM_CHAT_ID)
├── research_config.yaml              ← gitignored
├── setup_state.json                  ← gitignored
├── queue/                            ← gitignored
│   ├── pending/
│   ├── active/
│   ├── done/
│   ├── failed/
│   └── dead/
├── vault/                            ← gitignored
│   ├── _index.md
│   ├── sources/
│   ├── extracted/
│   ├── synthesis/
│   ├── output/
│   └── memory/
└── logs/                             ← gitignored

project-rx-llm-survey/                ← project lain, sama strukturnya
└── ...

archives/                             ← hasil archive-project.sh
├── project-rx-ai-alignment-2026.zip
└── project-rx-llm-survey-2026.zip
```

### `new-project.sh`

```bash
#!/usr/bin/env bash
# Buat project riset baru dari template
# API keys (JINA_API_KEY, TELEGRAM_BOT_TOKEN) ada di ~/.hermes/.env
# Project .env hanya berisi TELEGRAM_CHAT_ID

PROJECT_NAME="${1:-project-rx-$(date +%Y%m%d)}"
MASTER_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$MASTER_DIR/$PROJECT_NAME"
MASTER_ENV="$MASTER_DIR/.env"      # hanya TELEGRAM_CHAT_ID

echo "🔬 Membuat project: $PROJECT_NAME"

# Copy dari template
cp -r "$MASTER_DIR/project-template/" "$PROJECT_DIR"

# Buat folder runtime (gitignored)
mkdir -p "$PROJECT_DIR"/{queue/{pending,active,done,failed,dead},vault/{_topics,sources,extracted,synthesis,output,memory},logs}

# Copy .env dari master repo (hanya TELEGRAM_CHAT_ID)
if [ -f "$MASTER_ENV" ]; then
    cp "$MASTER_ENV" "$PROJECT_DIR/.env"
    echo "✅ .env di-copy dari master repo (TELEGRAM_CHAT_ID)"
else
    cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/.env"
    echo "⚠️  Master .env belum ada — gunakan /sst-rx-new via Telegram untuk setup"
fi

# API keys (JINA_API_KEY, TELEGRAM_BOT_TOKEN) dibaca dari ~/.hermes/.env
echo "ℹ️  API keys dibaca dari ~/.hermes/.env"

# Setup venv
cd "$PROJECT_DIR"
python -m venv .venv
.venv/bin/pip install -r requirements.txt -q

echo ""
echo "✅ Project '$PROJECT_NAME' siap di: $PROJECT_DIR"
```

---

## Startup Sequence

```
1. Clone master repo ke Mac Mini (SEKALI SAJA):
   git clone https://github.com/username/sst-research ~/projects/sst-research-master
   hermes skills install github.com/username/sst-research

2. Setup DM Topic Research di ~/.hermes/config.yaml → hermes gateway restart

3. Via Telegram — kirim /sst-rx-new project-rx-nama-project:
   → Hermes cek JINA_API_KEY di ~/.hermes/.env
   → Jika tidak ada, Hermes tanya user via Telegram dan tulis ke ~/.hermes/.env
   → Hermes tanya TELEGRAM_CHAT_ID (SEKALI, tulis ke project .env)
   → Hermes buat project, setup riset (5 pertanyaan)
   → Hermes jalankan query gen + fetch candidates + create tasks
   → Hermes kirim: "Ketik /sst-rx-start untuk memulai worker"

4. User kirim /sst-rx-start → worker mulai. Notif tiap 5 menit.
   Project berikutnya: /sst-rx-new project-rx-nama-lain → tidak ditanya API key lagi
```

---

## Recovery Scenarios

### Server / Mac mati saat worker berjalan
```bash
# Task stuck di active/ tanpa worker
mv queue/active/*.json queue/pending/
bash run_research.sh worker
```

### AI CLI timeout berulang
```
Fallback chain dicoba otomatis:
  ccs glm → gagal → ccs codex → gagal → ccs claude → RuntimeError
Dead task dilaporkan di notif stage selesai
```

### Setup Telegram terputus di tengah jalan
```
setup_state.json menyimpan state terakhir
Kirim /sst-rx-new [nama] lagi → lanjut dari pertanyaan yang belum dijawab
```

### Vault tidak konsisten
```bash
.venv/bin/python scripts/audit.py --verify
```

---

## Checklist Sebelum Mulai

```
Environment
[ ] ~/.hermes/.env sudah diisi (JINA_API_KEY, TELEGRAM_BOT_TOKEN)
[ ] Project .env sudah diisi (TELEGRAM_CHAT_ID)
[ ] TELEGRAM_BOT_TOKEN di ~/.hermes/.env sama dengan ~/.hermes/config.yaml
[ ] .venv/bin/python tersedia (bash new-project.sh sudah buat otomatis)

Tools (sudah ada di Mac, tidak perlu install)
[ ] hermes sudah terinstall & gateway running
[ ] ccs sudah terinstall

Cron
[ ] crontab -e: 3 job sudah terdaftar

Test
[ ] bash run_research.sh status → tidak ada error
[ ] Kirim /sst-rx-start ke Telegram → agent merespons
```

---

## Catatan Penting

- **`run_research.sh` adalah entry point tunggal** — satu command untuk semua
- **Komunikasi antar pipeline via file** — tidak ada direct function call, crash-safe
- **1 project = 1 folder** — clone dari `project-template/`, gitignored dari master repo
- **Token usage minimal** — fetch & notifikasi zero AI token, AI CLI hanya untuk extract/synthesize/memory
- **Recovery selalu bisa dilakukan** — semua state di file, tidak ada yang hilang saat crash
- **`/sst-rx-list`** scan semua folder `~/projects/project-rx-*/research_config.yaml`
