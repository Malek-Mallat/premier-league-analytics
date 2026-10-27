"""
Football Analytics BI — utilitaire d'appel API-Football.

Lit la clé depuis le fichier .env, appelle un endpoint,
affiche un résumé (errors / results / paging) et sauvegarde
la réponse JSON dans data/raw/.

Usage :
    python fetch.py status
    python fetch.py leagues id=39              -> data/raw/leagues.json
    python fetch.py teams league=39 season=2024 -> data/raw/teams.json

Option : --out nom_de_fichier pour forcer le nom du fichier de sortie.
    python fetch.py teams league=39 season=2024 --out teams_39_2024
"""

import sys
import json
import os
from pathlib import Path

import requests
from dotenv import load_dotenv

# --- Configuration ---------------------------------------------------------
BASE_URL = "https://v3.football.api-sports.io"
RAW_DIR = Path(__file__).parent / "data" / "raw"

load_dotenv()  # lit le fichier .env
API_KEY = os.getenv("API_FOOTBALL_KEY")


def main():
    if API_KEY is None:
        print("ERREUR : clé introuvable. Vérifie que .env contient "
              "API_FOOTBALL_KEY=... à la racine du projet.")
        sys.exit(1)

    args = sys.argv[1:]
    if not args:
        print('Usage : python fetch.py <endpoint> [param=valeur ...] [--out nom]')
        sys.exit(1)

    endpoint = args[0]

    # Nom de fichier de sortie : --out s'il est fourni, sinon le nom de l'endpoint
    out_name = endpoint
    params = {}
    i = 1
    while i < len(args):
        if args[i] == "--out":
            out_name = args[i + 1]
            i += 2
        elif "=" in args[i]:
            key, value = args[i].split("=", 1)
            params[key] = value
            i += 1
        else:
            print(f"Argument ignoré (format attendu cle=valeur) : {args[i]}")
            i += 1

    url = f"{BASE_URL}/{endpoint}"
    headers = {"x-apisports-key": API_KEY}

    print(f"Appel  : {url}")
    print(f"Params : {params if params else '(aucun)'}")

    response = requests.get(url, headers=headers, params=params, timeout=30)
    data = response.json()

    # Résumé de l'enveloppe (sans jamais afficher la clé)
    print(f"\nStatut HTTP : {response.status_code}")
    print(f"errors      : {data.get('errors')}")
    print(f"results     : {data.get('results')}")
    print(f"paging      : {data.get('paging')}")

    # Sauvegarde
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    out_path = RAW_DIR / f"{out_name}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\nSauvegardé  : {out_path}")


if __name__ == "__main__":
    main()
