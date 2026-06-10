#!/usr/bin/env python3
"""Triage near-match functions by diff type."""
import json
import re
import subprocess
import sys
import tempfile

OBJDIFF = "build/tools/objdiff-cli"


def insn_text(row):
    ins = row.get("instruction")
    return ins.get("formatted", "") if ins else ""


def classify(unit, symbol):
    with tempfile.NamedTemporaryFile(suffix=".json") as tf:
        r = subprocess.run(
            [OBJDIFF, "-L", "error", "diff", "-p", ".", "-u", unit,
             "-o", tf.name, "--format", "json", symbol],
            capture_output=True,
        )
        if r.returncode != 0:
            return ("error", 0)
        d = json.load(open(tf.name))

    def get_fn(side):
        for fn in d.get(side, {}).get("symbols", []):
            if fn.get("name") == symbol:
                return fn
        return None

    l, r_ = get_fn("left"), get_fn("right")
    if not l or not r_:
        return ("missing", 0)

    kinds = set()
    n = 0
    li, ri = l.get("instructions", []), r_.get("instructions", [])
    for i in range(max(len(li), len(ri))):
        a = li[i] if i < len(li) else {}
        b = ri[i] if i < len(ri) else {}
        if a.get("diff_kind") is None and b.get("diff_kind") is None:
            continue
        n += 1
        ta, tb = insn_text(a), insn_text(b)
        if not ta or not tb:
            kinds.add("insn")
        elif ta == tb:
            kinds.add("reloc")
        else:
            # same mnemonic, different args?
            ma, mb = ta.split()[0], tb.split()[0]
            if ma != mb:
                kinds.add("insn")
            elif re.search(r"r1, 0x[0-9a-f]+", ta) or re.search(r"\(r1\)", ta):
                kinds.add("stack")
            elif "@sda21" in ta or "@ha" in ta or "@l" in ta:
                kinds.add("reloc")
            else:
                kinds.add("regalloc" if re.sub(r"r\d+", "rX", ta) == re.sub(r"r\d+", "rX", tb) else "args")
    return ("+".join(sorted(kinds)) or "none", n)


def main():
    cands = json.load(open(sys.argv[1]))
    for m, size, unit, name in cands:
        kind, n = classify(unit, name)
        print(f"{m:7.3f} {size:5d} {n:3d} {kind:24s} {unit:46s} {name}", flush=True)


if __name__ == "__main__":
    main()
