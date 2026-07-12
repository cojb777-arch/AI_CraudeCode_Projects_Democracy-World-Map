# -*- coding: utf-8 -*-
"""OWIDのCSVから各国の最新値を抽出して data/indicators.js を生成する。"""
import csv
import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data")

# (ファイル名, 値の列名, 指標キー)
SOURCES = [
    ("electoral-democracy-index.csv", "Electoral democracy index", "electdem"),
    ("liberal-democracy-index.csv", "Liberal democracy index", "libdem"),
    ("political-regime.csv", "Political regime", "regime"),
    ("freedom-of-expression-index.csv", "Freedom of expression index", "freexp"),
    ("human-rights-index-vdem.csv", "Human Rights Index", "humrights"),
    ("rule-of-law-index.csv", "Rule of Law index", "rulelaw"),
    ("ti-corruption-perception-index.csv", "Corruption Perceptions Index", "cpi"),
]


def load_latest(path, col):
    """ISO3コードごとに最新年の値を返す {iso3: (year, value)}"""
    out = {}
    with open(path, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            code = (row.get("Code") or "").strip()
            if len(code) != 3 or code.startswith("OWID"):
                continue
            val = (row.get(col) or "").strip()
            if val == "":
                continue
            try:
                year = int(row["Year"])
                v = float(val)
            except ValueError:
                continue
            if code not in out or year > out[code][0]:
                out[code] = (year, v)
    return out


def load_conflict(path):
    """紛争死者数: 最新年の値と直近10年の累計 {iso3: (year, latest, sum10)}"""
    rows = {}
    with open(path, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            code = (row.get("Code") or "").strip()
            if len(code) != 3 or code.startswith("OWID"):
                continue
            val = (row.get("Best estimate") or "").strip()
            if val == "":
                continue
            try:
                year = int(row["Year"])
                v = float(val)
            except ValueError:
                continue
            rows.setdefault(code, {})[year] = v
    out = {}
    for code, series in rows.items():
        latest = max(series)
        s10 = sum(v for y, v in series.items() if y > latest - 10)
        out[code] = (latest, series[latest], s10)
    return out


def main():
    indicators = {}
    for fname, col, key in SOURCES:
        data = load_latest(os.path.join(DATA, fname), col)
        indicators[key] = {
            "values": {c: round(v, 4) for c, (y, v) in data.items()},
            "years": {c: y for c, (y, v) in data.items()},
        }
        print(f"{key}: {len(data)} countries, year range "
              f"{min(y for y, _ in data.values())}-{max(y for y, _ in data.values())}")

    conflict = load_conflict(os.path.join(DATA, "deaths-in-armed-conflicts.csv"))
    indicators["conflict"] = {
        "values": {c: v for c, (y, v, s) in conflict.items()},
        "years": {c: y for c, (y, v, s) in conflict.items()},
    }
    indicators["conflict10"] = {
        "values": {c: s for c, (y, v, s) in conflict.items()},
        "years": {c: y for c, (y, v, s) in conflict.items()},
    }
    print(f"conflict: {len(conflict)} countries")

    # ISO3 -> ISO2 (国名の日本語表示 Intl.DisplayNames 用)
    iso2 = {}
    with open(os.path.join(DATA, "iso3166.csv"), encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            iso2[row["alpha-3"]] = row["alpha-2"]

    with open(os.path.join(DATA, "indicators.js"), "w", encoding="utf-8") as f:
        f.write("var INDICATOR_DATA = ")
        json.dump(indicators, f, ensure_ascii=False, separators=(",", ":"))
        f.write(";\nvar ISO3_TO_ISO2 = ")
        json.dump(iso2, f, ensure_ascii=False, separators=(",", ":"))
        f.write(";\n")

    # GeoJSON -> JSリテラル (file:// でも読めるように)
    with open(os.path.join(DATA, "countries.geo.json"), encoding="utf-8") as f:
        geo = json.load(f)
    with open(os.path.join(DATA, "geo.js"), "w", encoding="utf-8") as f:
        f.write("var WORLD_GEO = ")
        json.dump(geo, f, ensure_ascii=False, separators=(",", ":"))
        f.write(";\n")
    print(f"geo: {len(geo['features'])} features")


if __name__ == "__main__":
    main()
