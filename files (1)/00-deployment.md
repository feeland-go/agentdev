# 00 — Deployment Guide

## Konteks Penting Sebelum Membaca

```
✅ Mac Mini sudah ada Hermes + terhubung ke Telegram
✅ ccs sudah terinstall
✅ Semua interaksi HANYA via Telegram — tidak ada akses terminal langsung
✅ .env diisi via Telegram (Hermes menulis file menggunakan terminal tools-nya)
✅ Skill = instruksi untuk Hermes, bukan script terpisah
```

---

## Story Deployment (Baca Ini Dulu)

Ini cerita lengkap dari nol sampai riset berjalan — tanpa menyentuh terminal sekalipun.

```
Hari 1 — Setup Awal (SEKALI SAJA, di terminal):

1. git clone https://github.com/username/sst-research ~/projects/sst-research-master
2. hermes skills install github.com/username/sst-research
3. Tambahkan DM Topic "Research" di ~/.hermes/config.yaml → hermes gateway restart

Setelah ini, SEMUANYA via Telegram:

4. User: /sst-rx-new project-rx-ai-alignment

   → Hermes cek ~/.hermes/.env — JINA_API_KEY belum ada
   → Hermes: "Masukkan JINA_API_KEY kamu:"
   → User: jina_xxxx
   → Hermes tulis JINA_API_KEY ke ~/.hermes/.env

   → Hermes cek master .env — TELEGRAM_CHAT_ID belum ada
   → Hermes: "Masukkan TELEGRAM_CHAT_ID kamu:"
   → User: 123456789
   → Hermes tulis TELEGRAM_CHAT_ID ke ~/projects/sst-research-master/.env

   → Hermes buat project dari template
   → Hermes: "Apa topik utama riset ini?"
   → User: AI Alignment
   → Hermes: "Pertanyaan riset? (DONE jika selesai)"
   → User: Apa metode alignment paling efektif?
   → User: DONE
   → ... (3 pertanyaan lagi)
   → Hermes tampilkan ringkasan → User: YES
   → Hermes tulis research_config.yaml
   → Hermes jalankan generate queries + fetch candidates
   → Hermes: "✅ Project project-rx-ai-alignment siap! 487 task antri. Jalankan /sst-rx-start untuk mulai worker."

5. User: /sst-rx-start
   → Worker berjalan. Notif masuk dari Python notify.py.

6. User: /sst-rx-status → lihat queue
   User: /sst-rx-memory-gaps → lihat gap riset
   User: /sst-rx-stop → hentikan worker sementara
   User: /sst-rx-start → jalankan lagi

7. Setelah selesai:
   User: /sst-rx-report → ringkasan final report
   User: /sst-rx-archive → zip vault + kirim ke chat ini

8. Project berikutnya:
   User: /sst-rx-new project-rx-llm-survey
   → JINA_API_KEY sudah ada di ~/.hermes/.env → skip
   → TELEGRAM_CHAT_ID sudah ada di master .env → skip
   → Langsung ke setup riset
```

---

## Struktur Repo

```
master-repo/                          ← ada di GitHub
├── new-project.sh
├── archive-project.sh
├── README.md
├── skills/
│   └── sst-research/
│       ├── SKILL.md                  ← skill utama
│       └── scripts/
│           └── setup-env.sh          ← helper tulis .env
└── project-template/
    ├── run_research.sh
    ├── requirements.txt
    ├── .env.example
    ├── config.yaml
    ├── connectors/
    ├── synthesis/
    ├── orchestrator/
    ├── memory/
    └── scripts/
```

---

## Skills Catalog (Urut Berdasarkan Workflow)

### Format Nama
```
/sst-rx-{nama-skill}
```

### Urutan Workflow

| # | Command | Kapan Dipakai |
|---|---|---|
| 1 | `/sst-rx-new` | Buat project baru + setup riset (topik, pertanyaan, dll) + generate queries + fetch candidates. TIDAK start worker otomatis. |
| 2 | `/sst-rx-start` | Start/resume sliding window worker. Jalankan setelah setup selesai, atau untuk resume worker yang dihentikan. |
| 3 | `/sst-rx-stop` | Stop worker |
| 4 | `/sst-rx-status` | Cek status queue real-time |
| 5 | `/sst-rx-memory` | Lihat ringkasan memory riset |
| 6 | `/sst-rx-memory-gaps` | Lihat gap yang belum terjawab |
| 7 | `/sst-rx-memory-status` | Lihat progress terkini |
| 8 | `/sst-rx-memory-summarize` | Kompres memory dengan AI CLI (`run_research.sh memory-summarize`) |
| 9 | `/sst-rx-report` | Lihat ringkasan final report |
| 10 | `/sst-rx-list` | List semua project riset |
| 11 | `/sst-rx-archive` | Arsipkan project + kirim zip ke Telegram |

