"""Command line: talk to your companion in the terminal before the hardware exists.

    export ANTHROPIC_API_KEY=...          (or: ant auth login)
    python -m suflet_ai birth --device demo --seed 0xC0FFEE --owner Andu
    python -m suflet_ai chat  --device demo
    python -m suflet_ai diary --device demo --events examples/events_day.jsonl
"""
from __future__ import annotations

import argparse
import json
import sys

from .companion import Companion
from .llm import LlmError


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="suflet_ai")
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("birth")
    b.add_argument("--device", required=True)
    b.add_argument("--seed", required=True)
    b.add_argument("--owner", default="")
    b.add_argument("--language", default="ro")
    b.add_argument("--traits", default='{"archetype":"Șmecherul","eyes":"Cream","rarity":"Common"}')
    c = sub.add_parser("chat")
    c.add_argument("--device", required=True)
    d = sub.add_parser("diary")
    d.add_argument("--device", required=True)
    d.add_argument("--events", help="JSON-lines file of device events to log first")
    d.add_argument("--day")
    a = ap.parse_args(argv)

    comp = Companion()
    try:
        if a.cmd == "birth":
            p = comp.birth(a.device, a.seed, json.loads(a.traits), a.owner, a.language)
            print(json.dumps(p.model_dump(), ensure_ascii=False, indent=2))
        elif a.cmd == "chat":
            print("(Ctrl-D to quit)")
            for line in sys.stdin:
                if not line.strip():
                    continue
                r = comp.turn(a.device, line)
                print(f"  [{r.tone}{'/' + r.reaction if r.reaction != 'none' else ''}] {r.say}")
                for rem in r.reminders:
                    print(f"  ⏰ {rem.at}  {rem.text}")
                for n in r.notes:
                    print(f"  📝 {n}")
                for f in r.remember:
                    print(f"  💾 {f}")
        elif a.cmd == "diary":
            if a.events:
                with open(a.events, encoding="utf-8") as f:
                    comp.log_events(a.device, [json.loads(x) for x in f if x.strip()])
            e = comp.diary(a.device, a.day)
            print(json.dumps(e.model_dump(), ensure_ascii=False, indent=2))
    except LlmError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
