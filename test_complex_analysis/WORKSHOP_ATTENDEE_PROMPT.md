# Workshop prompt — copy & paste to Agent Studio

Use this as the **user message** to the agent (database: `id_workshop`, table: `jakarta_air_daily`).

---

## Prompt (recommended)

Based on our data in **`id_workshop.jakarta_air_daily`**, inspect the **last 7 days** (the seven most recent `observation_date` values in the table) and:

1. **Top 10 worst kecamatan by ISPU** — higher ISPU means worse air quality. Each kecamatan has many stations: for **each day**, average ISPU across all stations in that kecamatan, then for the week take the **average of those seven daily kecamatan averages**. List the **10 kecamatan with the highest** that weekly average.

2. **Top 3 kecamatan with the best ISPU improvement trend** over the same 7 days:
   - Use the same **daily kecamatan average ISPU** (one value per kecamatan per day).
   - Sort the 7 days **oldest to newest**.
   - **Improvement** means ISPU moves **from high toward low** over time (lower ISPU is better).
   - Choose the **3 kecamatan** where that decrease is **most steady across the whole week**, not just a good last day. Prefer kecamatan whose daily averages **keep falling** day after day; if you need a single score, use the **strongest negative correlation** between day order (1…7) and daily average ISPU.

**Rules:** You may **not** create new tables or **temporary** tables. Use **`WITH`** clauses only to stage steps (no `CREATE TEMPORARY TABLE`).

**Report:** State the 7 dates used, show the top-10 table (kecamatan + average ISPU), show the top-3 trend kecamatan with a one-line reason each, and mention that most historical rows may be marked `is_synthetic`.

---

## Shorter variant (if the agent already knows the table)

Same as above but minimal — use if the long prompt hits token limits:

> On `id_workshop.jakarta_air_daily`, for the **last 7 observation dates**: (1) **Worst 10 kecamatan** = highest mean of **daily** station-averaged ISPU across the week. (2) **Best 3 improvement trends** = daily kecamatan ISPU over days **oldest→newest**, pick the 3 with the **steadiest decrease** (strongest negative correlation of day index vs daily avg ISPU if available). **WITH clauses only**, no temp tables. List the 7 dates in your answer.

---

## Why the trend part was added (facilitator note)

The original prompt described “high to low” correctly but not **how to compare kecamatan fairly**. Without “daily average → order days → steady decrease / negative correlation,” agents often pick kecamatan with a low last day only. The additions above match the workshop reference analysis while staying one message for attendees.

Regenerate reference lists: `python test_complex_analysis/ground_truth.py` (facilitators only).
