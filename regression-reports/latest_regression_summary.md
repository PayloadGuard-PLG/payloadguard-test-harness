# PayloadGuard Harness — Scan History

- **Collected (UTC):** `2026-10-26T17:20:34+00:00`
- **Check runs recorded:** `457` from `2026-04-24` to `2026-10-26`, across `38` fixtures
- **Source:** the `PayloadGuard` check run of every scan on each fixture PR's head commit (`regression-reports/scan_history.jsonl`, one record per check run with the full report)
- **Judged against:** the current `tools/test_cases.json`. Exit-code match is the live regression criterion (DESTRUCTIVE ⇔ expected exit 2); verdict match also compares SAFE/REVIEW/CAUTION. Aging cases are observational and excluded from both.

## Sweeps

| Started (UTC) | Analyser | Scans | Exit-code match | Verdict match | Exit-code mismatches |
|---|---|---|---|---|---|
| 2026-04-24 11:59 | unversioned (`main` @ `118827d`), unversioned (`main` @ `f6941e4`) | 18 | 3/14 | 3/14 | A01, A02, A04, A05, A07, A09, T03, T05, T09, T10, T11 |
| 2026-04-24 13:41 | unversioned (`main` @ `ac012cf`) | 36 | 6/28 | 6/28 | A01, A02, A04, A05, A07, A09, T03, T05, T09, T10, T11 |
| 2026-04-24 14:38 | unversioned (`main` @ `4220fc3`), unversioned (`main` @ `ea7eda6`) | 72 | 43/56 | 40/56 | A03, A05, T05, T09, T11 |
| 2026-05-25 15:44 | 1.1.0 (`3201411`) | 1 | 0/1 | 0/1 | WS03 |
| 2026-05-26 20:05 | 1.1.0 (`3201411`) | 5 | 4/5 | 3/5 | RTA02 |
| 2026-05-27 06:11 | 1.1.0 (`3201411`) | 5 | 5/5 | 5/5 | — |
| 2026-05-27 12:55 | 1.1.0 (`3201411`) | 5 | 5/5 | 5/5 | — |
| 2026-05-27 20:06 | 1.1.0 (`3201411`) | 5 | 5/5 | 5/5 | — |
| 2026-05-28 06:03 | 1.1.0 (`3201411`) | 5 | 5/5 | 5/5 | — |
| 2026-05-28 09:18 | 1.1.0 (`3201411`) | 10 | 10/10 | 10/10 | — |
| 2026-05-28 19:41 | 1.1.0 (`3201411`) | 15 | 15/15 | 15/15 | — |
| 2026-05-29 06:11 | 1.1.0 (`3201411`) | 5 | 5/5 | 5/5 | — |
| 2026-05-29 09:28 | 1.1.0 (`3201411`) | 10 | 10/10 | 10/10 | — |
| 2026-05-29 10:23 | 1.1.0 (`3201411`), 1.3.0 (`76139e9`), 1.3.0 (`ab31329`) | 129 | 124/129 | 120/129 | A03, A06, RT02, RTA03, WS07 |
| 2026-05-30 05:46 | 1.3.0 (`ab31329`) | 34 | 23/34 | 23/34 | A03, A06, AW02, AW04, RT01, RT02, RT03, RTA01, RTA03, RTA04, WS04 |
| 2026-05-31 06:15 | 1.3.0 (`257039a`) | 34 | 22/34 | 22/34 | A03, A06, AW02, AW04, RT01, RT02, RT03, RTA01, RTA03, RTA04, WS03, WS05 |
| 2026-05-31 14:11 | 1.3.0 (`fe68338`) | 34 | 34/34 | 33/34 | — |
| 2026-10-26 16:45 | 1.6.0 (`6c3df91`) | 34 | 34/34 | 27/34 | — |

## Latest scan per case

