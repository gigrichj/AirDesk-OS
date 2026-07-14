#!/usr/bin/env python3
import argparse
import csv
import math
from pathlib import Path


def parse_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def bearing(lat1, lon1, lat2, lon2):
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dlon = math.radians(lon2 - lon1)
    y = math.sin(dlon) * math.cos(phi2)
    x = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(dlon)
    return (math.degrees(math.atan2(y, x)) + 360.0) % 360.0


def load_large_airports(path):
    airports = {}
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("type") not in {"large_airport", "medium_airport"}:
                continue
            if row.get("closed") == "1":
                continue
            ident = row.get("ident", "").strip()
            if not ident:
                continue
            airports[ident] = {
                "lat": parse_float(row.get("latitude_deg")),
                "lon": parse_float(row.get("longitude_deg")),
            }
    return airports


def runway_segments(airports, path, limit):
    segments = []
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            ident = row.get("airport_ident", "").strip()
            if ident not in airports:
                continue
            if row.get("closed") == "1":
                continue
            le_lat = parse_float(row.get("le_latitude_deg"))
            le_lon = parse_float(row.get("le_longitude_deg"))
            he_lat = parse_float(row.get("he_latitude_deg"))
            he_lon = parse_float(row.get("he_longitude_deg"))
            if not (le_lat and le_lon and he_lat and he_lon):
                ap = airports[ident]
                heading = parse_float(row.get("le_heading_degT"), 0.0)
                length_km = parse_float(row.get("length_ft"), 0.0) * 0.0003048
                segments.append((ident, ap["lat"], ap["lon"], heading, length_km))
                continue
            lat = (le_lat + he_lat) * 0.5
            lon = (le_lon + he_lon) * 0.5
            heading = bearing(he_lat, he_lon, le_lat, le_lon)
            length_km = parse_float(row.get("length_ft"), 0.0) * 0.0003048
            segments.append((ident, lat, lon, heading, length_km))
    segments.sort(key=lambda item: item[0])
    return segments[:limit]


def write_header(path, segments):
    lines = [
        "#pragma once",
        "",
        "#include <stddef.h>",
        "",
        "struct RunwaySegment {",
        "    const char *icao;",
        "    float lat;",
        "    float lon;",
        "    float headingDeg;",
        "    float lengthKm;",
        "};",
        "",
        "static const RunwaySegment kRunways[] = {",
    ]
    for ident, lat, lon, heading, length_km in segments:
        lines.append(f'    {{"{ident}", {lat:.6f}f, {lon:.6f}f, {heading:.1f}f, {length_km:.2f}f}},')
    lines.extend([
        "};",
        "",
        "static constexpr size_t kRunwayCount = sizeof(kRunways) / sizeof(kRunways[0]);",
        "",
    ])
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Build embedded runway dataset from OurAirports CSV files.")
    parser.add_argument("--airports", required=True, type=Path)
    parser.add_argument("--runways", required=True, type=Path)
    parser.add_argument("--output", default=Path("src/airports.h"), type=Path)
    parser.add_argument("--limit", default=700, type=int)
    args = parser.parse_args()

    airports = load_large_airports(args.airports)
    segments = runway_segments(airports, args.runways, args.limit)
    write_header(args.output, segments)
    print(f"Wrote {len(segments)} runway segments to {args.output}")


if __name__ == "__main__":
    main()