---

## SKILL.md Lengkap

Simpan di: `skills/sst-research/SKILL.md` dalam master repo.

```markdown
---
name: sst-research
description: SST Research Agent — kelola pipeline riset akademik & industri dari Telegram. Handles project creation, research setup, queue management, memory, dan archiving.
version: 1.0.0
author: SST
platforms: [macos]
---

# SST Research Agent

Pipeline riset otomatis yang fetch sumber dari Jina AI + arXiv, ekstrak klaim,
sintesis per topik, dan hasilkan laporan final — semua dikelola via Telegram.

Master repo   : ~/projects/sst-research-master
Projects dir  : ~/projects/
Active project: simpan/baca dari ~/.hermes/sst_active_project

## Cara Baca Active Project

Sebelum menjalankan command apapun yang butuh project path:
```bash
PROJECT=$(cat ~/.hermes/sst_active_project 2>/dev/null)
PROJECT_DIR="$HOME/projects/$PROJECT"
```

---

## /sst-rx-new [nama-project]

**Kapan dipakai:** Buat project riset baru sekaligus setup topik, pertanyaan riset,
dan parameter pencarian. Melakukan FULL setup: create project + research setup conversation +
generate queries + fetch candidates. TIDAK start worker otomatis — gunakan `/sst-rx-start` setelah selesai.

**Format nama:** lowercase, dash separator, prefix project-rx-
Contoh: project-rx-ai-alignment, project-rx-llm-survey-2026, project-rx-climate-policy

### Langkah 1 — Cek ~/.hermes/.env (JINA_API_KEY)

```bash
HERMES_ENV="$HOME/.hermes/.env"
```

Jika `JINA_API_KEY` belum ada di `~/.hermes/.env`, tanya via Telegram (SEKALI SAJA):
```
🤖: "Masukkan JINA_API_KEY kamu: (https://jina.ai)"
USER: jina_xxxx

→ Hermes tulis JINA_API_KEY ke ~/.hermes/.env
```

Jika sudah ada, skip.

### Langkah 1b — Cek Master .env (TELEGRAM_CHAT_ID)

```bash
MASTER_ENV="$HOME/projects/sst-research-master/.env"
```

Jika `TELEGRAM_CHAT_ID` belum ada di master `.env`, tanya via Telegram (SEKALI SAJA):
```
🤖: "Masukkan TELEGRAM_CHAT_ID kamu: (kirim pesan ke @userinfobot)"
USER: 123456789

→ Hermes tulis TELEGRAM_CHAT_ID ke ~/projects/sst-research-master/.env
```

Jika sudah ada, skip langsung ke Langkah 2.

### Langkah 2 — Buat Project

```bash
bash ~/projects/sst-research-master/new-project.sh {nama}
# → copy project-template + copy .env dari master repo (TELEGRAM_CHAT_ID) + setup venv
echo "{nama}" > ~/.hermes/sst_active_project
```

### Langkah 3 — Setup Riset (AI-driven conversation)

Tanya satu per satu, tunggu jawaban sebelum lanjut:

```
[1/5] "Apa topik utama riset ini?"

[2/5] "Apa pertanyaan riset yang ingin dijawab?
       Ketik satu per pesan, ketik DONE jika selesai."

[3/5] "Ada sub-topik spesifik? (SKIP untuk lewati)
       Contoh: RLHF, Constitutional AI"

[4/5] "Batasan waktu publikasi? (SKIP untuk semua waktu)
       Contoh: 2020-2025"

[5/5] "Kategori arXiv yang relevan? (SKIP untuk semua)
       Contoh: cs.AI, cs.LG, stat.ML"
