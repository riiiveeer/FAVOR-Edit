"""Create a one-candidate smoke plan without hand-editing a full W1 plan."""

import argparse
from pathlib import Path

from w1_pipeline.delivery import make_smoke_plan


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    make_smoke_plan(args.input, args.output)
    print(f"wrote one-candidate smoke plan to {args.output}")


if __name__ == "__main__":
    main()
