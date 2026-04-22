# Pipeline 4 — Memory System

## Tujuan
Menyimpan **konteks dan state riset** agar agent tidak perlu membaca ulang seluruh vault 
setiap saat. Memory bukan duplikasi dari hasil riset — melainkan catatan harian agent 
tentang apa yang sedang berjalan, apa yang sudah ada, dan apa yang dipelajari selama 
proses riset.

> **Perbedaan mendasar dengan Pipeline 2 Synthesis:**
> - **Synthesis** = buku laporan hasil penelitian — apa yang ditemukan dari konten sumber
> - **Memory** = catatan harian peneliti — state, pointer, dan lessons learned selama riset

---

## Siapa Mengerjakan Apa

| Simbol | Aktor | Peran |
|---|---|---|
| 🤖 | AI CLI (`ccs`) | Summarize memory saat dipanggil manual atau per stage selesai |
| 🐍 | Python | Append raw notes otomatis per task, baca & tulis file memory |

---

## Struktur Memory

```
vault/
└── memory/
    ├── working.md     ← state task yang sedang/sudah berjalan
    ├── research.md    ← peta topik yang sudah ada + gap yang belum terjawab
    └── meta.md        ← lessons learned, error patterns, preferensi
```

**Aturan kepemilikan:**
- Hanya Memory System yang boleh **menulis** ke `vault/memory/`
- Pipeline lain hanya boleh **membaca** dari `vault/memory/`
- Tidak ada pipeline lain yang boleh overwrite folder ini

---

## Mengapa Memory Membuat Riset Lebih Efektif

Tanpa memory, agent buta konteks setiap kali dipanggil. Ini yang terjadi:

| Masalah Tanpa Memory | Solusi dengan Memory |
|---|---|
| Query generik, banyak hasil tidak relevan | `research.md` → query targeted ke gap spesifik |
| Error yang sama berulang (timeout, sumber buruk) | `meta.md` → error patterns dicatat & dihindari |
| Tidak tahu kapan berhenti fetch | `research.md` → status per pertanyaan: ANSWERED / OPEN |
| Gap tersebar di ratusan file extracted | `research.md` → semua gap diagregasi di satu tempat |
| Synthesizer tidak tahu konteks sebelumnya | `research.md` → di-inject ke prompt synthesizer |

---

## Self-Improving Loop

Inilah nilai utama memory — sistem ini bisa **memperbaiki dirinya sendiri** dalam satu project:

```
Gap ditemukan di research.md
       ↓
Pipeline 3 baca research.md saat generate queries
       ↓
Query baru yang lebih targeted masuk ke queue/pending/
       ↓
Fetch → Extract → Synthesis → gap baru ditemukan atau gap lama tertutup
       ↓
research.md diperbarui
       ↓
Loop lagi sampai semua pertanyaan riset berstatus ANSWERED
```

**Contoh nyata:**

```
Putaran 1:
→ Query: "RLHF reinforcement learning"
→ Fetch 142 sumber → Extract → Synthesis
→ Gap terdeteksi: "RLHF pada model >100B params belum ada"
→ research.md diperbarui

Putaran 2 (user jalankan /sst-rx-start lagi atau queue diisi ulang):
→ Query: "RLHF large language models 100B scale" ← jauh lebih spesifik
→ Fetch sumber yang tepat → gap tertutup
→ Pertanyaan riset Q1 berubah dari PARTIALLY ANSWERED → ANSWERED
```

**Ini membuat setiap putaran riset lebih presisi dari putaran sebelumnya.**

---

### 1. `working.md` — State & Progress
Catatan raw per task yang selesai. Di-append otomatis oleh Python worker, 
**tanpa memanggil AI**. Murah dan cepat.

