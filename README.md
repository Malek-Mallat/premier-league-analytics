# ⚽ Football Analytics BI — Premier League 2024-25

An end-to-end Business Intelligence project on the English Premier League,
built from a live REST API all the way to an interactive web dashboard.

**🔗 Live dashboard:** _(add your GitHub Pages link here once published)_

[![Premier League Analytics dashboard](docs/preview.png)](https://malek-mallat.github.io/premier-league-analytics/)

---

## What it does

The project turns raw football data from the [API-Football](https://www.api-football.com/)
REST API into analytical KPIs that go **beyond the classic league table** you find on
score apps — expected goals (xG), shot accuracy, possession dominance, a custom
discipline index, and team profiles on a radar.

It is delivered two ways from the **same data pipeline**:

- a **web dashboard** (`index.html`, vanilla HTML/CSS/JS + Chart.js) — interactive,
  filterable by team, hostable for free on GitHub Pages;
- a **Power BI** report built on a star-schema / constellation model (`.pbix`, not
  tracked here).

---

## The pipeline

```
API-Football  ──►  Python extraction  ──►  raw JSON (data/raw/)
                   (fetch.py,                    │
                    extract_team_stats.py)       ▼
                                          Python aggregation
                                          (build_data.py)
                                                 │
                                                 ▼
                                          index.html  (Chart.js)
```

1. **Extract** — `fetch.py` explores the API; `extract_team_stats.py` pulls the
   per-match statistics for all 380 matches, respecting the free plan's quota
   (100 requests/day) with a **resumable, idempotent** loop that skips matches
   already downloaded and continues the next day.
2. **Aggregate** — `build_data.py` reads the raw JSON (standings + per-match stats),
   computes per-team metrics, and injects them into the dashboard template to
   produce a ready-to-open `index.html`.
3. **Visualise** — the dashboard renders results, play-quality and team-profile
   views with Chart.js.

---

## Data model (Power BI)

A **constellation** schema: several fact tables sharing common dimensions.

- **Dimensions:** `DimTeam`, `DimDate`, `DimCompetition`
- **Facts:** `FactMatches`, `FactStandings`, `FactTeamStats`
- Linked by `team_id`, `match_id` and the match date. Fact tables never link to
  each other directly (that creates ambiguous filter paths) — only through
  shared dimensions.

---

## KPIs

| Area | Metrics |
|---|---|
| **Results** | points, wins/draws/losses, goals scored & conceded, goal difference |
| **Play quality** | average possession, shots per match, shot accuracy, xG per match |
| **Profile & style** | discipline index (fouls + cards), possession vs results, 5-axis radar |

**Example insight:** Manchester City — the highest-possession side (62%) — has the
**lowest discipline index** in the league. Discipline looks like a *consequence*
of dominance, not a cause of winning.

---

## Run it yourself

```bash
# 1. add your API key
echo "API_FOOTBALL_KEY=your_key_here" > .env

# 2. install deps
pip install requests python-dotenv

# 3. extract match stats (run daily until all 380 are downloaded)
python extract_team_stats.py

# 4. build the dashboard from the real data
python build_data.py        # writes index.html

# 5. open index.html in a browser
```

> Raw API responses (`data/raw/`) and the API key (`.env`) are **not** committed
> (size + API terms + secrets). The scripts regenerate everything.

---

## Tech stack

`Python` · `API-Football (REST)` · `Chart.js` · `HTML / CSS / JS` · `Power BI` ·
`Power Query (M)` · `DAX`

## Author

**Malek Mallat** — [github.com/Malek-Mallat](https://github.com/Malek-Mallat)
