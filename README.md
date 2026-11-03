# Cloudera AI — Jakarta Air Quality Workshop (AirAware)

Hands-on lab for building **multi-agent air quality workflows** on **Cloudera AI Workbench**, using **live Jakarta SPKU data** from [udara.jakarta.go.id](https://udara.jakarta.go.id) and **CrewAI** in Python, then recreating the same pattern in **Agent Studio**.

The lab uses a **live snapshot** model: current station ISPU and pollutants from DKI’s public portal, plus **current weather** from Open-Meteo. User prompts that mention date ranges are ignored for air quality; reports should cite the **observation time** returned by the Udara data.

**Repository:** [github.com/irvanzarkasie/cloudera-ai-air-quality](https://github.com/irvanzarkasie/cloudera-ai-air-quality)

**Python:** **3.11** everywhere (Cloudera AI Workbench session runtime and local virtualenv). The repo pins this via `.python-version`; see **`LOCAL_SETUP.md`** for macOS install steps.

---

## Workshop flow (four parts)

| Step | What you do | Primary artifacts |
|------|-------------|-------------------|
| **1** | Create a Cloudera AI Workbench project from Git | Project + Python 3.11 session |
| **2** | Fetch and explore air quality in the notebook | `Jakarta-Air-Snapshot-Lab.ipynb` |
| **3** | Hand-build the multi-agent crew in code | `main_v1.py`, `agent_tools/` |
| **4** | Build a similar agent in Agent Studio | `agent_tools_cai_studio/` |

---

## Step 1 — Create a Cloudera AI Workbench project from Git

1. In **Cloudera AI Workbench**, go to **Projects** and create a **New Project** (choose a name and visibility per your site policy).
2. Under **Initial Setup**, select **Git** (not Blank, Template, or Local Files).
3. Set the Git source:
   - **Protocol:** **HTTPS** (unless your facilitator specifies SSH and you have keys configured).
   - **Repository URL:**  
     `https://github.com/irvanzarkasie/cloudera-ai-air-quality.git`
   - **Branch name (optional):** leave empty for the repo default, or enter **`main`** or **`Lab`** as directed by your facilitator.
4. Turn on **Advanced Options**, then under **Runtimes** add a session runtime for this lab:
   - **Editor:** **JupyterLab**
   - **Kernel:** **Python 3.11**
   - **Edition:** **Standard**
   - **Version:** **2026.08**
   - Click **Add Runtime** so it appears in the project runtime list (default images are often Python 3.10 only).
5. Click **Create Project**. Workbench clones the repository into the project; lab files (`main_v1.py`, `Jakarta-Air-Snapshot-Lab.ipynb`, `agent_tools/`, etc.) appear at the **project root**.
6. Start a **Session** and choose the **JupyterLab / Python 3.11 / Standard / 2026.08** runtime you added.
7. In a session terminal, install dependencies from the project root:

   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

   - **Notebook-only (fast):** `pip install -r requirements-minimal.txt` — enough for Udara fetch, tables, and the Folium map.
   - **Full lab (CrewAI):** `requirements.txt` pulls minimal + CrewAI add-on (`requirements-crewai-addon.txt`).

8. Configure **OpenAI** for agent steps (not required for notebook data fetch or `main_v1.py --dry-run`):

   - Set **`OPENAI_API_KEY`** in the project environment / session variables, **or**
   - Copy `.env.example` to `.env` in the project and set the key (do not commit `.env`).

**Local prep (optional):** same lab on your laptop with **Python 3.11** — see **`LOCAL_SETUP.md`** and `requirements-local.txt`.

---

## Step 2 — Notebook: fetch, analyze, and map

Open **`Jakarta-Air-Snapshot-Lab.ipynb`** in a Workbench session.

You will:

1. Run **setup** (`agent_tools/workshop_install.py` ensures pandas, requests, folium, etc.).
2. **Fetch** the live SPKU snapshot via `agent_tools/jakarta_air_sources.py` and station tables via `agent_tools/jakarta_viz.py`.
3. Display an **interactive ISPU map** (station markers colored by Indonesian ISPU bands).

The notebook is intentionally **data and visualization only**. It does **not** run the full CrewAI crew (long agent output is easier to manage in the terminal).

**Tip:** If Folium is missing on the base image, re-run the setup cell; CAI often ships pandas but not folium.

---

## Step 3 — Hand-build the agent in `main_v1.py`

In a **session terminal** (same project, repo root on `PYTHONPATH`), you **hand-build** the **Jakarta live snapshot crew** in **`main_v1.py`** (your facilitator may start from a skeleton file; this repo also ships the completed crew for reference):

- **Tools** (under `agent_tools/`):
  - `InputParserTool` — locations and parameters from natural language
  - `AirQualityAnalysisTool` — live readings from udara.jakarta.go.id
  - `CurrentWeatherTool` — current weather for context
- **Agents** — e.g. input parser, weather specialist, air quality retriever, analyst (LLM)
- **Tasks** — parse → weather → air quality → markdown report
- **Crew** — `Crew(agents=..., tasks=...)` and `kickoff()`

Verify **without** an API key (tools only):

```bash
python main_v1.py --dry-run
```

Run the full crew (requires `OPENAI_API_KEY`):

```bash
python main_v1.py --user-input "Report current Jakarta air quality; focus on pm25 and ispu."
```

On CAI/CDSW, prefer **`--quiet`** and write the full report to a file (web terminals may truncate stdout):

```bash
python main_v1.py --quiet -o report.md \
  --user-input "Snapshot for Jakarta: worst and best ISPU today."
cat report.md
```

**Reference:** `main_v1_full_soln.py` is a thin runner that delegates to the crew in `main_v1.py`. **`main_v2.py`** offers an alternate layout for comparison.

---

## Step 4 — Agent Studio: same story, visual workflow

Use **`agent_tools_cai_studio/`** to register the same tool surface in **Cloudera AI Agent Studio**:

| Studio-oriented module | Role |
|------------------------|------|
| `input_parser_tool.py` | Parse user intent (locations, parameters) |
| `air_quality_analysis_tool.py` | Live Jakarta SPKU snapshot |
| `weather_tool.py` | Current weather |
| `agent_tools/jakarta_air_sources.py` | Shared Udara fetch helpers |

Build an agent workflow that mirrors **`main_v1.py`**: parse input → fetch weather → fetch air quality → analyst produces a concise markdown snapshot (worst/best ISPU stations, observation time, weather note, conclusion). Wire tools to agents and tasks the same way you did in code, using Studio’s UI instead of Python `Agent` / `Task` definitions.

Your facilitator may provide Studio-specific screenshots or naming; the behavioral target is **parity with the Step 3 crew**.

---

## Data sources and behavior

| Source | Use in this lab |
|--------|------------------|
| [udara.jakarta.go.id](https://udara.jakarta.go.id) | Official live SPKU/LCS snapshot (`window.__SPKU_DATA__`) — ISPU, PM2.5, PM10, station names, **kecamatan** |
| [Open-Meteo](https://open-meteo.com/) | Current weather for Jakarta |

Air quality tool output is a **string summary** for the LLM (including ISPU extremes), not a raw dataframe inside the agent loop.

---

## Repository layout

```
├── Jakarta-Air-Snapshot-Lab.ipynb   # Step 2 — fetch, table, map
├── main_v1.py                       # Step 3 — CrewAI crew (hand-build focus)
├── main_v2.py                       # Alternate crew layout
├── main_v1_full_soln.py             # Reference runner
├── agent_tools/                     # Python tools for fetch, viz, and CrewAI
│   ├── jakarta_air_sources.py
│   ├── jakarta_viz.py
│   ├── air_quality_analysis_tool.py
│   ├── weather_tools.py
│   ├── input_parser_tool.py
│   └── workshop_install.py
├── agent_tools_cai_studio/          # Step 4 — Agent Studio tool copies
├── requirements*.txt                # Staged installs (minimal / CrewAI)
└── LOCAL_SETUP.md                   # macOS local dev notes
```

---

## Troubleshooting

| Issue | What to try |
|-------|-------------|
| `401` from OpenAI | Set a valid `OPENAI_API_KEY`; do not use placeholder values in `.env` |
| `No module named folium` | Re-run notebook setup or `pip install -r requirements-minimal.txt` |
| Truncated report in browser terminal | `python main_v1.py --quiet -o report.md` |
| CrewAI install slow | Install `requirements-minimal.txt` first for the notebook; add CrewAI when starting Step 3 |

---

## Acknowledgments

Based on the **AirAware** lab ([SuperEllipse/AirAware](https://github.com/SuperEllipse/AirAware)), adapted for **Jakarta live air quality** and **Cloudera AI** workshop delivery.
