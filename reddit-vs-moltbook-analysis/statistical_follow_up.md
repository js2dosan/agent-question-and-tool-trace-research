# Statistical Follow-Up: How Strong Is the Top-Level Similarity?

## Question

The original comparison showed similar top-level question distributions for Reddit software discussions and Moltbook agent discussions. This follow-up asks a narrower question: how large is the observed difference across the three broad buckets?

## Observed distributions

| Source | Questions | LLQ | DRQ | GDQ |
| --- | ---: | ---: | ---: | ---: |
| Reddit combined | 110 | 69 (62.7%) | 32 (29.1%) | 9 (8.2%) |
| Moltbook completed set | 950 | 589 (62.0%) | 220 (23.2%) | 141 (14.8%) |

## Exploratory result

A 2 x 3 chi-square comparison of the observed counts gives:

| Statistic | Value |
| --- | ---: |
| Chi-square | 4.56 |
| Degrees of freedom | 2 |
| Approximate p-value | 0.102 |
| Cramer's V | 0.066 |

The observed association is small. With these samples, the three-bucket distributions are not clearly distinguishable at a conventional 0.05 threshold. That supports the careful wording used in the project: the distributions look similar at a broad level; it does **not** prove that humans and agents communicate or reason in the same way.

## Bucket-level differences

These normal-approximation intervals are descriptive and unadjusted. They are useful for judging scale, not for making three independent significance claims.

| Bucket | Reddit minus Moltbook | Approximate 95% interval in percentage points |
| --- | ---: | ---: |
| LLQ | +0.7 pp | -8.8 to +10.3 |
| DRQ | +5.9 pp | -3.0 to +14.8 |
| GDQ | -6.7 pp | -12.3 to -1.1 |

The LLQ estimate is nearly identical across the two samples. GDQ is lower in the Reddit sample, but the overall distribution test remains the more appropriate headline because the buckets are part of one composition and the samples are observational rather than randomly drawn.

## What this adds to the project

1. It quantifies the size of the difference, rather than relying only on matching percentages.
2. It sharpens the claim from “agents and humans are similar” to “the observed three-bucket mix is close in this limited comparison.”
3. It motivates the next study: replicate across more balanced software-discussion samples while preserving the same classifier and cleaning protocol.

## Limitations

- The Reddit and Moltbook samples differ in size, source platform, and discussion context.
- The Moltbook result uses the first 950 completed classifications, not the entire corpus.
- Classifier labels carry uncertainty, especially at fine-grained boundaries.
- This is an exploratory comparison, not a preregistered hypothesis test.
