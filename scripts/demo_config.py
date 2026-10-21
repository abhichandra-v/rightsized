"""Write a compressed-time config for the demo: rightsized.yaml with the window and the
data-confidence thresholds scaled to DAY_MINUTES and OBSERVE_DAYS.

    python scripts/demo_config.py results/rightsized.demo.yaml
"""

import os
import sys

from ruamel.yaml import YAML

day = float(os.environ.get("DAY_MINUTES", 20))
days = int(os.environ.get("OBSERVE_DAYS", 7))

y = YAML()
cfg = y.load(open("rightsized.yaml"))
# Lookback covers the whole observation phase (each run is followed by a 1 min pause) plus slack.
cfg["window"] = f"{int(days * (day + 1) + 15)}m"
cfg["policy"]["min_window_hours"] = round(day / 60, 4)  # one compressed day
cfg["policy"]["full_window_days"] = round(days * day / 1440, 4)  # one compressed week
with open(sys.argv[1], "w") as f:
    y.dump(cfg, f)
print(f"{sys.argv[1]}: window={cfg['window']}, day={day}m, week={days * day:.0f}m")
