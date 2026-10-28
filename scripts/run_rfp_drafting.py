"""CLI helper: run Part 2 drafting for an existing intake_complete ticket."""

from __future__ import annotations

import argparse
import json
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description="Run RFP Part 2 drafting for a ticket_id")
    parser.add_argument("ticket_id")
    args = parser.parse_args()

    from data.pipelines.rfp_intake import run_rfp_drafting

    result = run_rfp_drafting(args.ticket_id)
    print(json.dumps(result, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
