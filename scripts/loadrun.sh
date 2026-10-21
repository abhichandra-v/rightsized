#!/usr/bin/env bash
# Run the diurnal k6 load RUNS times and record cluster signals for each run.
#   scripts/loadrun.sh <label>     -> results/<label>/run<N>.json + run<N>.cluster.json
set -euo pipefail

label=${1:?usage: loadrun.sh <label>}
runs=${RUNS:-3}
day=${DAY_MINUTES:-20}
out="results/${label}"
mkdir -p "$out"

for i in $(seq 1 "$runs"); do
  echo "== ${label}: run ${i}/${runs} (${day} min)"
  SUMMARY="${out}/run${i}.json" DAY_MINUTES="$day" k6 run --quiet loadtest/diurnal.js
  # Range slightly wider than the run so the last scrape is included.
  rightsized capture --duration "$((day + 1))m" --node-selector "${NODE_SELECTOR:-}" --out "${out}/run${i}.cluster.json"
  # Let the trough settle so runs don't overlap in Prometheus' rate windows.
  sleep 60
done
