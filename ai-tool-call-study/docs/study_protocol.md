# Study Protocol

## Question

How do different prompts change the tool-use behavior of an AI coding agent building the same three-player tic-tac-toe app?

## Controlled Variables

- Same model unless explicitly varied.
- Same tool set.
- Same empty workspace shape.
- Same maximum turn limit.
- Same logging schema.

## Prompt Conditions

1. Minimal task prompt.
2. Rules-heavy task prompt.
3. Design-heavy task prompt.
4. Verification-heavy task prompt.
5. Trace-aware careful-work prompt.

## Primary Measures

- Total model calls.
- Total tool calls.
- Tool sequence.
- File read count.
- File write count.
- Command/test count.
- Whether the agent verifies behavior.
- Whether the agent performs design/styling iteration.

## Trace Interpretation

Tool calls are treated as observable action traces:

- `list_files` and `read_file`: orientation/context gathering.
- `write_file`: implementation or repair.
- `run_command`: execution, build, testing, or inspection.
- `finish`: finalization.

The model text and function-call choice are treated as language-level proxies for planning and decision behavior.
