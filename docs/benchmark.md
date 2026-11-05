# Model benchmark

*Bonus work, after the timebox. Run on 5 November 2026 with
`manage.py benchmark_models`. The raw results, including the judge's reasoning, are in
[benchmark-results.json](benchmark-results.json).*

I generated the same two assessments with Claude Opus 5.5 (the default), Sonnet 5.5
and Haiku 5.5, twice each. Every run went through the normal queue and worker, with
the same prompts, output schema and effort (`medium`).

- **Pacific Coast** (Default Insurer): a COPE survey in English from 3 photos and 2
  notes. The evidence is thin, so several questions should end as "insufficient
  evidence".
- **Udine** (Customer A): a COPE survey in Italian from the 4-page survey PDF and 3
  photos. The PDF ends with the engineer's five numbered recommendations. They serve
  as the answer key: an Opus judge marks each one as covered, partial or missed.

## Results

Mean of two runs. Quotes are totals over both runs.

| Assessment | Model | Time | Cost | Answered (of 22) | Quotes verified | Recommendations | Expert recommendations covered |
|---|---|---|---|---|---|---|---|
| Pacific Coast | Opus 5.5 | 107 s | $0.257 | 12 | 74 / 74 | 4 | n/a |
| Pacific Coast | Sonnet 5.5 | 52 s | $0.102 | 10 | 57 / 57 | 4 | n/a |
| Pacific Coast | Haiku 5.5 | 58 s | $0.010 | 10 | 46 / 46 | 4 | n/a |
| Udine | Opus 5.5 | 169 s | $0.469 | 20 | 170 / 170 | 9.5 | 5 / 5 |
| Udine | Sonnet 5.5 | 87 s | $0.193 | 19.5 | 114 / 114 | 8.5 | 5 / 5 |
| Udine | Haiku 5.5 | 118 s | $0.017 | 20 | 106 / 106 | 8.5 | 5 / 5 |

The 12 reports and 6 judge calls cost $2.23 in total, and all 12 runs completed.

## What it shows

- **The mechanics hold for every model.** All 567 quotes were found verbatim in the
  evidence, and every Udine report carried all five of the expert's recommendations.
- **Cost spans almost 30 times.** Haiku costs under 4% of what Opus does, and Sonnet
  about 40%. At these prices the model isn't the expensive part of a survey; the
  engineer's review is.
- **Opus finds more in thin evidence.** On Pacific Coast it answered 12 questions
  against 10, and cited 37 quotes per report against 28 (Sonnet) and 23 (Haiku).
  Opus answered construction class, hazardous materials and sprinkler adequacy in both
  of its runs, each with verified quotes. Sonnet answered the first two once in two
  runs and never the third, and Haiku answered them at most once.
- **Haiku overreaches where it matters.** In all three of its Pacific Coast runs (the
  two here, plus a smoke test), Haiku rated sprinkler coverage "Partial". It cited
  "Sprinkler system present but showing signs of corrosion", a real quote that says
  nothing about coverage. In all four of their runs, Opus and Sonnet answered
  "insufficient evidence" and asked for the sprinkler layout. **A verified quote
  proves the evidence exists, not that it supports the answer.**
- **Smaller models slip on the format, and the server catches it.** The server's
  checks rejected three answers, which were then retried:
  - Sonnet and Haiku each answered a choice question with an explanation instead of
    one of the options.
  - Haiku once translated an option into Italian ("Moderato" for "Moderate").

  Opus had none. Each retry is a billed call, now recorded in the cost ledger
  (errata 2).
- **Haiku isn't the fastest.** It produced the most output (14k to 27k tokens per
  report, against 10k to 18k for Opus and 6k to 11k for Sonnet), so it ran slower
  than Sonnet. Sonnet was fastest.
- **A warm cache makes a second report 14 to 24% cheaper.** Opus's second runs read
  the prefix its first runs had cached (it lasts 5 minutes): $0.276 to $0.238 on
  Pacific Coast, and $0.532 to $0.405 on Udine.

## Recommendation

- **Keep Opus 5.5 as the default for reports that will be issued.** It answered the
  most with cited evidence, declined when it should, and needed no retries. Its extra
  cost over Sonnet, $0.15 to $0.30 a report, is small next to an engineer's review
  time.
- **Offer Sonnet 5.5 to cost-sensitive customers and for drafts.** It is 2.4 times
  cheaper and twice as fast, with the same recall and slightly fewer findings.
  Organizations can already allow it per customer (`ai_models` in their YAML).
- **Keep Haiku 5.5 for previews, triage and high-volume internal work,** not for
  issued reports without a careful review: its "answered" doesn't always mean
  "supported".

## Limits of this benchmark

- Two runs per model and assessment: the results show a direction, not statistical
  proof.
- The answer key is part of the evidence, so the recall test measures completeness,
  and every model scored 5 out of 5. It doesn't separate them. The next version should
  hold the advice pages out of the evidence, then score whether a model reaches the
  expert's recommendations from the observations alone.
- The judge is Opus. With every model at 5 out of 5, no bias shows here, but a human
  should calibrate the judge before its scores drive decisions.
- "Answered more" isn't automatically better. I checked the sprinkler-coverage answers
  by hand, not every difference. The systematic fix is a second check that the quoted
  evidence supports each rated or classified answer, plus spot checks by engineers.
- A second run can read the first run's prompt cache, so costs vary between runs.

## Reproduce it

It costs about $2.50 and takes about 15 minutes with two workers:

```bash
docker compose up -d --scale worker=2
docker compose exec backend python manage.py benchmark_models --out /app/benchmark-results.json
```
