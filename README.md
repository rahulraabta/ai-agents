# AI Agents — Daily Outreach Pipeline

[One sentence: what this system does and who it is for.]

![Pipeline diagram or sample output](docs/pipeline.png)

## Why this exists

[2–3 sentences. The problem: manual outreach is repetitive and hard to
personalise at scale. This project automates research, drafting, and
reply handling while keeping a human-reviewable log of every action.]

## What it does

- **Day Agent** — [what it researches or decides each day]
- **Outreach Agent** — [how it selects leads and drafts messages]
- **Reply Agent** — [how it classifies and responds to replies]
- **Output** — [what artifacts are written: leads database, drafts,
  reply logs, etc.]

## Quickstart

### Prerequisites
- Python 3.11+
- [API keys required: e.g., Google Gemini, SMTP credentials]

### Local run
```bash
git clone https://github.com/rahulraabta/ai-agents.git
cd ai-agents
pip install -r requirements.txt
cp .env.example .env   # add your keys
python -m src.main
