# SRT timing review / 字幕时序

```sh
subtitle-timing-lab input.srt --max-cps 20 --gap-ms 2000 --html timing.html --json timing.json
```

Strict UTF-8 SRT: positive numeric index, `HH:MM:SS,mmm --> HH:MM:SS,mmm`, nonempty text,
blank line between cues. Supports CRLF/BOM; no timestamp settings/extensions or arbitrary encodings.
Two/three digit hours. At most 8 MiB / 10,000 cues / 20,000 findings. Heavy overlap rejects above limit.

Flags nonpositive duration, duplicate indices, start-time order inversions, all active-interval overlaps
(including nested cues), union-coverage gaps >= threshold, and CPS above threshold. Touching endpoints
are not overlap. CPS = non-whitespace Unicode code points after basic markup/entity stripping divided
by positive duration. No initial/trailing gap without video length. Nonpositive durations are excluded
from overlap/gap calculations. Findings refer to 1-based file position, not duplicate subtitle IDs.
Findings = number of diagnostic records; these are review heuristics, not automatic repair instructions.

可调阅读速度是启发式，不是语言/观众统一标准。报告保留字幕原文；分享前检查敏感信息。
不播放视频、不改稿、不自动移动字幕。对多行字幕保留换行。
