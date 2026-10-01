"""Strict SRT timing inspection. Never rewrite subtitle content."""

import html
import math
import re
from .common import text

TIME = r"(\d{2,3}):([0-5]\d):([0-5]\d),(\d{3})"
STAMP = re.compile("^" + TIME + r"\s+-->\s+" + TIME + "$")


def parse(source):
    source = source.lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n").strip()
    if not source:
        raise ValueError("Empty SRT")
    cues = []
    for block in re.split(r"\n[ \t]*\n", source):
        lines = block.split("\n")
        if len(lines) < 3 or not re.fullmatch(r"[1-9]\d*", lines[0].strip()):
            raise ValueError("SRT requires positive index, timestamp, text")
        matched = STAMP.fullmatch(lines[1].strip())
        if not matched:
            raise ValueError("Unsupported timestamp")
        nums = list(map(int, matched.groups()))
        ms = lambda x: ((x[0] * 60 + x[1]) * 60 + x[2]) * 1000 + x[3]
        content = "\n".join(lines[2:])
        if not content.strip():
            raise ValueError("Empty cue text")
        cues.append(
            {
                "position": len(cues) + 1,
                "index": int(lines[0]),
                "start_ms": ms(nums[:4]),
                "end_ms": ms(nums[4:]),
                "text": content,
            }
        )
        if len(cues) > 10000:
            raise ValueError("At most 10000 cues")
    return cues


def inspect(source, max_cps=20.0, gap_ms=2000):
    if (
        not math.isfinite(max_cps)
        or not 0 < max_cps <= 1000
        or type(gap_ms) is not int
        or not 0 <= gap_ms <= 600000
    ):
        raise ValueError("Invalid threshold")
    cues = parse(source)
    findings, seen = [], set()
    previous = -1
    for cue in cues:
        position, index = cue["position"], cue["index"]
        duration = cue["end_ms"] - cue["start_ms"]
        letters = sum(
            not c.isspace() for c in html.unescape(re.sub(r"<[^>]*>", "", cue["text"]))
        )
        cue.update(
            duration_ms=duration,
            visible_codepoints=letters,
            cps=round(letters * 1000 / duration, 2) if duration > 0 else None,
        )
        if index in seen:
            findings.append(
                {"kind": "duplicate_index", "cue": position, "related": index}
            )
        seen.add(index)
        if cue["start_ms"] < previous:
            findings.append({"kind": "out_of_order", "cue": position})
        previous = cue["start_ms"]
        if duration <= 0:
            findings.append({"kind": "nonpositive_duration", "cue": position})
        elif letters * 1000 / duration > max_cps:
            findings.append({"kind": "high_cps", "cue": position, "cps": cue["cps"]})
    ordered = sorted(
        (c for c in cues if c["end_ms"] > c["start_ms"]),
        key=lambda c: (c["start_ms"], c["position"]),
    )
    active = []
    union_end = None
    for cue in ordered:
        active = [other for other in active if other["end_ms"] > cue["start_ms"]]
        for other in active:
            findings.append(
                {
                    "kind": "overlap",
                    "cue": cue["position"],
                    "related_cue": other["position"],
                    "overlap_ms": min(cue["end_ms"], other["end_ms"]) - cue["start_ms"],
                }
            )
            if len(findings) > 20000:
                raise ValueError("More than 20000 findings; split input")
        if (
            union_end is not None
            and cue["start_ms"] > union_end
            and cue["start_ms"] - union_end >= gap_ms
        ):
            findings.append(
                {
                    "kind": "gap",
                    "cue": cue["position"],
                    "gap_ms": cue["start_ms"] - union_end,
                }
            )
        union_end = max(union_end or 0, cue["end_ms"])
        active.append(cue)
    if len(findings) > 20000:
        raise ValueError("More than 20000 findings; split input")
    return {
        "thresholds": {"max_cps": max_cps, "gap_ms": gap_ms},
        "cues": cues,
        "findings": findings,
        "finding_count": len(findings),
        "boundary": "Finding cue IDs refer to file position, not possibly duplicated SRT index. Overlaps include nested intervals. Touching boundaries are not overlaps. Reading speed is a configurable heuristic, not editorial judgment.",
    }


def configure(parser):
    parser.add_argument("srt", nargs="?")
    parser.add_argument("--max-cps", type=float, default=20.0)
    parser.add_argument("--gap-ms", type=int, default=2000)


def run(args):
    if not args.srt:
        raise ValueError("SRT path required")
    return inspect(text(args.srt), args.max_cps, args.gap_ms)


def demo():
    return inspect(
        "1\n00:00:01,000 --> 00:00:06,000\nSynthetic long cue\n\n2\n00:00:02,000 --> 00:00:03,000\nNested example\n\n3\n00:00:04,000 --> 00:00:04,300\nA fast synthetic subtitle\n\n4\n00:00:10,000 --> 00:00:11,000\nAfter a gap\n"
    )
