import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import unittest
import tempfile
import json
from subtitle_timing_lab import core


class SubtitleTests(unittest.TestCase):
    def cue(self, i, start, end, content="text"):
        return f"{i}\n00:00:{start} --> 00:00:{end}\n{content}\n"

    def test_nested_overlap(self):
        source = (
            self.cue(1, "01,000", "09,000")
            + "\n"
            + self.cue(2, "02,000", "03,000")
            + "\n"
            + self.cue(3, "04,000", "05,000")
        )
        overlaps = [
            x for x in core.inspect(source)["findings"] if x["kind"] == "overlap"
        ]
        self.assertEqual(len(overlaps), 2)

    def test_touching_not_overlap(self):
        r = core.inspect(
            self.cue(1, "01,000", "02,000") + "\n" + self.cue(2, "02,000", "03,000")
        )
        self.assertFalse(any(x["kind"] == "overlap" for x in r["findings"]))

    def test_gap_after_union(self):
        source = (
            self.cue(1, "01,000", "09,000")
            + "\n"
            + self.cue(2, "02,000", "03,000")
            + "\n"
            + self.cue(3, "10,000", "11,000")
        )
        self.assertFalse(
            any(
                x["kind"] == "gap"
                for x in core.inspect(source, gap_ms=2000)["findings"]
            )
        )

    def test_bad_duration(self):
        self.assertTrue(
            any(
                x["kind"] == "nonpositive_duration"
                for x in core.inspect(self.cue(1, "03,000", "02,000"))["findings"]
            )
        )

    def test_order_and_duplicate(self):
        r = core.inspect(
            self.cue(2, "05,000", "06,000") + "\n" + self.cue(2, "01,000", "02,000")
        )
        self.assertTrue(
            {"duplicate_index", "out_of_order"} <= {x["kind"] for x in r["findings"]}
        )

    def test_unicode_cps(self):
        r = core.inspect(self.cue(1, "01,000", "02,000", "<i>中文</i> &amp; A"))
        self.assertEqual(r["cues"][0]["visible_codepoints"], 4)

    def test_crlf_bom(self):
        self.assertEqual(
            len(
                core.parse(
                    "\ufeff" + self.cue(1, "01,000", "02,000").replace("\n", "\r\n")
                )
            ),
            1,
        )

    def test_invalid(self):
        for value in [
            "",
            "1\nbad\nx",
            self.cue(1, "61,000", "62,000"),
            "0\n00:00:01,000 --> 00:00:02,000\nx",
        ]:
            with self.assertRaises(ValueError):
                core.parse(value)

    def test_threshold(self):
        for cps in [0, -1, float("nan"), float("inf"), 1001]:
            with self.assertRaises(ValueError):
                core.inspect(self.cue(1, "01,000", "02,000"), max_cps=cps)

    def test_text_not_executed(self):
        r = core.inspect(self.cue(1, "01,000", "02,000", "<script>example</script>"))
        self.assertEqual(r["cues"][0]["text"], "<script>example</script>")
