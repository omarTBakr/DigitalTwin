"""Trigger ZenML pipelines.

Usage (from the repo root, after `zenml init` and with MongoDB running):
    uv run python -m tools.run --etl                                  # every enabled source
    uv run python -m tools.run --etl --user omar                      # one user's subscriptions
    uv run python -m tools.run --etl --source medium:tag:rag --source github:user:omartbakr
"""

import argparse
import sys

from llm_engineering.utils.dates import run_id
from pipelines.digital_data_etl import digital_data_etl


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--etl", action="store_true", help="crawl registered sources into MongoDB")
    parser.add_argument("--user", help="only this user's subscriptions")
    parser.add_argument(
        "--source", action="append", dest="sources", metavar="SOURCE_ID", help="only these source ids (repeatable)"
    )
    args = parser.parse_args()

    if not args.etl:
        parser.print_help()
        return 1
    digital_data_etl.with_options(run_name=f"digital_data_etl_{run_id()}")(user_id=args.user, source_ids=args.sources)
    return 0


if __name__ == "__main__":
    sys.exit(main())
