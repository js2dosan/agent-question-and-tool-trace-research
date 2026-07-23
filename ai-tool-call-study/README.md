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

## Tool-Routing Extension

[`extensions/tool_routing/`](extensions/tool_routing/) contains the next runnable experiment. It holds a deterministic CSV task constant, records whether the agent routes to Python through `run_command`, and scores the final JSON exactly. The experiment includes neutral, accuracy-focused, explanation-focused, and no-command control conditions.

The motivation is documented in [`analysis/tool_trace_quality_follow_up.md`](analysis/tool_trace_quality_follow_up.md): all five original pilot trials used the generic shell command for initial inspection, while only one executed a behavioral test.
