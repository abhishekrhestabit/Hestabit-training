# Day 2 — Multi-Agent Orchestration: Flow Diagram

## Architecture Overview

```
User Query
    │
    ▼
┌─────────────────────┐
│   Planner_Agent     │  → Breaks query into N numbered sub-tasks
└─────────────────────┘
    │
    ▼ (N sub-tasks dispatched in parallel)
┌──────────┐  ┌──────────┐  ┌──────────┐
│ Worker_1 │  │ Worker_2 │  │ Worker_N │  → Each handles ONE sub-task
│ task 1   │  │ task 2   │  │ task N   │
└──────────┘  └──────────┘  └──────────┘
    │               │              │
    └───────────────┴──────────────┘
                    │
                    ▼ (all outputs merged)
        ┌──────────────────────┐
        │   Reflection_Agent   │  → Synthesizes, fills gaps, improves
        └──────────────────────┘
                    │
                    ▼
          ┌──────────────────────────────┐
          │       Validator_Agent        │
          │  1. Validate                 │
          │  2. Self-correct if needed   │
          │  3. Output final answer      │
          └──────────────────────────────┘
                    │
                    ▼
            Plain Text Final Answer
             (printed to CLI)
```

## Agent Roles

| Agent | Role | Input | Output |
|---|---|---|---|
| Planner_Agent | Decompose query into sub-tasks | User query | Numbered task list |
| Worker_Agent_N | Execute one sub-task | Single task | Detailed raw output |
| Reflection_Agent | Synthesize + fill gaps | All worker outputs | Enriched synthesis |
| Validator_Agent | Validate + self-correct + answer | Reflection output | Clean plain text final answer |

## Key Design Decisions

- Parallel workers: All worker agents run concurrently via asyncio.gather() — no sequential bottleneck.
- Strict role isolation: Each agent has a tightly scoped system prompt. Workers only execute, reflection only synthesizes.
- Self-healing validation: Validator does not just flag errors — it fixes them itself and always produces a final answer.
- No separate answer agent: Validator is the last agent in the chain and directly outputs the final answer.
- CLI-friendly output: Final answer is always plain text with no markdown, ready for terminal display.
- Live progress: Each pipeline step prints real-time status to the terminal. No intermediate content is shown.

## Pipeline Execution Flow

```
[1/4] Planner        → creates N tasks
[2/4] Workers x N    → run in parallel, each prints when done
[3/4] Reflection     → merges and improves all worker outputs
[4/4] Validator      → validates, self-corrects, prints final answer
```

## File Structure

```
├── main.py 
├── dag.py                       ← Entry point, full pipeline (Day 2)
├── orchestrator/
│   └── planner.py                 ← Planner_Agent
├── agents/
│   ├── worker_agent.py            ← Worker_Agent (parameterized by ID)
│   ├── reflection_agent.py        ← Reflection_Agent
│   ├── validator.py               ← Validator_Agent (also final answer generator)
│   ├── research_agent.py          ← (Day 1)
│   ├── summarizer_agent.py        ← (Day 1)
│   └── answer_agent.py            ← (Day 1)
└── FLOW-DIAGRAM.md
```