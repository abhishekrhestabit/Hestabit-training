# AGENT-FUNDAMENTALS.md

## 1. What is an AI Agent? (Agent vs. Chatbot vs. Pipeline)

To build autonomous systems, we must fundamentally shift how we view LLMs:

* **Chatbot:** A stateless, reactive interface. It takes a prompt and predicts the most statistically likely next word. It has no autonomy, memory, or goal-oriented behavior beyond the immediate reply.
* **Pipeline:** A deterministic, hardcoded sequence of operations (e.g., Step A $\rightarrow$ Step B $\rightarrow$ Step C). Pipelines are rigid; if an edge case occurs that the developer didn't account for, the pipeline breaks.
* **Agent:** An autonomous entity driven by an LLM that acts as a reasoning engine. It maintains a state machine and pursues goals by perceiving its environment, deciding on an action, executing it, and evaluating the result.
from autogen_agentchat.teams import DiGraphBuilder, GraphFlow

## 2. The Perception $\rightarrow$ Reasoning $\rightarrow$ Action Loop

Agents operate on a continuous cognitive loop, allowing them to adapt to dynamic situations rather than following a rigid script:

1. **Perception:** The agent ingests context (user queries, system logs, database errors, or outputs from other agents).
2. **Reasoning:** The agent analyzes the context against its systemic prompt and current goal, deciding on the best path forward.
3. **Action:** The agent executes the decision (e.g., writing code, calling an API, querying a database, or replying to the user).

## 3. The ReAct Pattern (Reason + Act)

The ReAct pattern is the architectural standard for preventing LLM hallucinations during autonomous execution. It forces the LLM to expose its internal monologue *before* it takes an action.

* **Thought:** The agent explicitly states its logic ("I need to find the latest data on X to answer the user").
* **Action:** The agent defines the tool and parameters it will use ("Calling `WebSearch` with query 'X'").
* **Observation:** The agent ingests the result of the tool and loops back to **Thought** to determine if the task is complete.

## 4. Message Protocol Systems

In multi-agent architectures (like AutoGen), agents do not pass variables like standard Python functions. Instead, they communicate via **Message Protocols**—appending their outputs to a shared, rolling chat history.

* **State Passing:** The state of the application is the chat history itself.
* **Context Windows:** Because LLMs have strict token limits, message protocols must employ rolling memory buffers (e.g., keeping only the last 10 messages) or compression agents to prevent Out-Of-Memory (OOM) crashes.

## 5. Role Isolation & System Prompts

The foundation of a stable multi-agent system is **Role Isolation**, enforced entirely through strict **System Prompts**.

* **The Problem:** Giving a single "God Agent" too many tools or instructions causes it to confuse its context, misuse tools, and hallucinate.
* **The Solution:** Divide massive tasks into micro-agents (e.g., a `Researcher`, a `Summarizer`, and an `Answerer`).
* **System Prompts:** The prompt is the agent's OS. A strong agentic prompt explicitly states what the agent *is*, what it *must do*, and crucially, what it *must never do* (e.g., "You are a Summarizer. Do not answer the user's query directly. Do not perform new research.").

## 6. The LLM as a Tool Executor

In an agentic framework, the LLM stops being a simple text generator and becomes a routing engine. By defining tools (functions) in the agent's configuration, the LLM can output structured JSON indicating which function to run and with what arguments, bridging the gap between natural language reasoning and deterministic code execution.

