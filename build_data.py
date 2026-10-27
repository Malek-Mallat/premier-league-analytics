"""
Football Analytics BI — agrégation pour le dashboard web.

Lit les JSON bruts (data/raw/) et produit la ligne de données attendue par
le dashboard HTML (pl-dashboard.html) :

  - Résultats (saison complète)        <- standings.json
  - Équipes + codes 3 lettres          <- teams_39_2024.json
  - Mesures de jeu (poss, tirs, xG...)  <- data/raw/team_stats/*.json

Sortie :
  - data/dashboard_data.json  (les données, lisibles)
  - index.html                (le dashboard fini, données injectées, prêt à ouvrir
                               et à publier sur GitHub Pages)

Le fichier pl-dashboard.html (le "gabarit") doit être dans le même dossier.

Usage :  python build_data.py
"""

import json
import glob
import re
from pathlib import Path

BASE = Path(__file__).parent
RAW_DIR = BASE / "data" / "raw"
STATS_DIR = RAW_DIR / "team_stats"
OUT = BASE / "data" / "dashboard_data.json"
TEMPLATE = BASE / "pl-dashboard.html"   # le gabarit
INDEX = BASE / "index.html"             # le dashboard généré


def num(v):
    """Convertit '55%', '2.43', 12, None -> float ou None."""
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).replace("%", "").strip()
    try:
        return float(s)
    except ValueError:
        return None


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# --- 1. Équipes : id -> (nom, code) -------------------------------------
teams = {}
tdata = load(RAW_DIR / "teams_39_2024.json")
for item in tdata["response"]:
    t = item["team"]
    teams[t["id"]] = {"name": t["name"], "short": t.get("code") or t["name"][:3].upper()}

# --- 2. Classement : résultats complets ---------------------------------
results = {}
sdata = load(RAW_DIR / "standings.json")
table = sdata["response"][0]["league"]["standings"][0]
for row in table:
    tid = row["team"]["id"]
    allg = row["all"]
    results[tid] = {
        "pts": row["points"],
        "bm": allg["goals"]["for"],
        "be": allg["goals"]["against"],
        "v": allg["win"], "n": allg["draw"], "d": allg["lose"],
    }

# --- 3. Stats de jeu : moyennes par équipe sur les matchs extraits ------
acc = {}  # tid -> listes de valeurs


def push(tid, key, val):
    acc.setdefault(tid, {}).setdefault(key, []).append(val)


files = glob.glob(str(STATS_DIR / "*.json"))
for fp in files:
    data = load(fp)
    if data.get("errors"):
        continue
    for team_block in data.get("response", []):
        tid = team_block["team"]["id"]
        stat = {s["type"]: num(s["value"]) for s in team_block["statistics"]}
        poss = stat.get("Ball Possession")
        if poss is not None and poss <= 1:   # si stocké en fraction
            poss *= 100
        push(tid, "poss", poss)
        push(tid, "tirs", stat.get("Total Shots"))
        push(tid, "on", stat.get("Shots on Goal"))
        push(tid, "xg", stat.get("expected_goals"))
        push(tid, "fouls", stat.get("Fouls"))
        push(tid, "yc", stat.get("Yellow Cards") or 0)
        push(tid, "rc", stat.get("Red Cards") or 0)


def avg(xs):
    xs = [x for x in xs if x is not None]
    return round(sum(xs) / len(xs), 2) if xs else None


play = {}
for tid, d in acc.items():
    tot_on = sum(x for x in d.get("on", []) if x is not None)
    tot_sh = sum(x for x in d.get("tirs", []) if x is not None)
    play[tid] = {
        "poss": avg(d.get("poss", [])),
        "tirs": round(avg(d.get("tirs", []))) if d.get("tirs") else None,
        "xg": avg(d.get("xg", [])),
        "prec": round(tot_on / tot_sh * 100, 1) if tot_sh else None,
        "disc": round((avg(d.get("fouls", [])) or 0)
                      + (avg(d.get("yc", [])) or 0)
                      + 3 * (avg(d.get("rc", [])) or 0), 2) if d.get("fouls") else None,
    }

# --- 4. Fusion + tri par points -----------------------------------------
rows = []
for tid, r in results.items():
    info = teams.get(tid, {"name": str(tid), "short": "?"})
    p = play.get(tid, {})
    rows.append({
        "name": info["name"], "short": info["short"],
        "pts": r["pts"], "bm": r["bm"], "be": r["be"],
        "v": r["v"], "n": r["n"], "d": r["d"],
        "poss": p.get("poss"), "tirs": p.get("tirs"),
        "xg": p.get("xg"), "prec": p.get("prec"), "disc": p.get("disc"),
    })
rows.sort(key=lambda x: (-x["pts"], -(x["bm"] - x["be"]), -x["bm"]))

# --- 5. Écriture + affichage du bloc RAW --------------------------------
OUT.parent.mkdir(parents=True, exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(rows, f, ensure_ascii=False, indent=2)

order = ["name", "short", "pts", "bm", "be", "v", "n", "d",
         "poss", "tirs", "xg", "prec", "disc"]


def js_cell(v):
    if isinstance(v, str):
        return '"' + v.replace('"', '\\"') + '"'
    if v is None:
        return "null"
    return str(v)


raw_lines = ["const RAW = ["]
for r in rows:
    raw_lines.append("  [" + ",".join(js_cell(r[k]) for k in order) + "],")
raw_lines.append("];")
raw_block = "\n".join(raw_lines)

print(f"\n{len(rows)} équipes · {len(files)} fichiers de stats lus.")
print(f"Écrit : {OUT}")

# --- injecte le bloc RAW dans le gabarit -> index.html ------------------
if TEMPLATE.exists():
    html = TEMPLATE.read_text(encoding="utf-8")
    new_html, n = re.subn(r"const RAW = \[.*?\n\];", raw_block, html, count=1, flags=re.DOTALL)
    if n == 1:
        INDEX.write_text(new_html, encoding="utf-8")
        print(f"Écrit : {INDEX}  <-  ouvre ce fichier dans ton navigateur")
    else:
        print("ATTENTION : bloc 'const RAW = [...]' introuvable dans pl-dashboard.html.")
else:
    print(f"ATTENTION : gabarit {TEMPLATE.name} absent — index.html non généré.")
    print("\nBloc RAW (à coller manuellement) :\n")
    print(raw_block)
