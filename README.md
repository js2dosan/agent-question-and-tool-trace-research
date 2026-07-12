# Agent Question and Tool-Trace Research

This repository collects two connected studies of observable AI behavior:

1. **Question taxonomy analysis** compares questions in Reddit software-build discussions with questions in Moltbook agent discussions.
2. **Tool-call trace study** holds a coding task constant and tests how prompt wording changes an agent's observable workflow.

The shared premise is deliberately modest: hidden reasoning is not directly observable, but questions, tool calls, files, commands, tests, and final outputs are useful behavioral traces.

## Main result

Using the same Eris taxonomy and Gemini 2.5 Flash classification workflow, the high-level question distributions were similar across the completed samples:

| Source | Questions | LLQ | DRQ | GDQ |
| --- | ---: | ---: | ---: | ---: |
| Reddit software discussions | 110 | 62.7% | 29.1% | 8.2% |
| Moltbook agent discussions | 950 | 62.0% | 23.2% | 14.8% |

The taxonomy is applied at the fine-grained subcategory level first, then rolled up into the three top-level buckets. The top-level comparison is the primary result; subcategories are retained as diagnostic detail.

## Repository map

| Folder | Contents |
| --- | --- |
| [`question-taxonomy-pipeline/`](question-taxonomy-pipeline/) | Reproducible Python classification pipeline, configs, prompts, tests, and cleaned Reddit question sets. |
| [`reddit-vs-moltbook-analysis/`](reddit-vs-moltbook-analysis/) | Final report, source tables, Excel dashboard, chart preview, and classification examples. |
| [`ai-tool-call-study/`](ai-tool-call-study/) | Controlled Gemini coding-agent harness, prompt conditions, study protocol, and categorized pilot analysis. |
| [`presentation/`](presentation/) | Research handoff and the final four-slide lightning-talk assets. |
| [`docs/`](docs/) | Scope, limitations, attribution, and publication notes. |

## Reproduce the studies

### Question taxonomy pipeline

```bash
cd question-taxonomy-pipeline
uv sync
cp .env.example .env
# Add a provider key to .env
uv run python main.py --experiment configs/reddit_browser_video_editor_experiment.yaml
```

### Tool-call study

```bash
cd ai-tool-call-study
uv sync
export GEMINI_API_KEY="your key here"
uv run run-trial --trial-id trial_01_minimal --prompt prompts/trial_01_minimal.txt
uv run analyze-tool-calls --runs-dir runs --out-dir analysis
```

## Important limitations

- This is an observational research prototype, not a claim that question labels reveal hidden chain-of-thought.
- The Reddit baseline has 110 questions and the Moltbook sample has 950; compare percentages, not raw counts.
- The tool-call findings are a small pilot with one task and one model.
- The Reddit inputs were cleaned from scraped visible text, so some UI-text noise remains possible.

## Attribution and license

The question-taxonomy pipeline is adapted from [ahmedshahriar/llm-eval-question-taxonomy-verbal-design-protocols](https://github.com/ahmedshahriar/llm-eval-question-taxonomy-verbal-design-protocols), released under the Apache License 2.0. The retained license appears in [`question-taxonomy-pipeline/LICENSE`](question-taxonomy-pipeline/LICENSE). Research datasets, analysis, the tool-call harness, and presentation materials were assembled for this study.

See [`docs/PROJECT_SCOPE.md`](docs/PROJECT_SCOPE.md) before publishing the repository.