**Format entry:**
```markdown
## Session: 2026-04-21

### [14:32] FETCH ✓
- Title: "Attention Is All You Need"
- Source: arxiv | Credibility: 0.91
- URL: http://arxiv.org/abs/1706.03762v5
- Durasi: 23s

### [14:35] FETCH ✗ (retry 1/2)
- Title: "Scaling Laws for Neural Language Models"
- Error: Jina timeout
- URL: https://arxiv.org/abs/2001.08361

### [15:10] EXTRACT ✓
- Title: "Attention Is All You Need"
- Key entities: Transformer, Multi-head attention, WMT 2014
- Gaps ditemukan: 2

### [16:00] STAGE SELESAI: FETCH
- Berhasil: 142 | Gagal: 3 | Dead: 1
- Durasi total: 1j 28m
```

---

### 2. `research.md` — Peta Riset
Pointer ke synthesis yang sudah ada dan gap yang belum terjawab. 
Di-update oleh AI CLI **sekali per stage Extract selesai**.

**Bukan rangkuman konten** — tapi peta navigasi yang bilang "sudah ada di mana, 
kurang apa."

**Format:**
```markdown
## Research Map
**Project:** AI Alignment
**Last updated:** 2026-04-21 16:00
**Pertanyaan Riset:**
1. Apa metode alignment yang paling efektif saat ini? → [PARTIALLY ANSWERED]
2. Bagaimana RLHF dibandingkan Constitutional AI? → [OPEN]

---

## Topik yang Sudah Ada di Vault

### RLHF
- Synthesis: `vault/synthesis/rlhf.md`
- Jumlah sumber: 23
- Coverage: high
- Gap: belum ada sumber yang membahas RLHF pada model >100B params

### Constitutional AI
- Synthesis: `vault/synthesis/constitutional-ai.md`
- Jumlah sumber: 11
- Coverage: medium
- Gap: perbandingan empiris dengan RLHF masih kurang

### AI Safety (General)
- Synthesis: belum ada — masih dalam proses extract
- Jumlah sumber terekstrak: 7/34
- Coverage: in progress

---

## Gap Terbuka (Kandidat Riset Lanjutan)
- [ ] RLHF pada model skala >100B — belum ada sumber yang cover
- [ ] Perbandingan empiris RLHF vs Constitutional AI — 3 sumber menyebut tapi tidak detail
- [ ] Dataset benchmark untuk alignment evaluation — disebutkan di 5 paper tapi tidak dikaji

---

## Pertanyaan yang Sudah Terjawab
- (belum ada)
```

---

### 3. `meta.md` — Lessons Learned
Di-update oleh AI CLI **satu kali saat project selesai**. Berisi pola error, 
hal yang berjalan baik, dan catatan untuk project riset berikutnya.

**Format:**
```markdown
## Meta Memory
**Project:** AI Alignment
**Selesai:** 2026-04-21 20:15

---

## Yang Berjalan Baik
- Query "RLHF reinforcement learning human feedback" sangat produktif (relevance avg: 0.84)
- arXiv kategori cs.AI memberikan hasil lebih relevan dibanding cs.LG untuk topik ini
- Jina Reader dengan X-Engine: readerlm-v2 lebih baik untuk paper PDF

## Error Patterns
- Jina timeout sering terjadi pada URL dari researchgate.net — hindari di project berikutnya
- AI CLI sering gagal parse JSON jika konten terlalu panjang (>6000 karakter) — batasi lebih ketat
- arXiv rate limit terkena 3x — tambah delay menjadi 1 detik untuk project berikutnya

## Preferensi yang Terdeteksi
- User prefer synthesis per topik sebelum final report
- User tidak perlu notif per task untuk stage Synthesize — terlalu berisik

## Saran untuk Project Berikutnya
- Mulai dengan query yang lebih spesifik — query umum banyak menghasilkan dead task
- Tambah PubMed sebagai plugin jika topik ada irisan dengan neuroscience
```

---

## Update Triggers & Alur

