# Model benchmark

*Bonus work, after the timebox. Run on 5 November 2026 with
`manage.py benchmark_models`. The raw results, including every judge verdict and its
reason, are in [benchmark-results.json](benchmark-results.json), and there is a
[one-page PDF summary](benchmark-summary.pdf).*

I generated the same two assessments with Claude Opus 5.5 (the default), Sonnet 5.5
and Haiku 5.5, each at two reasoning efforts: `medium`, the deployment's default, and
`xhigh` (extra high). That makes six configurations, with two runs each on both
assessments: 24 reports. Every report went through the normal queue and worker, with
the same prompts and output schema, and records the model and effort it was
generated with.

- **Pacific Coast** (Default Insurer): a COPE survey in English from 3 photos and 2
  notes. The evidence is thin, so several of the 22 questions should end as
  "insufficient evidence".
- **Udine** (Customer A): a COPE survey in Italian from the 4-page survey PDF and 3
  photos. The PDF ends with the engineer's five numbered recommendations, which serve
  as an answer key.

Two Opus 5.5 judges score the reports:

- **Recall** (Udine): each of the expert's five recommendations is covered, partial
  or missed.
- **Support** (both assessments): for each rated or multiple-choice answer, do the
  quotes it cites justify that option over the others? The verdicts are supported;
  partial (consistent with it, but not ruling out a neighbouring option);
  unsupported; or photos only, which the judge can't see.

## Results

Times and costs are the mean of two runs. The other columns are totals over both runs
and both assessments, except "Answered", which is Pacific Coast's mean.

| Model | Effort | Pacific Coast | Udine | Answered (of 22) | Quotes verified | Expert recs (Udine) | Rated answers supported | Unsupported | Rejected and retried |
|---|---|---|---|---|---|---|---|---|---|
| Opus 5.5 | medium | 107 s · $0.26 | 169 s · $0.47 | 12 | 244 / 244 | 5 / 5 | 10 / 22 | 1 | 0 |
| Opus 5.5 | xhigh | 220 s · $0.52 | 484 s · $1.31 | 12.5 | 386 / 386 | 5 / 5 | 9 / 24 | 3 | 0 |
| Sonnet 5.5 | medium | 52 s · $0.10 | 87 s · $0.19 | 10 | 171 / 171 | 5 / 5 | 6 / 21 | 0 | 1 |
| Sonnet 5.5 | xhigh | 135 s · $0.22 | 274 s · $0.50 | 11 | 262 / 262 | 5 / 5 | 8 / 22 | 1 | 0 |
| Haiku 5.5 | medium | 58 s · $0.010 | 118 s · $0.017 | 10 | 152 / 152 | 4.75 / 5 | 5 / 24 | 4 | 2 |
| Haiku 5.5 | xhigh | 214 s · $0.026 | 372 s · $0.051 | 10.5 | 231 / 231 | 5 / 5 | 7 / 23 | 3 | 0 |

The `medium` reports and their judging cost $2.23 in the first run. The `xhigh`
reports, plus the support check on all 24 reports, cost $6.13. Smoke tests added
about $0.20.

## What it shows

**Between models, at `medium`:**

- **The mechanics hold for every model.** All 1,446 quotes across the 24 reports were
  found verbatim in the evidence, and every Udine report covered the expert's
  recommendations. Haiku's one 4.5 out of 5 is judge noise: the same report scored 5
  out of 5 in an earlier pass.
- **Cost spans almost 30 times.** Haiku costs under 4% of what Opus does, and Sonnet
  about 40%. At these prices the model isn't the expensive part of a survey; the
  engineer's review is.
- **Opus finds more, and its ratings are the best supported.** On Pacific Coast it
  answered 12 questions against 10. Ten of its 22 rated answers were fully supported,
  against 6 of 21 for Sonnet and 5 of 24 for Haiku.
- **Haiku overreaches.** In all three of its Pacific Coast runs at `medium` (the two
  here, plus a smoke test), Haiku rated sprinkler coverage "Partial". Its quote was
  about corrosion and says nothing about coverage. Its four unsupported ratings
  include "no combustible insulation", drawn from a recommendation to use
  non-combustible insulation, and an "Extra high" occupancy hazard drawn from a quote
  about sprinkler control. **A verified quote proves the evidence exists, not that it
  supports the answer.**
- **Smaller models slip on the format, and the server catches it.** Sonnet and Haiku
  sometimes answered a choice question with an explanation instead of one of the
  options, and Haiku once translated an option into Italian ("Moderato" for
  "Moderate"). The server rejected each one and the queue retried it. Opus had none.

**Between efforts, `xhigh` against `medium`:**

- **It costs 2 to 3 times more and takes 2 to 4 times longer, for every model.** Opus
  at `xhigh` needed 8 minutes and $1.31 for the Udine report.
- **It removes the format slips.** There were no rejected answers in 12 `xhigh` runs,
  against 3 in 12 at `medium`.
- **It cites more evidence.** On Udine there were 55 to 75% more quotes, all
  verified, and slightly more recommendations.
- **It doesn't make the ratings better supported overall.** Sonnet and Haiku improve
  a little (29% to 36%, and 21% to 30% supported), but Opus doesn't (45% to 38%).
  Unsupported ratings rise from 5 to 7 in total. The sprinkler question cuts both
  ways: at `xhigh` Haiku declined in two of its three runs, but Opus rated coverage
  "Full" in one of two runs, where at `medium` it had declined both times.

**In the template:**

- **The most frequent unsupported rating comes from the question, not the model.**
  Every model, at both efforts, rated Udine's *external exposure* (from neighbouring
  properties) with quotes about earthquakes and floods, which a separate question
  covers. The evidence says nothing about neighbours, so the honest answer is
  "insufficient evidence". Sharper guidance on that question is the fix, and the
  support check is what found it.

## Recommendation

- **Keep Opus 5.5 at `medium` as the default for reports that will be issued.** Its
  ratings are the best supported, at a fraction of the cost and time of `xhigh`.
- **Don't raise effort by default.** `xhigh` doubles or triples cost and latency
  without better-supported answers here. Its one clear gain, no format slips from
  Sonnet and Haiku, is cheaper to get from Opus at `medium`. Sonnet at `xhigh` costs
  about the same as that, takes longer and is less well supported.
- **Offer Sonnet 5.5 at `medium` to cost-sensitive customers and for drafts.** Keep
  Haiku 5.5 for previews and triage.
- **Fix the template, and check support in the product.** Tighten the "external
  exposure" guidance. Then consider running the support check on rated answers
  before an engineer reviews a report, to flag the ones the quotes don't justify.
- Each report now records its effort, so effort can be offered per organization or
  per model if a customer needs it.

## Limits of this benchmark

- Two runs per configuration, so the results show a direction, not statistical
  proof. Differences of one to three rated answers are within noise.
- The judges are noisy too: the same Haiku report scored 5 out of 5 recall in one
  pass and 4.5 in another. The support judge is also strict, with "partial" its most
  common verdict everywhere, so compare its numbers rather than reading them as
  absolutes.
- The answer key is part of the evidence, so recall measures completeness and barely
  separates the models. The next version should hold the advice pages out of the
  evidence, then score whether a model reaches the expert's recommendations from the
  observations alone.
- The judges are Opus, and a human should calibrate them before their scores drive
  decisions.
- A second run can read the first run's prompt cache, so costs vary between runs.

## Reproduce it

It costs about $8.50 and takes about an hour with two workers:

```bash
docker compose up -d --scale worker=2
docker compose exec backend python manage.py benchmark_models --efforts medium xhigh --support-check \
  --out /app/benchmark-results.json
```
