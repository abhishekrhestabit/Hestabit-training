# Day 1 — Agent Fundamentals: Multi-Agent Round-Robin Chat

## Overview

Day 1 introduces the core concepts of AI agents and implements a simple multi-agent conversation system using Microsoft AutoGen's `RoundRobinGroupChat`. Three role-isolated agents collaborate in a fixed turn order to answer user queries.

## Architecture

```
User Query
    │
    ▼
┌──────────────────────┐
│   RoundRobinGroupChat │  (max 4 messages, buffered context of 10)
│                        │
│  ┌─────────────────┐  │
│  │ Research Agent   │──┼──▶ Gathers raw information on the topic
│  └─────────────────┘  │
│          │             │
│          ▼             │
│  ┌─────────────────┐  │
│  │ Summarizer Agent │──┼──▶ Condenses research into key points
│  └─────────────────┘  │
│          │             │
│          ▼             │
│  ┌─────────────────┐  │
│  │ Answer Agent     │──┼──▶ Formulates the final user-facing answer
│  └─────────────────┘  │
└──────────────────────┘
    │
    ▼
 Final Answer (printed to CLI)
```

## Agent Roles

| Agent | Role | Constraint |
|---|---|---|
| Research Agent | Gather raw information | Must not summarize or answer directly |
| Summarizer Agent | Condense research into key points | Must not do new research or answer |
| Answer Agent | Produce final user-facing answer | Must not research or summarize — only compose |

## Key Concepts

### 1. Agent vs. Chatbot vs. Pipeline

- **Chatbot:** Stateless, reactive — takes a prompt and predicts the next word.
- **Pipeline:** Deterministic, hardcoded sequence (Step A → B → C). Breaks on edge cases.
- **Agent:** Autonomous entity with an LLM reasoning engine. Perceives, decides, acts, evaluates.

### 2. The Perception → Reasoning → Action Loop

1. **Perception:** Ingest context (user queries, agent outputs, system state).
2. **Reasoning:** Analyze context against system prompt and current goal.
3. **Action:** Execute the decision (generate text, call a tool, delegate).

### 3. Role Isolation via System Prompts

Each agent has a tightly scoped system prompt that defines what it *is*, *must do*, and *must never do*. This prevents a single "God Agent" from confusing its context and hallucinating.

### 4. Message Protocol

Agents communicate via a shared rolling chat history (`BufferedChatCompletionContext` with buffer_size=10). The state of the application is the message history itself.

## File Structure

```
Day1/
├── day1.py                        ← Entry point, RoundRobinGroupChat setup
├── agents/
│   ├── research_agent.py          ← Research Agent
│   ├── summarizer_agent.py        ← Summarizer Agent
│   └── answer_agent.py            ← Answer Agent
├── config/
│   ├── __init__.py
│   ├── model_client.py
│   ├── gemini_client.py
│   └── models.yaml
└── AGENT-FUNDAMENTALS.md
```

## Usage

```bash
python day1.py
# Interactive loop — type a question, get a researched + summarized answer
```

