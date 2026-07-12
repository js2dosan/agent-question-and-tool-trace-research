# Project Scope and Publication Notes

## What is included

- The modified, reproducible question-classification pipeline with configs, prompts, and tests.
- Cleaned Reddit question datasets used for the completed comparison.
- The final Reddit versus Moltbook report, tables, example classifications, Excel workbook, and dashboard preview.
- The AI tool-call study source code, prompt conditions, protocol, and aggregated analysis artifacts.
- The current research handoff and four presentation slide images.

## What is intentionally excluded

- API keys, `.env` files, virtual environments, package caches, and local editor state.
- Raw model batches, full uncurated output folders, logs, and model event runs.
- The full raw Moltbook question dataset. The public repo retains aggregate comparison outputs instead.
- Intermediate slide thumbnails and unrelated projects, including Cortex OS.

## Data and interpretation boundaries

The Reddit question sets came from scraped comment text and were cleaned before classification. They should be treated as research samples, not canonical Reddit API archives. The Moltbook comparison covers the first 950 completed classifications, not the full source corpus.

The tool-call study records observable system behavior such as reads, writes, commands, test execution, and generated files. It does not expose or claim access to a model's hidden reasoning.

## Recommended GitHub description

> Observable AI behavior research using question-taxonomy analysis and coding-agent tool-call traces.

## Recommended repository topics

`llm-evaluation`, `ai-agents`, `tool-calling`, `prompt-engineering`, `research`, `gemini`, `python`
