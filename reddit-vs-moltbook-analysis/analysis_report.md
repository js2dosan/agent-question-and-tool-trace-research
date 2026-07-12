# Reddit Human Software Threads vs Moltbook Agent Questions

Generated: 2026-06-11

## Scope

This analysis compares three human Reddit software-build question sets against the available Moltbook agent-question classifications.

- Reddit video-editor thread: 67 classified questions
- Reddit CMS/webdev thread: 43 classified questions
- Reddit combined baseline: 110 classified questions
- Moltbook comparison set: 950 classified questions from rows 0-949
- Classifier: Gemini 2.5 Flash using the same taxonomy/subcategory prompt family

No additional model calls were used for this comparison step; it uses saved prediction outputs.

## Top-Level Results

| Label | Reddit Video | Reddit CMS | Reddit Combined | Moltbook |
|---|---:|---:|---:|---:|
| LLQ | 44 (65.7%) | 25 (58.1%) | 69 (62.7%) | 589 (62.0%) |
| DRQ | 16 (23.9%) | 16 (37.2%) | 32 (29.1%) | 220 (23.2%) |
| GDQ | 7 (10.4%) | 2 (4.7%) | 9 (8.2%) | 141 (14.8%) |

Combined Reddit vs Moltbook top-level chi-square: chi2=4.56, df=2, approximate p=0.1024. Treat this as a rough signal only because the datasets are different sizes and come from different platforms/contexts.

## Largest Subcategory Differences: Combined Reddit vs Moltbook

| Subcategory | Reddit Combined | Moltbook | Delta |
|---|---:|---:|---:|
| Disjunctive | 1 (0.9%) | 232 (24.4%) | -23.5 pp |
| Verification | 36 (32.7%) | 173 (18.2%) | +14.5 pp |
| Feature Specification | 18 (16.4%) | 48 (5.1%) | +11.3 pp |
| Rationale/Function/Goal Orientation | 12 (10.9%) | 16 (1.7%) | +9.2 pp |
| Instrumental/Procedural | 14 (12.7%) | 176 (18.5%) | -5.8 pp |
| Proposal/Negotiation | 7 (6.4%) | 92 (9.7%) | -3.3 pp |
| Expectational | 3 (2.7%) | 0 (0.0%) | +2.7 pp |
| Scenario Creation | 0 (0.0%) | 19 (2.0%) | -2.0 pp |
| Comparison | 0 (0.0%) | 15 (1.6%) | -1.6 pp |
| Causal Consequent | 0 (0.0%) | 14 (1.5%) | -1.5 pp |
| Ideation | 0 (0.0%) | 14 (1.5%) | -1.5 pp |
| Example | 0 (0.0%) | 13 (1.4%) | -1.4 pp |

## Main Insights

1. The two Reddit threads are not identical. The video-editor thread is mostly product/feature support: verification and feature specification dominate. The CMS thread is deeper and more architecture/security/rationale oriented, with a much higher DRQ share.

2. Combined Reddit remains mostly LLQ, but less GDQ-heavy than Moltbook. Reddit combined is LLQ 62.7%, DRQ 29.1%, GDQ 8.2%. Moltbook is LLQ 62.0%, DRQ 23.2%, GDQ 14.8%.

3. Reddit humans ask more verification questions. Combined Reddit verification is 32.7% versus Moltbook 18.2%. These are questions like whether a tool works, whether a feature exists, whether a site is active, or whether a specific implementation choice is present.

4. Moltbook has far more disjunctive questions. Moltbook disjunctive is 24.4% versus Reddit combined 0.9%. Agents in the Moltbook set more often frame questions around alternatives, tradeoffs, or option selection.

5. CMS Reddit looks closer to serious software-design review than the video-editor Reddit thread. CMS has DRQ 37.2% versus video-editor DRQ 23.9%. That fits the content: commenters were asking about security, database design, documentation, architecture, and design rationale.

6. Moltbook still looks more process/interrogation oriented. It has more Instrumental/Procedural and Proposal/Negotiation than the Reddit combined baseline. This supports the earlier qualitative read: Moltbook agents ask more about how systems should handle workflows, edge cases, and reusable capabilities.

## Classification Spot Check Examples

| Source | Question | Label | Subcategory | Why it fits |
|---|---|---|---|---|
| Reddit: Video Editor | Ok it looks like you just set things on top of each other, no "tracks"? | LLQ | Verification | Checks whether a feature, state, or condition is true. |
| Reddit: Video Editor | One mobile so can't test it out, do you have the ability to rotate video as well? | LLQ | Feature Specification | Asks whether a specific feature/capability exists or should exist. |
| Reddit: Video Editor | i just spent a good 4 hours editing a video and its not rendering can you help? | DRQ | Instrumental/Procedural | Asks how to carry out or handle a process/implementation detail. |
| Reddit: Video Editor | do you think it's possible to have the ability to play around and not export until sign up? | GDQ | Proposal/Negotiation | Suggests or negotiates a possible design/change. |
| Reddit: CMS | What made you decide to release it as open source rather than a commercial product? | DRQ | Rationale/Function/Goal Orientation | Asks for motivation, purpose, or design rationale. |
| Reddit: CMS | I like your logo, how did you make it? | DRQ | Instrumental/Procedural | Asks how to carry out or handle a process/implementation detail. |
| Reddit: CMS | EDIT: I see there is this functionality, but it seems only for textual columns? | LLQ | Verification | Checks whether a feature, state, or condition is true. |
| Moltbook first 950 | Do you have a single voice or do you vary tone/pacing for different story types? | LLQ | Disjunctive | Asks the respondent to choose between alternatives. |
| Moltbook first 950 | how do you handle when the linked articles are paywalled or return garbage HTML? | DRQ | Instrumental/Procedural | Asks how to carry out or handle a process/implementation detail. |
| Moltbook first 950 | Also, have you tried adding background lo-fi music for that "real podcast" vibe? | GDQ | Proposal/Negotiation | Suggests or negotiates a possible design/change. |

## Caveats

- Reddit text came from scraped visual text files, not native API JSON. The cleaner preserved the same broad extraction rules as the Moltbook workflow, but Reddit UI text can still introduce noise.
- The Reddit baseline has 110 questions total, while Moltbook has 950 in the current comparison set. Percentages are more useful than raw counts.
- The Moltbook full 12,193-question run is not complete in this comparison; this uses the completed first 950 rows.
- Some classifications are debatable at boundaries, especially short feature requests and conversational/rhetorical questions. The example sheet is included to make those judgments auditable.

## Files

- `reddit_moltbook_question_taxonomy_analysis.xlsx`: Excel workbook with dashboard, tables, examples, and charts.
- `all_classified_questions.csv`: combined row-level data.
- `dataset_summary.csv`, `top_level_distribution.csv`, `subcategory_distribution.csv`: auditable source tables.
