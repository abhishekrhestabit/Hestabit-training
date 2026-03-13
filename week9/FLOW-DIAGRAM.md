# Flow Diagram: DAG-Based Execution (Day 2)

## The Multi-Agent Architecture
This system utilizes a **Directed Acyclic Graph (DAG)** via AutoGen's `SelectorGroupChat` and a custom state machine router to implement a Planner-Executor hierarchy. 

```text
                        [ USER QUERY ]
                              │
                              ▼
                      ┌───────────────┐
                      │    Planner    │ (Splits task into Tech & Biz)
                      └───────────────┘
                              │
                 (Simulated Parallel Fan-Out)
                 ┌────────────┴────────────┐
                 ▼                         ▼
        ┌────────────────┐        ┌────────────────┐
        │ Worker 1 (Tech)│        │ Worker 2 (Biz) │ 
        └────────────────┘        └────────────────┘
                 │                         │
                 └────────────┬────────────┘
                   (Join / Fan-In Execution)
                              ▼
                     ┌─────────────────┐
                     │ Reflection Agent│ (Synthesizes worker outputs)
                     └─────────────────┘
                              │
                              ▼
                      ┌───────────────┐
                      │ Validator     │ (Final logic & error check)
                      └───────────────┘
                              │
                              ▼
                       [ FINAL ANSWER ]