| ID | Expected | Latest | Analyser | Scanned (UTC) | Consequence detectors | Exit code | History (oldest → newest) |
|---|---|---|---|---|---|---|---|
| `T01` | `SAFE` | `SAFE` | unversioned (`main` @ `ea7eda6`) | 2026-04-24 15:38 | — | observing | `SSSSSSS` |
| `T02` | `SAFE` | `SAFE` | unversioned (`main` @ `ea7eda6`) | 2026-04-24 15:38 | — | observing | `SSSSSSS` |
| `T12` | `SAFE` | `SAFE` | unversioned (`main` @ `ea7eda6`) | 2026-04-24 15:38 | — | observing | `SSSSSSS` |
| `T03` | `DESTRUCTIVE` | `DESTRUCTIVE` | 1.6.0 (`6c3df91`) | 2026-10-26 16:45 | `D03_COMPOUND_LOSS`, `D04_PUBLIC_API_BREAK` | match | `CCCDDDDDDDDDDD` |
| `T04` | `DESTRUCTIVE` | `DESTRUCTIVE` | 1.6.0 (`6c3df91`) | 2026-10-26 16:46 | `D02_BODY_WEAKENING`, `D03_COMPOUND_LOSS`, `D04_PUBLIC_API_BREAK` | match | `DDDDDDDDDDDDDD` |
| `T05` | `DESTRUCTIVE` | `DESTRUCTIVE` | 1.6.0 (`6c3df91`) | 2026-10-26 16:46 | `D03_COMPOUND_LOSS`, `D04_PUBLIC_API_BREAK` | match | `CCCCCCDDDDDDDD` |
| `T09` | `DESTRUCTIVE` | `DESTRUCTIVE` | 1.6.0 (`6c3df91`) | 2026-10-26 16:46 | `D03_COMPOUND_LOSS`, `D04_PUBLIC_API_BREAK` | match | `CCCCCCDDDDDDDD` |
| `T10` | `DESTRUCTIVE` | `DESTRUCTIVE` | 1.6.0 (`6c3df91`) | 2026-10-26 16:47 | `D03_COMPOUND_LOSS`, `D04_PUBLIC_API_BREAK` | match | `CCCDDDDDDDDDDDD` |
| `T11` | `DESTRUCTIVE` | `DESTRUCTIVE` | 1.6.0 (`6c3df91`) | 2026-10-26 16:47 | `D03_COMPOUND_LOSS`, `D04_PUBLIC_API_BREAK` | match | `CCCCCCDDDDDDDD` |
| `A01` | `DESTRUCTIVE` | `DESTRUCTIVE` | 1.6.0 (`6c3df91`) | 2026-10-26 16:47 | `D03_COMPOUND_LOSS`, `D04_PUBLIC_API_BREAK` | match | `CCCDDDDDDDDDDD` |
| `A02` | `DESTRUCTIVE` | `DESTRUCTIVE` | 1.6.0 (`6c3df91`) | 2026-10-26 16:47 | `D02_BODY_WEAKENING`, `D03_COMPOUND_LOSS`, `D04_PUBLIC_API_BREAK` | match | `CCCDDDDDDDDDDD` |
| `A03` | `SAFE` | `REVIEW` | 1.6.0 (`6c3df91`) | 2026-10-26 16:47 | `D03_COMPOUND_LOSS`, `D04_PUBLIC_API_BREAK`, `D06_GUARD_REGRESSION` | match | `SSSCCCDSSDDDSR` |
| `A04` | `DESTRUCTIVE` | `DESTRUCTIVE` | 1.6.0 (`6c3df91`) | 2026-10-26 16:47 | `D03_COMPOUND_LOSS`, `D04_PUBLIC_API_BREAK` | match | `RRRDDDDDDDDDDD` |
| `A05` | `DESTRUCTIVE` | `DESTRUCTIVE` | 1.6.0 (`6c3df91`) | 2026-10-26 16:47 | `D02_BODY_WEAKENING`, `D03_COMPOUND_LOSS`, `D04_PUBLIC_API_BREAK` | match | `CCCCCCDDDDDDDDD` |
| `A06` | `SAFE` | `REVIEW` | 1.6.0 (`6c3df91`) | 2026-10-26 16:48 | `D03_COMPOUND_LOSS`, `D04_PUBLIC_API_BREAK` | match | `SSSSSSSSSSDDDSR` |
| `A07` | `DESTRUCTIVE` | `DESTRUCTIVE` | 1.6.0 (`6c3df91`) | 2026-10-26 16:48 | `D02_BODY_WEAKENING`, `D03_COMPOUND_LOSS`, `D04_PUBLIC_API_BREAK` | match | `CCCDDDDDDDDDDD` |
| `A09` | `DESTRUCTIVE` | `DESTRUCTIVE` | 1.6.0 (`6c3df91`) | 2026-10-26 16:48 | — | match | `RRRDDDDDDDDDDD` |
| `A10` | `SAFE` | `SAFE` | unversioned (`main` @ `ea7eda6`) | 2026-04-24 15:38 | — | observing | `SSSSSSS` |
| `WS01` | `DESTRUCTIVE` | `DESTRUCTIVE` | 1.6.0 (`6c3df91`) | 2026-10-26 16:48 | — | match | `DDDDDDD` |
| `WS02` | `DESTRUCTIVE` | `DESTRUCTIVE` | 1.6.0 (`6c3df91`) | 2026-10-26 16:48 | — | match | `DDDDDDD` |
| `WS03` | `CAUTION` | `CAUTION` | 1.6.0 (`6c3df91`) | 2026-10-26 16:49 | — | match | `DCCCCDCC` |
| `WS04` | `CAUTION` | `CAUTION` | 1.6.0 (`6c3df91`) | 2026-10-26 16:49 | — | match | `CCCDCCC` |
| `WS05` | `CAUTION` | `CAUTION` | 1.6.0 (`6c3df91`) | 2026-10-26 16:49 | — | match | `CCCCDCC` |
| `WS06` | `DESTRUCTIVE` | `DESTRUCTIVE` | 1.6.0 (`6c3df91`) | 2026-10-26 16:49 | `D08_WORKFLOW_INTEGRITY` | match | `DDDDDDDD` |
| `WS07` | `SAFE` | `REVIEW` | 1.6.0 (`6c3df91`) | 2026-10-26 16:49 | — | match | `SSDSSSR` |
| `AW01` | `DESTRUCTIVE` | `DESTRUCTIVE` | 1.6.0 (`6c3df91`) | 2026-10-26 16:49 | — | match | `DDDDDDD` |
| `AW02` | `CAUTION` | `CAUTION` | 1.6.0 (`6c3df91`) | 2026-10-26 16:50 | — | match | `CCCDDCC` |
| `AW03` | `DESTRUCTIVE` | `DESTRUCTIVE` | 1.6.0 (`6c3df91`) | 2026-10-26 16:50 | `D08_WORKFLOW_INTEGRITY` | match | `DDDDDDD` |
| `AW04` | `SAFE` | `REVIEW` | 1.6.0 (`6c3df91`) | 2026-10-26 16:50 | `D08_WORKFLOW_INTEGRITY` | match | `SSSDDSR` |
| `AW05` | `DESTRUCTIVE` | `DESTRUCTIVE` | 1.6.0 (`6c3df91`) | 2026-10-26 16:50 | — | match | `DDDDDDD` |
| `RTA01` | `REVIEW` | `REVIEW` | 1.6.0 (`6c3df91`) | 2026-10-26 16:50 | — | match | `RRRRRRRRRRRRRRRRSSSSDDSR` |
| `RTA02` | `DESTRUCTIVE` | `DESTRUCTIVE` | 1.6.0 (`6c3df91`) | 2026-10-26 16:50 | — | match | `SDDDDDDDDDDDDDDDDDDDDDDD` |
| `RTA03` | `CAUTION` | `CAUTION` | 1.6.0 (`6c3df91`) | 2026-10-26 16:50 | `D08_WORKFLOW_INTEGRITY` | match | `CCCCCCCCCCCCCCCCCCCDDDCC` |
| `RTA04` | `CAUTION` | `CAUTION` | 1.6.0 (`6c3df91`) | 2026-10-26 16:51 | — | match | `SCCCCCCCCCCCCCCCCCCCDDCC` |
| `RTA05` | `DESTRUCTIVE` | `DESTRUCTIVE` | 1.6.0 (`6c3df91`) | 2026-10-26 16:51 | — | match | `DDDDDDDDDDDDDDDDDDDDDDDD` |
| `RT01` | `SAFE` | `REVIEW` | 1.6.0 (`6c3df91`) | 2026-10-26 16:51 | — | match | `SSSSDDSR` |
| `RT02` | `SAFE` | `REVIEW` | 1.6.0 (`6c3df91`) | 2026-10-26 16:51 | — | match | `SSSDDDSR` |
| `RT03` | `SAFE` | `REVIEW` | 1.6.0 (`6c3df91`) | 2026-10-26 16:51 | — | match | `SSSSDDSR` |

History letters: S = SAFE, R = REVIEW, C = CAUTION, D = DESTRUCTIVE.