```

Tampilkan konfirmasi ringkasan, tunggu YES/NO.

### Langkah 4 — Jalankan Pipeline

Jika YES:
```bash
PROJECT_DIR="$HOME/projects/{nama}"
python $PROJECT_DIR/orchestrator/setup.py --write-config '{json_answers}'
python $PROJECT_DIR/memory/memory.py --init
bash $PROJECT_DIR/run_research.sh fetch
```

Balas: "✅ Project {nama} siap! {n} task antri. Jalankan /sst-rx-start untuk mulai worker."

**Crash recovery:** Jika `setup_state.json` sudah ada, baca state terakhir dan
lanjutkan dari pertanyaan yang belum dijawab.

---

## /sst-rx-start

**Kapan dipakai:** Start/resume sliding window worker. Jalankan setelah `/sst-rx-new` selesai setup, atau untuk resume worker yang dihentikan.

```bash
PROJECT=$(cat ~/.hermes/sst_active_project 2>/dev/null)
bash ~/projects/$PROJECT/run_research.sh worker
```

Tampilkan PID dan path log.

---

## /sst-rx-stop

**Kapan dipakai:** Hentikan worker yang sedang berjalan.

```bash
PROJECT=$(cat ~/.hermes/sst_active_project 2>/dev/null)
PID=$(cat ~/projects/$PROJECT/logs/worker.pid 2>/dev/null)
if [ -n "$PID" ] && ps -p "$PID" > /dev/null 2>&1; then
  kill "$PID"
  echo "✅ Worker dihentikan (PID: $PID)"
else
  echo "⚠️ Worker tidak berjalan"
fi
```

---

## /sst-rx-status

**Kapan dipakai:** Cek status queue dan progress riset real-time. ZERO token AI CLI.

```bash
PROJECT=$(cat ~/.hermes/sst_active_project 2>/dev/null)
DIR="$HOME/projects/$PROJECT/queue"
echo "📊 Status: $PROJECT"
echo "Pending : $(ls $DIR/pending/ 2>/dev/null | wc -l | tr -d ' ')"
echo "Active  : $(ls $DIR/active/  2>/dev/null | wc -l | tr -d ' ')/5"
echo "Done    : $(ls $DIR/done/    2>/dev/null | wc -l | tr -d ' ')"
echo "Failed  : $(ls $DIR/failed/  2>/dev/null | wc -l | tr -d ' ')"
echo "Dead    : $(ls $DIR/dead/    2>/dev/null | wc -l | tr -d ' ')"
```

---

## /sst-rx-memory

**Kapan dipakai:** Lihat ringkasan working memory + research map.

Baca dan ringkas:
- `{PROJECT_DIR}/vault/memory/working.md` → 10 entry terakhir
- `{PROJECT_DIR}/vault/memory/research.md` → status pertanyaan + gap terbuka

---

## /sst-rx-memory-gaps

**Kapan dipakai:** Lihat gap riset yang belum terjawab.

Baca section "Gap Terbuka" dari `{PROJECT_DIR}/vault/memory/research.md`
Tampilkan sebagai daftar yang actionable.

---

## /sst-rx-memory-status

**Kapan dipakai:** Lihat progress terkini (task apa yang terakhir selesai).

Baca 20 entry terakhir dari `{PROJECT_DIR}/vault/memory/working.md`

---

## /sst-rx-memory-summarize

**Kapan dipakai:** Kompres dan rapikan semua memory yang sudah panjang. Memanggil AI CLI.

```bash
bash {PROJECT_DIR}/run_research.sh memory-summarize
```

---

## /sst-rx-report

**Kapan dipakai:** Lihat ringkasan final report setelah riset selesai.

Baca `{PROJECT_DIR}/vault/output/final-report.md`
Tampilkan: overall conclusion + answered questions summary + suggested further research.
Jika file belum ada: "Final report belum tersedia — riset masih berjalan."

---

## /sst-rx-list

**Kapan dipakai:** List semua project riset yang pernah dibuat.

```bash
for dir in ~/projects/project-rx-*/; do
  name=$(basename "$dir")
  if [ -f "$dir/research_config.yaml" ]; then
    topic=$(grep "topic:" "$dir/research_config.yaml" | head -1 | cut -d'"' -f2)
    done_count=$(ls "$dir/queue/done/" 2>/dev/null | wc -l | tr -d ' ')
    pending_count=$(ls "$dir/queue/pending/" 2>/dev/null | wc -l | tr -d ' ')
    if [ -f "$dir/vault/output/final-report.md" ]; then
      status="selesai ✅"
    elif [ "$pending_count" -gt 0 ] || [ "$(ls $dir/queue/active/ 2>/dev/null | wc -l)" -gt 0 ]; then
      status="berjalan 🔄 ($done_count done)"
    else
      status="setup/pause ⏸"
    fi
    echo "• $name — $topic [$status]"
  fi
