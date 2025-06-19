

## 0 · Vision

> *Ship a self-contained, yet deeply configurable tool that fetches, parses (text + figures), summarises, rates, and delivers weekly ArXiv digests in PDF/HTML — runnable either in Docker or a lightweight virtual-env, with a friendly setup wizard that writes a YAML config.*

---

## 1 · Repository Layout

```
arxiv-autosumm/
├─ autosumm/                 ← importable package
│  ├─ __init__.py
│  ├─ cli.py                 ← Typer entry-points (init/run)
│  ├─ ui/                    ← Textual or Streamlit wizard
│  ├─ config.py              ← pydantic dataclass ↔︎ YAML helpers
│  ├─ pipeline/
│  │   ├─ fetch.py
│  │   ├─ parse/
│  │   │   ├─ text.py
│  │   │   └─ figures.py
│  │   ├─ summarise.py
│  │   ├─ rate.py
│  │   ├─ cache.py
│  │   ├─ render.py
│  │   └─ deliver.py
│  └─ utils/
├─ prompts/                  ← default prompt templates
├─ scripts/                  ← helper scripts (install-texlive, cron stub)
├─ docker/
│  ├─ Dockerfile
│  └─ entrypoint.sh
├─ tests/
├─ pyproject.toml            ← poetry
├─ requirements.txt          ← slim fallback
└─ README.md
```

---

## 2 · Configuration Schema (`config.yaml`)

```yaml
runtime:
  mode: docker          # docker | venv
  texlive_root: null    # only used in venv mode
  docker_mount_cache: ~/.cache/arxiv-autosumm
  docker_mount_output: ~/arxiv_summaries
  ollama_mode: host     # host | embedded

run:
  schedule: "0 3 * * 1"          # cron syntax
  autostart: true                # wizard adds Cron/systemd entry if true
  categories: ["cs.CL"]
  max_results: 8
  workload_soft_limit: true

summariser:
  provider: aliyun
  model: deepseek-r1
  batch: true
  system_prompt_file: null
  user_prompt_file: null

rater:
  strategy: embed_rerank         # llm | embed_rerank | hybrid
  model: qwen3-rerank
  prompt_file: null
  top_k: 200

embedder:
  model: qwen3-embed
  instruction: "Represent the scientific abstract for retrieval:"

parser:
  figures:
    enabled: true
    caption_model: SciCap-6B
  ocr_engine: pytesseract

cache:
  dir: ~/.cache/arxiv-autosumm
  ttl_days: 14
  store_pdf: false

output:
  dir: ~/arxiv_summaries
  formats: [pdf, html]

email:
  smtp_server: smtp.gmail.com
  port: 465
  sender: me@gmail.com
  recipient: you@uni.edu
```

---

## 3 · Setup Wizard (GUI) — **6 + 1 Sections**

| #     | Section                   | Exposed Fields                                                                                                                                                            |
| ----- | ------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **1** | **Environment**           | • Runtime mode (docker/venv)• If **docker**: host paths for **/cache** & **/output** (default pre-filled) • If **venv**: detect TeX — else file-picker for `texlive_root` |
| **2** | **LLM**                   | Provider, model, API key, **prompt file pickers** (system/user/rater)                                                                                                     |
| **3** | **Categories & Schedule** | Multi-select arXiv cats, cron widget, **“Add to startup items?”** toggle (writes `run.autostart`)                                                                         |
| **4** | **Weekly Budget**         | `max_results`, token budget slider, workload soft-limit checkbox                                                                                                          |
| **5** | **Output**                | Formats (PDF/HTML), output dir picker                                                                                                                                     |
| **6** | **Parsing Extras**        | Enable figure OCR, caption model dropdown, OCR engine picker                                                                                                              |

The wizard writes/updates `config.yaml` and (if `autostart: true`) offers to install:

- **Cron job** (`crontab -e`) in venv mode, or

- **systemd user service** that executes `docker run ...` on login.

---

## 4 · Functional Modules

| Module               | Core Responsibilities                                                       |
| -------------------- | --------------------------------------------------------------------------- |
| **fetch.py**         | Async + cached paper & PDF/HTML download.                                   |
| **parse/text.py**    | arxiv2text → fallback to ar5iv HTML.                                        |
| **parse/figures.py** | YOLO-v8 region detection → SciCap caption → inject `![caption]()` markdown. |
| **summarise.py**     | Wrapper for OpenAI/Ollama batch & stream modes.                             |
| **rate.py**          | Strategy pattern (LLM, embed_rerank, hybrid).                               |
| **cache.py**         | SQLite index, TTL eviction, disk storage.                                   |
| **render.py**        | md → pdf/html (Pandoc / markdown-it-py).                                    |
| **deliver.py**       | Email, Slack, WeChat (SMTP abstraction).                                    |

---

## 5 · Execution Flow

```
cli.run(config) -> fetch -> (cache) -> rate -> summarize -> render -> deliver
```

---

## 6 · Risk & Mitigation

| Risk                          | Mitigation                                                                 |
| ----------------------------- | -------------------------------------------------------------------------- |
| TeXLive bulk in Docker        | Use `texlive-small` plus on-demand `tlmgr`.                                |
| Figure OCR latency            | Cache caption results in sqlite; allow user to disable.                    |
| Ollama host networking quirks | Document `host.docker.internal` for Windows/macOS + fallback IP for Linux. |
| Cron/systemd portability      | Provide shell snippets; run health-check on first startup.                 |


