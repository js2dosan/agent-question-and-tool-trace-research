# Tool-Routing Extension

## Research question

When a coding agent can either inspect and reason manually from a small data file or use Python through a command tool, what predicts its tool choice and does that choice improve correctness?

This extension turns the broad question of “how does an agent know when to use a tool?” into a controlled, observable experiment. It does not infer private reasoning. It measures the visible routing decision: which tool was used, when it was used, what it produced, and whether the result was correct.

## Task

Each agent receives the same `transactions.csv` file and must produce a `report.json` with monthly totals, the largest expense, and the number of expenses. The file is small enough for manual calculation, but a Python command is an available alternative.

That creates an intentional choice point:

- Read the CSV and calculate manually.
- Use `run_command` to inspect or calculate with Python.
- Combine both, then verify the output.

The scorer checks the final JSON against an expected result. The expected result is not placed in the agent workspace.

## Conditions

Run each condition at least three times with the same model, temperature, task fixture, and maximum turns.

| Condition | What changes | Why |
| --- | --- | --- |
| Neutral | The task requests the report with no extra emphasis. | Baseline routing behavior. |
| Accuracy-focused | The task explicitly prioritizes exact arithmetic and validation. | Tests whether an accuracy goal increases command use or verification. |
| Explanation-focused | The task asks for a brief explanation of the method used. | Tests whether an accountability cue changes the visible workflow. |
| No-command control | Same neutral task, but `run_command` is removed. | Shows whether the task remains solvable without the command tool. |

## Measures

### Routing

- First tool used.
- Whether `run_command` was used.
- Whether the command appeared before the first write.
- Whether the agent used the dedicated `read_file` tool rather than a shell command for file inspection.

### Process

- Tool-call count and sequence.
- Number of writes and rewrites.
- Verification type: structural file check or behavioral/computational check.

### Outcome

- Valid JSON output.
- Exact numeric correctness.
- Required schema fields present.

## Commands

Run one trial with the command tool available:

```bash
uv run run-trial \
  --trial-id routing_neutral_01 \
  --prompt extensions/tool_routing/prompts/neutral.txt \
  --seed-dir extensions/tool_routing/fixture \
  --runs-dir runs/tool_routing

uv run python extensions/tool_routing/score_report.py \
  --report runs/tool_routing/routing_neutral_01/workspace/report.json
```

Run the availability-control condition:

```bash
uv run run-trial \
  --trial-id routing_no_command_01 \
  --prompt extensions/tool_routing/prompts/neutral.txt \
  --seed-dir extensions/tool_routing/fixture \
  --disable-run-command \
  --runs-dir runs/tool_routing
```

## Predictions to test, not results

- Accuracy-focused prompts may increase computational or verification actions.
- Removing `run_command` may preserve correctness for this small task but increase manual work or rework.
- Agents may prefer a generic shell command for file inspection even when a dedicated file-reading tool exists.

These are preregistered-style expectations. They should only be called findings after repeated runs are scored.