```
Per task selesai
    ↓
🐍 worker() selesai
    ↓
🐍 append_working_memory(task)     ← zero AI, hanya tulis teks ke working.md


Per stage selesai
    ↓
🐍 notify_stage_done()
    ↓
🤖 AI CLI summarize extracted/     ← satu kali panggilan AI per stage
    ↓
🐍 update_research_map()           ← tulis hasil ke research.md


Project selesai
    ↓
🐍 notify_all_done()
    ↓
🤖 AI CLI analyze patterns         ← satu kali panggilan AI di akhir project
    ↓
🐍 write_meta_memory()             ← tulis hasil ke meta.md
```

**Kalkulasi token:**
- Per task → **0 token**
- Per stage Extract selesai (batch) → **1x panggilan AI per batch**
- Project selesai → **1x panggilan AI**
- Total bergantung jumlah batch stage Extract + 1 panggilan final meta, tetap jauh lebih hemat daripada update per task

---

## Implementasi

### memory.py

```python
# 🐍 Python — semua operasi file memory

from pathlib import Path
from datetime import datetime, timezone

MEMORY_DIR = Path("vault/memory")
WORKING_MD = MEMORY_DIR / "working.md"
RESEARCH_MD = MEMORY_DIR / "research.md"
META_MD = MEMORY_DIR / "meta.md"


def init_memory(project_topic: str):
    """
    🐍 Inisialisasi folder dan file memory di awal project.
    Dipanggil satu kali setelah research_config.yaml dibuat.
    """
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)

    if not WORKING_MD.exists():
        WORKING_MD.write_text(
            f"# Working Memory\n**Project:** {project_topic}\n\n", 
            encoding="utf-8"
        )

    if not RESEARCH_MD.exists():
        RESEARCH_MD.write_text(
            f"# Research Map\n**Project:** {project_topic}\n"
            f"**Last updated:** {_now()}\n\n"
            "## Topik yang Sudah Ada di Vault\n\n"
            "## Gap Terbuka\n\n"
            "## Pertanyaan yang Sudah Terjawab\n",
            encoding="utf-8"
        )

    if not META_MD.exists():
        META_MD.write_text(
            f"# Meta Memory\n**Project:** {project_topic}\n\n",
            encoding="utf-8"
        )


def append_working_memory(task: dict, status: str):
    """
    🐍 Append raw note ke working.md setiap task selesai atau gagal.
    Zero AI — hanya tulis teks.
    """
    duration = _calculate_duration(task)
    icon = "✓" if status == "done" else "✗"
    error_line = f"\n- Error: {task.get('error', '')}" if status != "done" else ""

    entry = (
        f"\n### [{_now_time()}] {task['stage'].upper()} {icon}\n"
        f"- Title: \"{task['title'][:80]}\"\n"
        f"- Source: {task['source_type']} | "
        f"Credibility: {task.get('relevance_score', 'n/a')}\n"
        f"- URL: {task['url']}"
        f"{error_line}\n"
        f"- Durasi: {duration}s\n"
    )

    with WORKING_MD.open("a", encoding="utf-8") as f:
        # Tambahkan header tanggal jika belum ada untuk hari ini
        today_header = f"\n## Session: {datetime.now().strftime('%Y-%m-%d')}\n"
        content = WORKING_MD.read_text(encoding="utf-8")
        if today_header.strip() not in content:
            f.write(today_header)
        f.write(entry)


def append_stage_summary(stage: str, stats: dict):
    """
    🐍 Append summary stage ke working.md.
    Dipanggil setelah semua task satu stage selesai.
    """
    entry = (
        f"\n### [STAGE SELESAI: {stage.upper()}]\n"
        f"- Berhasil: {stats['done']} | "
        f"Gagal: {stats['failed']} | "
        f"Dead: {stats['dead']}\n"
        f"- Durasi total: {stats['duration']}\n"
    )

    with WORKING_MD.open("a", encoding="utf-8") as f:
        f.write(entry)
```

---

### Prompt: Update Research Map (🤖 AI CLI)

Dipanggil **satu kali setelah stage Extract selesai**.

