# Pilot Report: Prompt Effects on Gemini Tool Use

## Research Framing

This pilot treats tool calls as observable action traces in a Thought-Action-Observation style loop. The model's hidden reasoning is not directly visible, but the sequence of tool calls, tool arguments, tool outputs, generated files, and final summaries provides a behavioral trace of how the agent approached the task.

Task held constant: build a three-player tic-tac-toe web game.

Model held constant: `gemini-3.1-flash-lite`.

## Prompt Conditions

- `trial_01_minimal`: Create a playable three-player tic-tac-toe web game.
- `trial_02_rules_heavy`: Create a three-player tic-tac-toe web game with clear win detection, turn order, invalid move prevention, reset, and score tracking.
- `trial_03_design_heavy`: Create a polished three-player tic-tac-toe web game with strong visual design, clear player identities, animations, and responsive layout.
- `trial_04_verification_heavy`: Create a three-player tic-tac-toe web game and thoroughly test the game logic and UI before finishing.
- `trial_05_trace_aware`: Create a three-player tic-tac-toe web game. Work carefully, inspect files before editing, verify behavior with tests or browser checks, and explain final design decisions.

## Tool-Call Category Summary

| Trial | Model Calls | Tool Calls | Orientation | Implementation | Verification | Finalization | Created Files |
|---|---:|---:|---:|---:|---:|---:|---|
| trial_01_minimal | 4 | 4 | 1 | 1 | 1 | 1 | index.html |
| trial_02_rules_heavy | 3 | 3 | 1 | 1 | 0 | 1 | index.html |
| trial_03_design_heavy | 4 | 4 | 1 | 1 | 1 | 1 | index.html |
| trial_04_verification_heavy | 5 | 5 | 1 | 2 | 1 | 1 | index.html;test.js |
| trial_05_trace_aware | 5 | 5 | 1 | 2 | 1 | 1 | game.js;index.html |

## Early Findings

1. All five prompts produced completed artifacts, but prompt framing changed the trace shape.
2. The verification-heavy prompt produced the strongest verification behavior: it created `test.js` and ran `node test.js` before finalizing.
3. The trace-aware prompt produced a more modular implementation by splitting the game into `index.html` and `game.js`.
4. The design-heavy prompt produced the largest single HTML artifact among the non-test runs, suggesting more styling/UI code.
5. The minimal and rules-heavy prompts completed with fewer structural side effects and mostly single-file implementations.

## Interpretation

The pilot suggests that prompt wording can shift agent behavior from simple implementation toward verification or modularization. The most visible distinction is not only in the final app, but in the intermediate tool trace: whether the model creates test artifacts, runs commands, or separates implementation files.

## Limitations

- This is a small pilot with one model and one task.
- The harness captures observable behavior, not hidden chain-of-thought.
- UI verification is still shallow; the current agent can run commands but does not yet perform browser screenshots or interaction checks.
- The category labels are rule-based and should be manually audited before being used as final research data.

## Suggested Next Step

Run a second batch with browser/screenshot tools enabled, then compare whether design-heavy prompts trigger more visual inspection and iterative styling changes.

## Event-Level Data

See `tool_call_events_categorized.csv` for every categorized tool call.