done
```

Tandai project aktif dengan ⭐

---

## /sst-rx-archive

**Kapan dipakai:** Arsipkan project yang sudah selesai. Zip vault + kirim ke Telegram chat.

**Langkah:**
1. Jalankan archive script:
   ```bash
   bash ~/projects/sst-research-master/archive-project.sh {PROJECT}
   ```
   Output: `~/projects/archives/{PROJECT}.zip`

2. Kirim zip ke Telegram menggunakan send_file tool atau:
   ```bash
   TOKEN=$(grep TELEGRAM_BOT_TOKEN ~/.hermes/.env | cut -d= -f2)
   CHAT_ID=$(grep TELEGRAM_CHAT_ID {PROJECT_DIR}/.env | cut -d= -f2)
   curl -s -F "chat_id=$CHAT_ID" \
        -F "document=@$HOME/projects/archives/{PROJECT}.zip" \
        -F "caption=📦 Archive: {PROJECT}" \
        "https://api.telegram.org/bot$TOKEN/sendDocument"
   ```

3. Tanya: "Hapus folder project setelah archive? (YES / NO)"
   - YES: `rm -rf ~/projects/{PROJECT}`
   - NO: biarkan

4. Balas: "✅ Archive {PROJECT}.zip sudah dikirim ke chat ini."

---

## Troubleshooting

| Masalah | Solusi |
|---|---|
| Worker mati | `/sst-rx-start` |
| Task stuck di active/ | Hermes: `mv ~/projects/{proj}/queue/active/*.json ~/projects/{proj}/queue/pending/` lalu `/sst-rx-start` |
| `.env` salah isi | Cek `~/.hermes/.env` (JINA_API_KEY, TELEGRAM_BOT_TOKEN) dan master `.env` (TELEGRAM_CHAT_ID) |
| Notif tidak masuk | Cek `TELEGRAM_CHAT_ID` di master `.env` dan `TELEGRAM_BOT_TOKEN` di `~/.hermes/.env` |
| Setup terpotong | `/sst-rx-new` lagi — Hermes baca `setup_state.json` dan lanjutkan |
```

---

## .env — Input Sekali, Berlaku Semua Project

Secrets disimpan di dua tempat:
- **`~/.hermes/.env`** — TELEGRAM_BOT_TOKEN (sudah ada untuk Hermes) + JINA_API_KEY (ditambahkan saat pertama `/sst-rx-new`)
- **Master `.env`** (`~/projects/sst-research-master/.env`) — TELEGRAM_CHAT_ID (user-specific)

Setiap project baru otomatis meng-copy master `.env` (TELEGRAM_CHAT_ID) — user tidak perlu input ulang.

Python scripts (notify.py dll.) membaca `TELEGRAM_BOT_TOKEN` dan `JINA_API_KEY` dari `~/.hermes/.env`, dan `TELEGRAM_CHAT_ID` dari project `.env`.

### Struktur

```
~/.hermes/.env                              ← TELEGRAM_BOT_TOKEN + JINA_API_KEY
~/projects/sst-research-master/.env         ← TELEGRAM_CHAT_ID (sumber kebenaran)
~/projects/project-rx-ai-alignment/.env     ← copy dari master saat project dibuat
~/projects/project-rx-llm-survey/.env       ← copy dari master saat project dibuat
```

### Isi `~/.hermes/.env`

```env
# ~/.hermes/.env (sudah ada untuk Hermes, JINA_API_KEY ditambahkan saat pertama /sst-rx-new)
TELEGRAM_BOT_TOKEN=bot_xxxxxxxxxxxxxxxxxxxx
JINA_API_KEY=jina_xxxxxxxxxxxxxxxxxxxx
```

### Isi `.env` Master Repo

```env
# ~/projects/sst-research-master/.env
TELEGRAM_CHAT_ID=123456789
```

### Setup Pertama Kali (via Telegram)

Ketika `/sst-rx-new` dijalankan:
1. Cek `~/.hermes/.env` — jika `JINA_API_KEY` belum ada, tanya via Telegram
2. Cek master `.env` — jika `TELEGRAM_CHAT_ID` belum ada, tanya via Telegram

```
🤖: Ini pertama kali setup.

    Masukkan JINA_API_KEY kamu:
    (dapatkan di: https://jina.ai)

USER: jina_xxxx

→ Hermes tulis JINA_API_KEY ke ~/.hermes/.env

🤖: Masukkan TELEGRAM_CHAT_ID kamu:
    (kirim pesan ke @userinfobot untuk dapat ID-mu)

USER: 123456789

→ Hermes tulis TELEGRAM_CHAT_ID ke ~/projects/sst-research-master/.env

🤖: ✅ Setup selesai. Lanjut buat project...
```

Setelah ini, **tidak pernah ditanya lagi** untuk project berikutnya.

Kontrak env yang dipakai:
- `~/.hermes/.env`: `TELEGRAM_BOT_TOKEN`, `JINA_API_KEY`
- project `.env`: `TELEGRAM_CHAT_ID` (boleh disalin dari master `.env`)

Ini adalah satu-satunya langkah yang perlu terminal. Setelah ini, segalanya via Telegram.

```bash
# 1. Clone master repo
mkdir -p ~/projects
git clone https://github.com/username/sst-research ~/projects/sst-research-master

# 2. Install skill ke Hermes
hermes skills install github.com/username/sst-research

# 3. Verifikasi skill terpasang
hermes skills list | grep sst-research

# 4. Setup DM Topic "Research" — tambahkan ke ~/.hermes/config.yaml:
```

```yaml
# ~/.hermes/config.yaml
platforms:
  telegram:
    extra:
      dm_topics:
        - chat_id: 123456789        # ganti dengan Telegram user ID kamu
          topics:
            - name: General
              icon_color: 7322096
            - name: Research
              icon_color: 16766590
              skill: sst-research   # auto-load setiap masuk topic Research
```

```bash
# 5. Restart gateway
hermes gateway restart

# Selesai. Semua selanjutnya via Telegram.
```

---

## Setup: Quick Commands (Optional, Zero Token)

Untuk command yang sering dipakai tanpa butuh AI sama sekali:

```yaml
# ~/.hermes/config.yaml
quick_commands:
  sst-queue:
    type: exec
    command: |
      P=$(cat ~/.hermes/sst_active_project 2>/dev/null || echo "none")
      echo "Queue: $P"
      echo "Pending: $(ls ~/projects/$P/queue/pending/ 2>/dev/null | wc -l | tr -d ' ')"
      echo "Done   : $(ls ~/projects/$P/queue/done/    2>/dev/null | wc -l | tr -d ' ')"
      echo "Dead   : $(ls ~/projects/$P/queue/dead/    2>/dev/null | wc -l | tr -d ' ')"
  sst-log:
    type: exec
    command: |
      P=$(cat ~/.hermes/sst_active_project 2>/dev/null)
      tail -20 ~/projects/$P/logs/worker_$(date +%Y%m%d).log 2>/dev/null || echo "Log tidak ada"
```

Ketik `/sst-queue` atau `/sst-log` di Telegram → langsung dapat output, zero token.

---

## Naming Convention Project

```
Format  : project-rx-{topik-singkat}
Rules   : lowercase, dash separator, prefix "project-rx-", no spasi, no underscore

✅ project-rx-ai-alignment
✅ project-rx-llm-survey-2026
✅ project-rx-climate-policy
✅ project-rx-biomedical-rag
❌ project-rx_ai_alignment   (underscore)
❌ project-rx ai alignment   (spasi)
❌ AI-Alignment              (no prefix, uppercase)
❌ sst-ai-alignment          (old prefix)
```

---

## Checklist Deploy

```
Terminal (SEKALI):
[ ] ~/projects/sst-research-master/ sudah di-clone
[ ] hermes skills list | grep sst-research → terpasang
[ ] ~/.hermes/config.yaml sudah ada dm_topics untuk Research
[ ] hermes gateway restart sudah dijalankan

Via Telegram (test):
[ ] Kirim /sst-rx-list → tidak ada error
[ ] Kirim /sst-rx-new project-rx-test → Hermes tanya JINA_API_KEY (cek ~/.hermes/.env)
[ ] Berikan key → Hermes tulis ke ~/.hermes/.env
[ ] Hermes tanya TELEGRAM_CHAT_ID → tulis ke master .env
[ ] Setup riset selesai → Hermes: "Jalankan /sst-rx-start untuk mulai worker"
[ ] Kirim /sst-rx-start → worker berjalan
[ ] bash run_research.sh status dari project test → tidak ada error
```