```python
RESEARCH_MAP_PROMPT = """
Kamu adalah research coordinator. Tugasmu memperbarui peta riset berdasarkan 
dokumen yang sudah diekstraksi.

PERTANYAAN RISET:
{research_questions}

DOKUMEN TEREKSTRAKSI (ringkasan):
{extracted_summaries}

PETA RISET SAAT INI:
{current_research_map}

Perbarui peta riset dan kembalikan HANYA JSON berikut, tanpa preamble:
{{
  "topics": [
    {{
      "name": "nama topik",
      "synthesis_path": "vault/synthesis/{slug}.md atau null jika belum ada",
      "source_count": 0,
      "coverage": "high | medium | low | in_progress",
      "gaps": ["gap spesifik yang ditemukan"]
    }}
  ],
  "open_gaps": ["gap lintas topik yang belum terjawab"],
  "answered_questions": ["pertanyaan riset yang sudah terjawab (jika ada)"],
  "partially_answered": ["pertanyaan yang sebagian terjawab"]
}}
""".strip()
```

```python
def update_research_map(config: dict):
    """
    🤖 AI CLI + 🐍 Python
    Panggil AI CLI untuk update research.md berdasarkan vault/extracted/.
    Dipanggil satu kali setelah stage Extract selesai.
    """
    from llm_client import call_llm
    from utils import parse_json_response

    # Kumpulkan ringkasan semua extracted docs
    extracted_summaries = _collect_extracted_summaries()
    current_map = RESEARCH_MD.read_text(encoding="utf-8")

    prompt = RESEARCH_MAP_PROMPT.format(
        research_questions="\n".join(config["project"]["research_questions"]),
        extracted_summaries=extracted_summaries[:10000],
        current_research_map=current_map[:3000],
    )

    raw = call_llm(prompt)
    result = parse_json_response(raw)

    if result:
        _write_research_map(result, config)
        print("[MEMORY] ✓ research.md diperbarui")
    else:
        print("[MEMORY] ⚠ Gagal update research.md")


def _collect_extracted_summaries() -> str:
    """🐍 Kumpulkan section Summary dari semua file di vault/extracted/."""
    import re
    summaries = []
    for f in Path("vault/extracted").glob("*.md"):
        content = f.read_text(encoding="utf-8")
        match = re.search(r"## Summary\n(.*?)(?=\n## |\Z)", content, re.DOTALL)
        if match:
            summaries.append(f"### {f.stem}\n{match.group(1).strip()}")
    return "\n\n".join(summaries)
```

---

### Prompt: Update Meta Memory (🤖 AI CLI)

Dipanggil **satu kali saat project selesai**.

```python
META_PROMPT = """
Kamu adalah research advisor. Tugasmu menganalisis pola dari seluruh proses riset 
yang baru selesai untuk menghasilkan catatan yang berguna di project berikutnya.

WORKING MEMORY (log seluruh proses):
{working_memory}

DEAD TASKS (task yang gagal permanent):
{dead_tasks}

RESEARCH CONFIG:
{research_config}

Kembalikan HANYA JSON berikut, tanpa preamble:
{{
  "yang_berjalan_baik": ["hal yang efektif selama riset"],
  "error_patterns": ["pola error yang berulang dan cara menghindarinya"],
  "preferensi_terdeteksi": ["preferensi user yang terdeteksi dari interaksi"],
  "saran_project_berikutnya": ["rekomendasi konkret untuk riset serupa"]
}}
""".strip()
```

---

## Kapan Memory Dibaca

Memory dibaca oleh agent dalam dua kondisi:

**1. Saat user tanya via Telegram:**
```
User: /sst-rx-memory
🤖: [baca working.md + research.md → kirim ringkasan ke Telegram]

User: /sst-rx-memory-gaps  
🤖: [baca research.md → tampilkan Open Gaps saja]

User: /sst-rx-memory-status
🤖: [baca working.md → tampilkan progress terkini]

User: /sst-rx-memory-summarize
🤖: [panggil AI CLI → kompres & rapikan semua memory]
```

