# Errata

Issues found after the timebox ended (tag `timebox-end`). After closing, I asked a
second Claude instance to review the code independently. I checked each of its six main findings against the code: all six were
real. Each is fixed in its own commit, tagged `(BONUS)`, with a regression test that
fails without the fix. The history up to `timebox-end` is unchanged, so the
evaluated version is still the one at the tag.

| # | What was wrong | Impact | Fix |
|---|---|---|---|
| 1 | A 529 "overloaded" response was treated as permanent. The SDK raises it as `OverloadedError`, a direct `APIStatusError` subclass rather than an `InternalServerError`, so it fell through to the "rejected" branch. | When the API was busy, reports failed for good instead of being retried by the queue. | Errors are classified by status code: 408, 409, 429 and every 5xx are retried. The tests run the real SDK against a fake HTTP transport. `b969e48` |
| 2 | Calls that were billed but unusable (a refusal, an answer cut off or malformed, or one our own checks rejected) raised before their usage was saved. | Budgets under-counted exactly the bad runs, including every automatic retry. | Usage is recorded on every path, as `report_section:<key>:failed` when the answer wasn't used. Cost estimates calibrate on used sections only. `17a8248` |
| 3 | Retry, regenerate, issue and answer edits read the status and then wrote it. The worker set statuses without checking the current one. | A double click could queue two paid generations, and a stale or duplicate job could un-issue or fail an issued report. | The views lock the report row and re-check its status. The task and the failure handler only move a report from the status they expect. `bd50c87` |
| 4 | "Issued" only locked answer edits. Deleting a report while it was being generated crashed the worker. | An issued report could be deleted or renamed, and one deletion stopped background processing until a restart. | Deleting or renaming an issued report is refused, and so is deleting a report mid-generation. Task signals are sent robustly, and the worker loop survives unexpected errors. `c6c0a8b` |
| 5 | The production stack logged in to Postgres as the superuser, and the tenant role could read and write sessions and credentials. | Row-level security only protected code that remembered to set the tenant context. | The app and the worker log in as `nettle_app`, which isn't a superuser, can't bypass row-level security, and is refused tenant tables outside a tenant transaction (`NOINHERIT`). Grants are narrower, and only the migrate job and a host-only admin service use the owner role. The new role caught one real gap at once: `generate_report()` read the report outside a tenant transaction. Verified on the full production stack: as `nettle_app` it signs in, generates a report through the worker and refuses another organization's data. `d1e681a` |
| 6 | Clearing "Previous claims" wrote `""` into a non-null integer column. | A 500 error. | The column is nullable like the other optional numbers, since an empty field means "not recorded", not zero claims. A test checks that every built-in column can be emptied. `625eeab` |

What this changes in [SOLUTION.md](SOLUTION.md):

- "Approve and issue locks the report" now also covers deleting and renaming.
- Item 8 under "Documented, not fixed" (the superuser login) is fixed for production. The development stack still logs in as the owner, because one container runs the migrations, the seed and the Django admin.
- There are 173 tests (145 at the tag).

What I take from it: an independent review found real defects that my own tests
and live runs had missed. I'd make that a standing step before merging anything that touches tenancy, money or AI
calls.
