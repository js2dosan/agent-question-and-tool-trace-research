# Tool-Trace Quality Follow-Up

## Why this follow-up matters

The original pilot correctly showed that prompt framing changed the number and sequence of tool calls. A closer read of the event-level trace adds a more specific insight: the same category name, `verification`, can represent very different levels of evidence.

## What the existing five trials show

| Observation | Evidence | Interpretation |
| --- | --- | --- |
| Generic command routing dominated initial inspection. | All 5/5 trials started with `run_command` using `ls -F`. | The agent chose a shell command despite having a dedicated `list_files` tool. Tool availability alone does not determine tool selection. |
| Dedicated inspection tools were unused. | 0/5 trials used `list_files`; 0/5 used `read_file`. | The tool interface should be studied as part of routing behavior, not treated as neutral infrastructure. |
| Most “verification” was structural rather than behavioral. | 3/5 trials used `ls -l` to confirm files existed. | File existence is weaker evidence than testing whether the app works. |
| Only one trial executed an actual behavioral test. | The verification-heavy trial created `test.js` and ran `node test.js`. | Prompt wording can shift verification from a superficial check to executable evidence. |
| Trace-aware did not guarantee stronger verification. | It split the app into `index.html` and `game.js`, then ran a file-existence check. | Modularity and verification are separate dimensions and should be measured separately. |

## Resulting analysis change

The trace analyzer now records verification strength for command-based checks:

- `structural` for file/content checks such as `ls -l`, `cat`, or `grep`.
- `behavioral` for executable checks such as `node test.js`, `pytest`, Playwright, or Vitest.

This is a methodological improvement, not a new model result. It makes the next batch capable of distinguishing “the file exists” from “the behavior was tested.”

## Research implication

The next extension should focus on **tool routing plus outcome quality**. The prepared `extensions/tool_routing/` experiment makes that connection testable by scoring an agent's output against a known correct answer while preserving its complete tool trace.
