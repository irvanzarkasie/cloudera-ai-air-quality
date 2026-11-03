# Local environment (macOS)

The lab pins **CrewAI 0.120.1**, which requires **Python >=3.10 and <3.14**.  
Do **not** use the default Homebrew `python3` if it is **3.14** (your first `.venv` was created with 3.14 and `pip install` will fail).

## Recommended: Python 3.12

```bash
cd AirAware
deactivate 2>/dev/null || true

# Remove the old 3.14 venv if you created it (optional)
# rm -rf .venv

python3.12 -m venv .venv312    # or: python3.13 -m venv .venv312
source .venv312/bin/activate
python --version               # should show 3.12.x or 3.13.x

pip install --upgrade pip
pip install -r requirements-local.txt
```

`requirements-local.txt` matches `requirements.txt` except it **drops `pysqlite3-binary`** (no macOS arm64 wheel).

**Trimmed deps (workshop fork):** we removed **boto3** and **crewai-tools** — the Jakarta snapshot path does not use OpenAQ/S3 or extra CrewAI tools. **crewai** still installs its own stack (litellm, chromadb, openai, etc.) transitively.

On **Cloudera AI** use **Python 3.11**. Attendees: **`docs/workshop-attendee-guide.md`** (notebook = map + data; **terminal** = `main_v1.py` agent report). Notebook: **`Jakarta-Air-Snapshot-Lab.ipynb`**. Faster installs: **`docs/cai-workshop-dependencies.md`**.

## Verify

```bash
python -c "import crewai; print('crewai ok')"
python agent_tools/jakarta_air_sources.py
```

## Run the crew workflow

Set your OpenAI key (required for CrewAI LLM steps). **Do not use** the old lab placeholder `open-ai-key` in `.env` — that causes immediate 401 errors.

```bash
export OPENAI_API_KEY='sk-...'
# or uncomment and set OPENAI_API_KEY in AirAware/.env (see .env.example)
```

Test data fetch **without** an API key:

```bash
python main_v1.py --dry-run
```

Use **`main_v1.py`** or **`main_v2.py`** (both are filled in this workshop fork).  
Upstream lab **`main_v1.py`** is a skeleton until you copy agent/task rows from the lab guide.

```bash
python main_v1.py --user-input "Analyze air quality for Jakarta, Indonesia; focus on pm25."
```

On **CAI/CDSW SSH**, use **`--quiet`** (less box UI) and **`--output report.md`** so the full report is saved even if the web terminal truncates long stdout:

```bash
python main_v1.py --quiet -o report.md --user-input "Snapshot for Jakarta: worst and best ISPU today."
cat report.md
```

**Jakarta live data:** the air quality tool uses **udara.jakarta.go.id** (current SPKU snapshot).  
This workshop fork is **snapshot-only**: air quality comes from the latest **udara.jakarta.go.id** SPKU embed; weather uses **CurrentWeatherTool** (Open-Meteo current). Date ranges in user text are ignored—reports should cite the observation time from the Udara data, not a historical range.

## Optional: use `.venv` name instead of `.venv312`

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements-local.txt
```
