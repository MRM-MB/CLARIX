# Clarix

**Probabilistic Capacity & Sourcing Engine** built for a Danfoss Climate Solutions hackathon.

> Danfoss (Denmark) organized a 1-day AI hackathon challenging teams to build a predictive manufacturing system — forecasting production capacity, simulating supply chain scenarios, and optimizing raw material sourcing across a global factory network. This is our submission.

---

## Screenshots

<!-- Add screenshots after running the app — place files in assets/screenshots/ -->
| Dashboard | Capacity Heatmap | AI Agent |
|-----------|-----------------|----------|
| ![Overview](assets/screenshots/overview.png) | ![Capacity](assets/screenshots/capacity.png) | ![Agent](assets/screenshots/agent.png) |

---

## What it does

- **13-page Streamlit dashboard** — capacity planner, bottleneck detector, sourcing MRP, logistics disruptions, executive overview
- **4 scenarios** — base / optimistic / pessimistic / monte carlo
- **AI agent** — Claude `tool_use` answers natural-language planner questions with real engine data
- **Demo mode** — guided 7-step narrative with step banners

---

## Quick start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. (Optional) Set API key for live AI agent
echo ANTHROPIC_API_KEY=sk-ant-... > .env

# 3. Generate processed data for advanced pages (run once)
python -m project.src.wave6.runner
python -m project.src.wave7.runner

# 4. Run
streamlit run app.py
```

Opens at **http://localhost:8501** — first load ~10 s (Excel parse), then instant.

---

## Stack

`Python 3.11` · `Streamlit` · `Pandas` · `Plotly` · `Claude claude-sonnet-4-6 (tool_use)`

---

## Project layout

```
app.py                  # Streamlit entry point (all 13 pages)
clarix/                 # Core engine: data loader, capacity maths, charts, AI agent
project/src/            # Wave 6/7 runners for advanced dashboard pages
project/data/processed/ # Pre-generated CSVs consumed by advanced pages
data/                   # hackathon_dataset.xlsx (26 MB, 13 sheets)
```

---

## Team

Built in one day at the Danfoss AI hackathon (April 2026).

| Name | GitHub |
|------|--------|
| Luigi | [@Lucol24](https://github.com/Lucol24) |
| Carolina | [@chaeyrie](https://github.com/chaeyrie) |
| Gabriele | [@Gabbo693](https://github.com/Gabbo693) |
| Lara | [@Lara-Ghi](https://github.com/Lara-Ghi) |
| Mats | [@mqts241](https://github.com/mqts241) |
| Manish | — |
