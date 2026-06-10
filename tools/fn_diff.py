#!/usr/bin/env python3
"""One-shot function diff viewer using objdiff-cli JSON output.

Usage: python3 tools/fn_diff.py <unit> <symbol> [--context N] [--all]
Prints side-by-side target/base instruction rows around mismatches.
"""
import argparse
import json
import subprocess
import sys
import tempfile

OBJDIFF = "build/tools/objdiff-cli"


def insn_text(row):
    ins = row.get("instruction")
    if ins is None:
        return ""
    text = ins.get("formatted", "")
    if "branch_dest" in ins:
        text += f" -> {int(ins['branch_dest']):#x}"
    return text


def get_fn(side, symbol):
    for fn in side.get("symbols", []):
        if fn.get("name") == symbol:
            return fn
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("unit")
    ap.add_argument("symbol")
    ap.add_argument("--context", type=int, default=3)
    ap.add_argument("--all", action="store_true", help="print all rows")
    args = ap.parse_args()

    unit = args.unit
    if not unit.startswith("main/"):
        unit = "main/" + unit

    with tempfile.NamedTemporaryFile(suffix=".json") as tf:
        subprocess.run(
            [OBJDIFF, "-L", "error", "diff", "-p", ".", "-u", unit,
             "-o", tf.name, "--format", "json", args.symbol],
            check=True,
        )
        d = json.load(open(tf.name))

    left = get_fn(d.get("left", {}), args.symbol)
    right = get_fn(d.get("right", {}), args.symbol)
    if left is None or right is None:
        print("symbol not found in diff output", file=sys.stderr)
        sys.exit(1)

    print(f"match: {left.get('match_percent')}")
    lrows = left.get("instructions", [])
    rrows = right.get("instructions", [])
    n = max(len(lrows), len(rrows))
    marks = []
    for i in range(n):
        li = lrows[i] if i < len(lrows) else {}
        ri = rrows[i] if i < len(rrows) else {}
        ld = li.get("diff_kind", "DIFF_NONE")
        rd = ri.get("diff_kind", "DIFF_NONE")
        marks.append(ld != "DIFF_NONE" or rd != "DIFF_NONE")

    show = set()
    for i, m in enumerate(marks):
        if m or args.all:
            for j in range(max(0, i - args.context), min(n, i + args.context + 1)):
                show.add(j)

    last = None
    for i in sorted(show):
        if last is not None and i != last + 1:
            print("...")
        last = i
        li = lrows[i] if i < len(lrows) else {}
        ri = rrows[i] if i < len(rrows) else {}
        lt = insn_text(li)
        rt = insn_text(ri)
        mark = ">" if marks[i] else " "
        print(f"{mark} {i*4:6x} | {lt:60s} | {rt}")


if __name__ == "__main__":
    main()
