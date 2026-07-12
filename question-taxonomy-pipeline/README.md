# Question Taxonomy Pipeline

This folder contains the reproducible classification code used in the Reddit versus Moltbook comparison. It assigns a fine-grained Eris taxonomy subcategory to each question and rolls that classification up to `LLQ`, `DRQ`, or `GDQ`.

Included research inputs are the two clean Reddit software-discussion question sets. The completed combined analysis is in [`../reddit-vs-moltbook-analysis/`](../reddit-vs-moltbook-analysis/).

Run the pipeline with:

```bash
uv sync
cp .env.example .env
uv run python main.py --experiment configs/reddit_browser_video_editor_experiment.yaml
```

This is a modified research copy of the original [LLM Evaluation: Question Taxonomy Classification](https://github.com/ahmedshahriar/llm-eval-question-taxonomy-verbal-design-protocols) project. Apache License 2.0 terms are retained in [`LICENSE`](LICENSE).
