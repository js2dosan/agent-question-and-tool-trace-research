# AI Tool-Call Study

This is a controlled study harness for logging how a Gemini coding agent uses tools while completing the same task under different prompt conditions.

The five conditions vary prompt framing: minimal, rules-heavy, design-heavy, verification-heavy, and trace-aware. The study protocol and pilot findings are in [`docs/study_protocol.md`](docs/study_protocol.md) and [`analysis/pilot_report.md`](analysis/pilot_report.md).

```bash
uv sync
export GEMINI_API_KEY="your key here"
uv run run-trial --trial-id trial_01_minimal --prompt prompts/trial_01_minimal.txt
uv run analyze-tool-calls --runs-dir runs --out-dir analysis
```

Generated runs are intentionally ignored. The checked-in analysis contains aggregate results from the completed pilot.
