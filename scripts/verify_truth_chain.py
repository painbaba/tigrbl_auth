from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tba_auth.cli.truth import verify_truth_chain


def main() -> int:
    parser = argparse.ArgumentParser(description="Fail closed when current-state truth artifacts drift.")
    parser.add_argument(
        "--mode",
        choices=("all", "current-state", "release-decision", "repository-state"),
        default="all",
    )
    parser.add_argument(
        "--use-recorded-date",
        action="store_true",
        help="Use the committed snapshot date when comparing the current-state report.",
    )
    args = parser.parse_args()
    if args.use_recorded_date and args.mode != "current-state":
        parser.error("--use-recorded-date requires --mode current-state")
    payload = verify_truth_chain(ROOT, mode=args.mode, use_recorded_date=args.use_recorded_date)
    print(json.dumps(payload, indent=2))
    return 0 if payload["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
