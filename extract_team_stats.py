"""
Football Analytics BI — extraction en masse de FactTeamStats.

Récupère les statistiques détaillées (/fixtures/statistics) pour TOUS les
matchs de la saison, en respectant le quota de l'API-Football gratuite :
  - 10 requêtes / minute  -> pause entre chaque appel
  - 100 requêtes / jour   -> on s'arrête à MAX_REQUESTS_PER_RUN

Reprise automatique (idempotent) :
  - un match déjà téléchargé (fichier déjà présent) est SAUTÉ.
  - on relance simplement le même script chaque jour : il continue
    là où il s'était arrêté, jusqu'à avoir les 380 matchs.

Usage :
    python extract_team_stats.py
"""

import json
import time
import os
from pathlib import Path

import requests
from dotenv import load_dotenv

# --- Réglages -------------------------------------------------------------
MAX_REQUESTS_PER_RUN = 90     # marge de 10 sous la limite de 100/jour
SECONDS_BETWEEN_CALLS = 7     # 60s / 7 ≈ 8 appels/min, < 10/min : sûr

BASE_URL = "https://v3.football.api-sports.io"
PROJECT_DIR = Path(__file__).parent
RAW_DIR = PROJECT_DIR / "data" / "raw"
FIXTURES_FILE = RAW_DIR / "fixtures_39_2024.json"
STATS_DIR = RAW_DIR / "team_stats"      # un fichier par match ici

load_dotenv()
API_KEY = os.getenv("API_FOOTBALL_KEY")


def load_fixture_ids():
    """Lit les ids de match depuis le fichier fixtures déjà extrait."""
    with open(FIXTURES_FILE, encoding="utf-8") as f:
        data = json.load(f)
    ids = [match["fixture"]["id"] for match in data["response"]]
    return ids


def already_done(fixture_id):
    """Vrai si le fichier de stats de ce match existe déjà."""
    return (STATS_DIR / f"stats_{fixture_id}.json").exists()


def fetch_stats(fixture_id):
    """Appelle l'API pour un match et renvoie le JSON."""
    url = f"{BASE_URL}/fixtures/statistics"
    headers = {"x-apisports-key": API_KEY}
    params = {"fixture": fixture_id}
    response = requests.get(url, headers=headers, params=params, timeout=30)
    return response.json()


def main():
    if API_KEY is None:
        print("ERREUR : clé introuvable. Vérifie le fichier .env.")
        return

    STATS_DIR.mkdir(parents=True, exist_ok=True)

    all_ids = load_fixture_ids()
    todo = [fid for fid in all_ids if not already_done(fid)]
    done_count = len(all_ids) - len(todo)

    print("=" * 50)
    print(f"Total matchs        : {len(all_ids)}")
    print(f"Déjà téléchargés    : {done_count}")
    print(f"Restants à faire    : {len(todo)}")
    print(f"Max ce run          : {MAX_REQUESTS_PER_RUN}")
    print("=" * 50)

    if not todo:
        print("\n✅ Terminé ! Tous les matchs sont déjà téléchargés.")
        return

    requests_made = 0
    for fixture_id in todo:
        if requests_made >= MAX_REQUESTS_PER_RUN:
            print(f"\n⏸  Limite de {MAX_REQUESTS_PER_RUN} requêtes atteinte pour ce run.")
            print("   Relance le script demain pour continuer.")
            break

        data = fetch_stats(fixture_id)
        requests_made += 1

        # Vérifier l'enveloppe avant de sauver
        errors = data.get("errors")
        if errors:
            print(f"⚠  Match {fixture_id} : erreur API -> {errors}")
            # Si c'est un problème de quota, on arrête proprement
            if isinstance(errors, dict) and "rateLimit" in str(errors).lower():
                print("   Quota atteint côté API. On s'arrête.")
                break
            continue

        out_path = STATS_DIR / f"stats_{fixture_id}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"[{requests_made:>2}/{MAX_REQUESTS_PER_RUN}] match {fixture_id} ✓")

        time.sleep(SECONDS_BETWEEN_CALLS)

    # Bilan de fin
    remaining = len([fid for fid in all_ids if not already_done(fid)])
    print("\n" + "=" * 50)
    print(f"Requêtes faites ce run : {requests_made}")
    print(f"Matchs restants        : {remaining}")
    if remaining == 0:
        print("🎉 Extraction COMPLÈTE ! Les 380 matchs sont téléchargés.")
    else:
        print("↻ Relance le même script demain pour continuer.")
    print("=" * 50)


if __name__ == "__main__":
    main()
