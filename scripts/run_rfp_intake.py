"""CLI smoke runner for RFP intake: uv run python scripts/run_rfp_intake.py <ticket_id>"""

from __future__ import annotations

import sys


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: uv run python scripts/run_rfp_intake.py <ticket_id>")
    ticket_id = sys.argv[1]
    from data.pipelines.rfp_intake import run_rfp_intake

    result = run_rfp_intake(ticket_id)
    print(result)


if __name__ == "__main__":
    main()
