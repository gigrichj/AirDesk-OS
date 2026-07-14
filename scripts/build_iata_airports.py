#!/usr/bin/env python3
import argparse
import csv
from pathlib import Path


def c_escape(value):
    return value.replace("\\", "\\\\").replace('"', '\\"')


def load_iata_cities(path, countries):
    rows = []
    seen = set()
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            iata = row.get("iata_code", "").strip().upper()
            if len(iata) != 3 or iata in seen:
                continue
            if row.get("closed") == "1":
                continue
            if countries and row.get("iso_country", "").strip().upper() not in countries:
                continue
            airport_type = row.get("type", "")
            if airport_type not in {"large_airport", "medium_airport"}:
                continue
            city = row.get("municipality", "").strip() or row.get("name", "").strip()
            if not city:
                continue
            seen.add(iata)
            rows.append((iata, city))
    rows.sort(key=lambda item: item[0])
    return rows


def write_header(path, rows):
    lines = [
        "#pragma once",
        "",
        "#include <stddef.h>",
        "",
        "struct IataAirportCity {",
        "    const char *iata;",
        "    const char *city;",
        "};",
        "",
        "static const IataAirportCity kIataAirportCities[] = {",
    ]
    for iata, city in rows:
        lines.append(f'    {{"{c_escape(iata)}", "{c_escape(city)}"}},')
    lines.extend([
        "};",
        "",
        "static constexpr size_t kIataAirportCityCount = sizeof(kIataAirportCities) / sizeof(kIataAirportCities[0]);",
        "",
    ])
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Build embedded IATA-to-city dataset from OurAirports airports.csv.")
    parser.add_argument("--airports", required=True, type=Path)
    parser.add_argument("--output", default=Path("src/airports_iata.h"), type=Path)
    parser.add_argument(
        "--countries",
        default="",
        help="Optional comma-separated ISO country allowlist, for example ES,GB,FR,DE,IT",
    )
    args = parser.parse_args()

    countries = {item.strip().upper() for item in args.countries.split(",") if item.strip()}
    rows = load_iata_cities(args.airports, countries)
    write_header(args.output, rows)
    print(f"Wrote {len(rows)} IATA airport city records to {args.output}")


if __name__ == "__main__":
    main()
