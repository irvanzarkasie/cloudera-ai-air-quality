# Complex Impala analysis — instruction review & agent test (isolated)

Does **not** modify production `main_v1.py` or workshop tools.

## Instruction review (workshop prompt)

### Strengths
- Clear data source: `id_workshop.jakarta_air_daily`
- Kecamatan aggregation rule (average station ISPU)
- Explicit constraint: **no new tables / no temp tables** — `WITH` CTEs allowed
- Trend definition: ISPU moving **high → low** over ordered days = improvement

### Ambiguities to steer in agent tasks
| Topic | Recommendation |
|--------|----------------|
| **Last 7 days** | Define as the 7 distinct `observation_date` values ending at `MAX(observation_date)` in the table (inclusive). |
| **Lower ISPU = better** | State explicitly so the model ranks “worst” by **highest** average ISPU. |
| **Trend “consistency”** | Define a metric, e.g. **Pearson/Spearman correlation** of `day_index` vs daily kecamatan avg ISPU (more **negative** = stronger steady improvement), with minimum 5 days of data. |
| **NULL kecamatan** | Exclude `kecamatan IS NULL` or `'unknown'`. |
| **Synthetic data** | Our backfill is mostly `is_synthetic=true`; mention in report so audience knows trends are illustrative. |
| **Multi-station** | Always `GROUP BY observation_date, kecamatan` then aggregate across days — never rank raw station rows as kecamatan. |

### SQL pattern (read-only, WITH-only)

See `ground_truth.py` and `sample_queries.sql` for reference implementations.

## Current `main_v1.py` crew — baseline expectation

| Capability | `AirQualityAnalysisCrew` |
|------------|---------------------------|
| Udara live snapshot | Yes |
| Impala / `jakarta_air_daily` | **No tool** |
| User’s analysis prompt | **Cannot run faithfully** — will guess or discuss ISPU generically |

Run baseline check:

```bash
cd AirAware
python test_complex_analysis/run_baseline_check.py
```

## Prototype steered crew (this folder)

```bash
cd AirAware
export OPENAI_API_KEY='...'
export IMPALA_USER=... IMPALA_PASSWORD=... IMPALA_HOST=... IMPALA_DATABASE=id_workshop

# Ground truth (no LLM)
python test_complex_analysis/ground_truth.py

# Steered multi-agent test
python test_complex_analysis/run_complex_analysis_crew.py --quiet -o test_complex_analysis/report.md
```

Compare agent output to `ground_truth.py` results.
