# 🎭 The Muppet Show — Multi-Agent Demo

A multi-agent AI demo built on [Google ADK](https://google.github.io/adk-docs/) and deployed to [Vertex AI Agent Engine](https://cloud.google.com/vertex-ai/generative-ai/docs/agent-engine/overview). Seven Muppet characters run as independent LLM agents that genuinely communicate with each other — and Statler & Waldorf occasionally try to smuggle prompt injections past [Google Cloud Model Armor](https://cloud.google.com/security/products/model-armor).

---

## What it does

Type a command and watch the cast react:

| Command | What happens |
|---|---|
| `joke [topic]` | Fozzie performs a terrible pun. Statler, Waldorf and Kermit each listen to the shared session history and react in turn. A surprise guest may appear. |
| `heckle [topic]` | An LLM orchestrator drives Statler and Waldorf through two rounds of back-and-forth via AgentTool calls, then Kermit tries to restore order. |

Topics: `cybersecurity` · `AI` · `cloud computing` · `kermit` · `miss piggy` · `gonzo`

---

## Agents

| Agent | Role |
|---|---|
| Fozzie | Tells one terrible pun per show |
| Statler | Heckles from the balcony — occasionally attempts a prompt injection |
| Waldorf | One-ups Statler — occasionally attempts a prompt injection |
| Kermit | Exasperated host trying to keep order |
| Scooter | Surprise guest — bursts on with urgent backstage news |
| Gonzo | Surprise guest — announces a bizarre dangerous act |
| Miss Piggy | Surprise guest — sweeps in and makes everything about her |
| Kermit (alert) | Interrupts as on-call responder when Model Armor fires |

---

## Architecture

### v1 — Python string-passing (`muppets_agent_v1/`)
Each agent is called sequentially by Python code. Fozzie's joke is passed as a string to Statler, Statler's reply is passed to Waldorf, and so on. Simple and reliable.

### v2 — Genuine multi-agent (`muppets_agent_v2/`)
Agents communicate through ADK primitives:

- **Joke flow** — `SequentialAgent`: Fozzie, Statler, Waldorf and Kermit share a session. Each agent reads the full conversation history and reacts to what it "hears" rather than being handed strings by Python.
- **Heckle flow** — `AgentTool` orchestration: an LLM orchestrator drives five sequential tool calls (Statler → Waldorf → Statler → Waldorf → Kermit). The LLM decides the content of each call based on the previous response.
- **Surprise guests** — `AgentTool` with a host LLM that decides ~60% of the time whether to call Scooter, Gonzo or Miss Piggy.
- **Model Armor** — every Statler and Waldorf line is checked against a Model Armor template. Statler and Waldorf are instructed to occasionally smuggle prompt injection attempts into their heckling. When a line is blocked, Kermit's comms device buzzes and he interrupts as the on-call alert responder.

```
joke AI
  └─ SequentialAgent
       ├─ Fozzie      → tells joke (shared session)
       ├─ Statler     → reads session, reacts → Model Armor check
       ├─ Waldorf     → reads session, reacts → Model Armor check
       │                  └─ if blocked → Kermit alert agent interrupts
       └─ Kermit      → reads full session, despairs
            └─ SurpriseGuestHost (AgentTool) → maybe calls Scooter/Gonzo/Miss Piggy
```

---

## Project structure

```
muppets_agent_v1/       # Agent Engine package — v1
  agent.py
  requirements.txt

muppets_agent_v2/       # Agent Engine package — v2 (active)
  agent.py
  requirements.txt

muppets_chat_v1.py      # Local interactive runner for v1
muppets_chat_v2.py      # Local interactive runner for v2
statler_waldorf.py      # Original two-agent experiment
```

---

## Running locally

### Prerequisites
- Python 3.11+
- `google-adk` installed (`pip install google-adk`)
- A Gemini API key **or** Google Cloud project with Vertex AI enabled

### With Gemini API (direct)
```bash
export GEMINI_API_KEY=your_key_here
python3 muppets_chat_v2.py
```

> **Note:** The free tier allows 20 requests/day for `gemini-2.5-flash`. A full `heckle` run makes ~10 requests. Use Vertex AI for sustained testing.

### With Vertex AI
```bash
export GOOGLE_GENAI_USE_VERTEXAI=TRUE
export GOOGLE_CLOUD_PROJECT=your-project-id
export GOOGLE_CLOUD_LOCATION=europe-west2
python3 muppets_chat_v2.py
```

---

## Model Armor setup

Model Armor checks require a template in your GCP project. Create one in the [Model Armor console](https://console.cloud.google.com/security/model-armor) named `my-first-template` in `europe-west2`, with at minimum the **Prompt injection & jailbreak** filter enabled.

The agent calls `sanitizeUserPrompt` on every Statler/Waldorf line. When blocked, `pi_and_jailbreak` (or another filter name) appears in the output alongside Kermit's intervention.

---

## Deploying to Agent Engine

```bash
# From the repo root
adk deploy agent_engine muppets_agent_v2
```

Requires a `.env` file in `muppets_agent_v2/` (not committed):
```
GOOGLE_GENAI_USE_VERTEXAI=TRUE
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=europe-west2
```

The Agent Engine service account must have:
- `roles/aiplatform.user`
- `roles/modelarmor.user` (for Model Armor calls)

---

## Tech stack

- [Google ADK](https://google.github.io/adk-docs/) — `LlmAgent`, `SequentialAgent`, `AgentTool`, `BaseAgent`
- [Vertex AI Agent Engine](https://cloud.google.com/vertex-ai/generative-ai/docs/agent-engine/overview) — managed deployment
- [Google Cloud Model Armor](https://cloud.google.com/security/products/model-armor) — prompt sanitization
- `gemini-2.5-flash` — all agents
