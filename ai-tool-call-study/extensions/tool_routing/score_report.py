from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


EXPECTED = {
    "monthly_net": {"2026-01": 480.75, "2026-02": 744.5},
    "largest_expense": {"date": "2026-01-20", "amount": -312.5, "category": "rent"},
    "expense_count": 6,
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Score a tool-routing trial report.")
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()

    try:
        actual = json.loads(args.report.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(json.dumps({"passed": False, "reason": "report.json was not created"}, indent=2))
        raise SystemExit(1)
    except json.JSONDecodeError as exc:
        print(json.dumps({"passed": False, "reason": f"invalid JSON: {exc.msg}"}, indent=2))
        raise SystemExit(1)

    passed = actual == EXPECTED
    print(json.dumps({"passed": passed, "expected": EXPECTED, "actual": actual}, indent=2))
    raise SystemExit(0 if passed else 1)


if __name__ == "__main__":
    main()
