# Term Research Summary

## The project in one sentence

I studied whether visible question patterns and tool-call traces can help us describe how AI agents work, without claiming access to their private reasoning.

## Why I chose this

When an AI agent receives a prompt, it may inspect files, choose a tool, write code, run a command, test an implementation, or stop. Those choices look like reasoning, but the internal process is not directly observable. I wanted a concrete, defensible way to study the behavior we can actually see.

## What I built

### Question-taxonomy analysis

I used the Eris question taxonomy to classify questions from two kinds of software discussion:

- Human questions in public Reddit software-build comment sections.
- Agent questions in the Moltbook discussion sample.

Each question was first assigned a fine-grained subcategory, then rolled up to one of three broad buckets: LLQ, DRQ, or GDQ. This made the final comparison easier to interpret while preserving detailed labels for audit.

### Tool-call trace study

I built a local Gemini coding-agent harness that logs model messages, tool calls, tool outputs, files written, commands executed, and final results. I held the task constant, building a three-player tic-tac-toe game, and changed only the prompt framing.

## What I found

The combined Reddit baseline had 110 questions. The completed Moltbook comparison set had 950 questions.

| Source | LLQ | DRQ | GDQ |
| --- | ---: | ---: | ---: |
| Reddit | 62.7% | 29.1% | 8.2% |
| Moltbook | 62.0% | 23.2% | 14.8% |

The main result is that the high-level bucket mix was similar. Both datasets were mostly LLQ. The subcategories differed more, especially for Reddit verification questions and Moltbook questions about alternatives.

In the tool-call pilot, prompt wording changed what the agent visibly did. A verification-heavy prompt caused the agent to create and run a test file. A trace-aware prompt produced a more modular two-file implementation. The final artifact alone would not have captured those differences.

## What I learned

- Observable traces can support useful research questions, but they are not hidden chain-of-thought.
- Data cleaning and transparent examples matter as much as model output for a credible comparison.
- Aggregated categories can be more dependable for claims than fine-grained labels.
- Controlled prompts, fixed tasks, and structured logs make agent behavior easier to compare.

## Why it matters

This approach can support future work on agent evaluation, prompt design, tool-use debugging, and human-agent collaboration. Instead of asking only whether an agent completed a task, we can also ask how it behaved while completing it.

## Where I would take it next

1. Add larger, balanced discussion samples and human label review.
2. Repeat tool-call trials across several models and tasks.
3. Enable browser-based inspection to measure deeper verification behavior.
4. Test whether question-type patterns are associated with tool-use patterns.

## Evidence in this repository

- [`../reddit-vs-moltbook-analysis/analysis_report.md`](../reddit-vs-moltbook-analysis/analysis_report.md)
- [`../ai-tool-call-study/analysis/pilot_report.md`](../ai-tool-call-study/analysis/pilot_report.md)
- [`../question-taxonomy-pipeline/`](../question-taxonomy-pipeline/)
