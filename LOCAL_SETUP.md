# Local environment (macOS)

Use the **same Python version as Cloudera AI Workbench: 3.11**.

The lab pins **CrewAI 0.120.1**, which requires **Python >=3.10 and <3.14**. Do **not** use Homebrew’s default `python3` if it is **3.14** — `pip install` for CrewAI will fail.

## Install Python 3.11 (one-time)

`python3.11: command not found` means **3.11 is not on your PATH yet** — install it, then create the venv.

**Homebrew (Apple Silicon):**

```bash
brew install python@3.11
/opt/homebrew/opt/python@3.11/bin/python3.11 --version
```

**pyenv** (repo has `.python-version` → `3.11`):

```bash
pyenv install 3.11.9
cd AirAware && pyenv local 3.11.9
python --version
```

Do **not** use bare `python3` on macOS if it reports **3.14** — CrewAI will not install there.

## Create a virtualenv

```bash
cd AirAware   # repo root
deactivate 2>/dev/null || true

# Required if .venv ever existed with another Python (e.g. 3.14):
# Re-running `python3.11 -m venv .venv` on an old venv leaves `python` → 3.14 symlinks.
rm -rf .venv .venv312

# After Homebrew install (adjust if Intel Mac: /usr/local/opt/python@3.11/...):
/opt/homebrew/opt/python@3.11/bin/python3.11 -m venv .venv

# If `python3.11` is on your PATH (pyenv or brew link), this also works:
# python3.11 -m venv .venv

source .venv/bin/activate
python --version   # should show 3.11.x

pip install --upgrade pip
pip install -r requirements-local.txt
```

`requirements-local.txt` matches `requirements.txt` except it **drops `pysqlite3-binary`** (no macOS arm64 wheel). On **Linux / CAI**, use `requirements.txt` so `pysqlite3-binary` is included.

## Verify

```bash
python -c "import crewai; print('crewai ok')"
python agent_tools/jakarta_air_sources.py
```

## Run the crew workflow

Set your OpenAI key (required for CrewAI LLM steps). **Do not use** placeholder keys in `.env` — that causes immediate 401 errors.

```bash
export OPENAI_API_KEY='sk-...'
# or set OPENAI_API_KEY in AirAware/.env (see .env.example)
```

Test data fetch **without** an API key:

```bash
python main_v1.py --dry-run
```

```bash
python main_v1.py --user-input "Analyze air quality for Jakarta, Indonesia; focus on pm25."
```

On CAI/CDSW SSH, use **`--quiet`** and **`--output report.md`** so the full report is saved if the web terminal truncates stdout:

```bash
python main_v1.py --quiet -o report.md --user-input "Snapshot for Jakarta: worst and best ISPU today."
cat report.md
```

**Jakarta live data:** air quality comes from the latest **udara.jakarta.go.id** SPKU snapshot; weather uses **CurrentWeatherTool** (Open-Meteo current). Date ranges in user text are ignored — reports should cite the observation time from the Udara data.

## If you only have Python 3.12 locally (temporary)

Cloudera AI sessions should still use **3.11**. On your Mac, **3.12 is fine** for the same lab code until 3.11 is installed:

```bash
python3.12 -m venv .venv   # e.g. ~/.local/bin/python3.12 if that is your 3.12
source .venv/bin/activate
pip install -r requirements-local.txt
```

Prefer moving to **3.11** when you can so local matches CAI.
