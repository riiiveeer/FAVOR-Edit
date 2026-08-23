"""Build or verify the E0 visual audit package.

Build:
    python scripts/build_e0_audit.py \
        --plan <E0/plan.json> \
        --candidates <E0/candidates.json> \
        --output-dir <E0_AUDIT dir>

Verify an existing (human-filled) audit package:
    python scripts/build_e0_audit.py --verify-existing <E0_AUDIT dir>

The build path refuses to run when the output directory already exists, and never
writes into the E0 input directories.
"""

import argparse
import subprocess
from pathlib import Path

from w1_pipeline.e0_audit import AuditError, build_audit, verify_existing


def _git_head_or_unversioned() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
        )
        value = out.stdout.strip()
        if value:
            return value
    except FileNotFoundError:
        pass
    return "unversioned"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path)
    parser.add_argument("--candidates", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--verify-existing", type=Path)
    args = parser.parse_args()

    if args.verify_existing is not None:
        result = verify_existing(args.verify_existing)
        print(f"audit verified: {result}")
        return

    if args.plan is None or args.candidates is None or args.output_dir is None:
        parser.error("--plan, --candidates and --output-dir are required for build")

    code_snapshot = _git_head_or_unversioned()
    try:
        summary = build_audit(args.plan, args.candidates, args.output_dir, code_snapshot)
    except AuditError as exc:
        parser.error(str(exc))

    print(
        f"built audit package: {summary['contact_sheets']} contact sheets, "
        f"{summary['proxies']} proxies -> {summary['output_dir']}"
    )


if __name__ == "__main__":
    main()