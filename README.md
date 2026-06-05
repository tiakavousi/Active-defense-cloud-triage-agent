# Cloud Triage

Containerized full-stack app that ingests simulated cloud network logs, learns per-user baselines of normal activity, and deploys a LangGraph multi-agent investigator (Ollama-backed) to triage anomalies autonomously.

## Stack

- **FastAPI** — ingest, baseline computation, anomaly scoring, agent tool endpoints
- **Streamlit** — live feed, incidents, baselines dashboard
- **LangGraph + LangChain** — supervisor / identity-analyst / network-analyst agents
- **Ollama** — local LLM (`qwen2.5:7b-instruct` by default)
- **Postgres** — log + baseline + incident store
- **Docker Compose** — orchestration

## Services

| Service | Port | Role |
|---|---|---|
| `db` | 5432 | Postgres |
| `ollama` | 11434 | Local LLM inference |
| `api` | 8000 | FastAPI ingest + tool endpoints |
| `log_generator` | — | Streams synthetic cloud logs |
| `agent` | — | LangGraph investigator (polls API) |
| `ui` | 8501 | Streamlit dashboard |

## Quick start

```bash
cp .env.example .env
docker compose up --build
```

First boot pulls the Ollama model (~4GB) — give it a few minutes. Open <http://localhost:8501>.

## Data flow

1. `log_generator` emits events for ~25 synthetic users with per-user behavioral profiles, mixing in anomalies (impossible travel, off-hours privilege escalation, data exfil spikes).
2. `api` ingests events into Postgres, periodically refreshes baselines, and scores each event statistically (z-score on bytes, set-membership on geo/IP/UA, time-of-day likelihood).
3. Events above `ANOMALY_FLAG_THRESHOLD` become **pending incidents**.
4. `agent` polls for pending incidents and runs a LangGraph workflow: supervisor delegates to identity- and network-analyst sub-agents, who call API tool endpoints, then a reporter synthesizes findings.
5. `ui` shows the live feed, incidents with full reasoning trace, and per-user baselines.

## Layout

```
db/init.sql              Postgres schema
services/log_generator/  Streaming synthetic-log emitter
services/api/            FastAPI: ingest, baselines, scoring, tools
services/agent/          LangGraph multi-agent investigator
services/ui/             Streamlit dashboard
```
