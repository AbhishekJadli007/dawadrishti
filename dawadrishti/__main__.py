"""DawaDrishti command line.

  python -m dawadrishti fetch       # download CDSCO alerts (portal JSON + PDFs)        [real data, needs internet]
  python -m dawadrishti build       # stage -> ERP history -> warehouse -> mining -> risk -> study -> evaluations
  python -m dawadrishti check S000  # national check for a supplier
  python -m dawadrishti ask "Which states make the most failing drugs?"
"""
from __future__ import annotations

import argparse
import json
import time


def build():
    from . import entity_eval, study, warehouse
    from .erp import service, simulate
    from .etl import audit, stage
    from .mining import conformance, patterns, process, risk
    steps = [("ETL: stage + clean + entity resolution", stage.main), ("ERP: simulate 20 months for 5 buyers", simulate.main),
             ("Warehouse: star schema", warehouse.main), ("Process mining", process.main), ("Conformance engine cross-check", lambda: conformance.main([])), ("Data mining", patterns.main),
             ("Risk models", risk.main), ("Live ERP seed", lambda: print("  seeded", service.seed_live(), "open batches")),
             ("Headline study: repeat failures in the national record", study.main),
             ("Entity-resolution evaluation", entity_eval.main), ("Extraction audit: PDF vs portal", audit.main)]
    for name, fn in steps:
        t = time.time()
        print(f"== {name}")
        fn()
        print(f"   ({time.time() - t:.0f}s)")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="dawadrishti")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("fetch")
    sub.add_parser("build")
    p = sub.add_parser("check")
    p.add_argument("supplier_id")
    p = sub.add_parser("ask")
    p.add_argument("question")
    a = ap.parse_args(argv)
    if a.cmd == "fetch":
        from .etl import crawl, portal
        portal.main()
        crawl.main()
    elif a.cmd == "build":
        build()
    elif a.cmd == "check":
        from .erp.service import national_check
        print(json.dumps(national_check(a.supplier_id), indent=2, default=str))
    elif a.cmd == "ask":
        from .ai.ask import ask
        r = ask(a.question)
        print(r["sql"])
        print(r["columns"])
        for row in r["rows"][:20]:
            print(row)


if __name__ == "__main__":
    main()