**2. Saat stage baru dimulai:**
```
Stage Synthesis dimulai
→ 🐍 baca research.md 
→ inject ke prompt synthesizer sebagai konteks
→ "Topik yang sudah ada: X, Y. Gap yang perlu dijawab: Z"
```

---

## Telegram Commands untuk Memory

| Command | Aksi | Siapa |
|---|---|---|
| `/sst-rx-memory` | Ringkasan working + research map | 🤖 Hermes Agent baca memory/ |
| `/sst-rx-memory-status` | Progress task terkini dari working.md | 🤖 Hermes Agent |
| `/sst-rx-memory-gaps` | Daftar gap terbuka dari research.md | 🤖 Hermes Agent |
| `/sst-rx-memory-summarize` | AI CLI kompres & rapikan semua memory | 🤖 AI CLI (`ccs`) |

> **Catatan:** `/sst-rx-memory-summarize` adalah satu-satunya command yang memanggil AI CLI. 
> Semua command lain hanya membaca file — zero token.

---

## Integrasi dengan Pipeline Lain

### Pipeline 1 → Memory
```python
# Di pipeline.py Pipeline 1, setelah dokumen disimpan ke vault/sources/:
from memory import append_working_memory
append_working_memory(task, status="done")   # 🐍 zero AI
```

### Pipeline 2 → Memory
```python
# Di synthesizer.py Pipeline 2, setelah stage Extract selesai:
from memory import update_research_map
update_research_map(config)                  # 🤖 AI CLI — satu kali per stage
```

### Pipeline 3 → Memory
```python
# Di worker() Pipeline 3, setelah setiap task:
from memory import append_working_memory
append_working_memory(task, status)          # 🐍 zero AI

# Di sliding_window_runner() saat project selesai:
from memory import write_meta_memory
write_meta_memory(config)                    # 🤖 AI CLI — satu kali di akhir
```

---

## Vault Structure (Final — Semua Pipeline)

```
vault/
├── _index.md                            # katalog untuk manusia (rebuild tiap jam)
├── _topics/
│   └── {topic-slug}.md                  # metadata per topik
├── sources/                             # Pipeline 1 — konten mentah bersih
│   └── {YYYY-MM-DD}--{slug}.md
├── extracted/                           # Pipeline 2 Stage 1 — klaim terstruktur
│   └── {YYYY-MM-DD}--{slug}.md
├── synthesis/                           # Pipeline 2 Stage 2 — sintesis per topik
│   └── {topic-slug}.md
├── output/                              # Pipeline 2 Stage 3 — laporan final
│   └── final-report.md
└── memory/                              # Pipeline 4 — memory system
    ├── working.md                       # state & progress (append otomatis)
    ├── research.md                      # peta riset & gap (update per stage)
    └── meta.md                          # lessons learned (update saat selesai)
```

---

## Config (config.yaml — Bagian Pipeline 4)

```yaml
memory:
  enabled: true
  auto_append_per_task: true        # zero AI, selalu aktif
  auto_update_research_map: true    # AI CLI, sekali per stage Extract selesai
  auto_write_meta: true             # AI CLI, sekali saat project selesai
  max_working_size_kb: 500          # kalau lebih dari ini, auto-compress working.md
```

---

## Catatan Penting

- **Memory bukan duplikasi synthesis** — synthesis berisi konten riset, memory berisi state & navigasi
- **Zero AI untuk append** — Python langsung tulis teks, tidak perlu LLM
- **AI hanya dipanggil 4x maksimal** untuk seluruh memory system berapapun jumlah task
- **`vault/memory/` adalah territory eksklusif** Pipeline 4 — pipeline lain hanya boleh membaca
- **Memory dibaca saat stage baru dimulai** — di-inject ke prompt synthesizer sebagai konteks tambahan
- **Semua Telegram command memory** kecuali `/sst-rx-memory-summarize` adalah zero token
