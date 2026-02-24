# SQL QA Engine — Day 4

A natural language to SQL pipeline powered by Gemini 2.5 Flash. Users ask questions in plain English and receive answers derived from CSV data — no SQL knowledge required.

---

## Overview

The SQL QA Engine bridges the gap between human language and structured data. Instead of requiring users to write SQL queries, they can ask questions naturally and the system handles everything — from understanding the question to returning a readable answer.

The pipeline is built around three core ideas:
- **Schema-aware generation** — the LLM sees the actual table structure before generating SQL
- **Safety-first execution** — only read queries are allowed to run
- **Plain-English answers** — raw results are summarized back into natural language

---

## Architecture

The pipeline follows a linear flow where each stage feeds into the next.

When a user submits a question, it is first combined with the database schema and sent to Gemini. The model uses the schema context to generate a syntactically correct SQL query tailored to the actual tables and columns available. This avoids hallucinated column names or wrong table references.

Before the query reaches the database, it passes through a safety validator. The validator checks the query against a blocklist of destructive or write operations. Any query attempting to modify, delete, or restructure data is rejected outright. Only retrieval operations are permitted.

If the query passes validation, it is executed against an in-memory SQLite database that was loaded from the user's CSV files at startup. The results are returned as a list of records.

Finally, the raw results are passed back to Gemini along with the original question. The model summarizes the findings into a concise, human-readable answer — including actual names and values from the data.

---

## Components

### Schema Loader
Responsible for ingesting CSV files and making their structure available to the rest of the pipeline. It reads all CSV files from the data directory, sanitises column names to be SQL-safe, and loads everything into an in-memory SQLite database. It also extracts the schema in a format suitable for the LLM prompt, including a small number of masked sample rows so the model understands what kind of data each column holds without exposing real values.

### SQL Generator
Takes the schema and the user's question and produces a valid SQL query. It communicates with Gemini 2.5 Flash using the configuration defined in the model config file. If execution fails, it can make a second attempt by asking the model to correct the broken query given the error message.

### Safety Validator
A lightweight layer that inspects the generated SQL before execution. It operates on a blocklist principle — any query that starts with or contains a write or destructive keyword is rejected. This ensures the in-memory database cannot be modified regardless of what the LLM generates.

### SQL Pipeline
The orchestrator that connects all components. It initialises the database, manages the generate → validate → execute → summarize flow, and handles the retry logic if the first generated query fails.

---

## Data Privacy

Sample rows shown to the LLM are masked before being included in the prompt. Each value has all characters after the first replaced with asterisks on a word-by-word basis. This means the model can understand the shape and format of the data without seeing real personal information.

---

## Configuration

The model provider and API key are defined in a single YAML config file. Switching models or providers requires only a change to this file — no code changes are needed anywhere in the pipeline.

The API key itself is never hardcoded. It is read from an environment variable whose name is specified in the config file, and loaded at runtime from a `.env` file.

---

## Limitations

- The free tier of the Gemini API allows 20 requests per day. Each question consumes two requests — one for SQL generation and one for summarization.
- The in-memory database is rebuilt from CSVs on every run. Any changes to the CSV files are automatically reflected on the next run.
- Only SQLite-compatible SQL is supported since the underlying database is SQLite.