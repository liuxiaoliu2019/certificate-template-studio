from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from _common import load_json, save_json, utc_now
from schema_runtime import validate_document


COUNTERS = (
    "analysis_calls",
    "planning_calls",
    "three_concept_generations",
    "image_generation_calls",
    "visual_review_calls",
    "auto_repair_calls",
    "cache_hits",
    "cache_misses",
    "context_builds",
    "references_loaded",
    "prompt_chars",
    "image_inputs",
    "user_pauses",
    "title_derivatives",
)


def new_metrics() -> dict[str, Any]:
    now = utc_now()
    return {
        "schema_version": "1.0",
        "counters": {name: 0 for name in COUNTERS},
        "events": [],
        "updated_at": now,
    }


class MetricsRecorder:
    def __init__(self, path: Path):
        self.path = path.expanduser().resolve()
        self.data = load_json(self.path) if self.path.is_file() else new_metrics()
        validate_document(self.data, "execution_metrics.schema.json")

    def increment(
        self,
        counter: str,
        count: int = 1,
        *,
        stage: str | None = None,
        orientation: str | None = None,
        path: str | None = None,
        token_count: int | None = None,
    ) -> None:
        if counter not in COUNTERS:
            raise ValueError(f"未知执行指标：{counter}")
        if isinstance(count, bool) or not isinstance(count, int) or count < 1:
            raise ValueError("指标增量必须是正整数")
        if token_count is not None and token_count < 0:
            raise ValueError("token_count 不能为负数")
        self.data["counters"][counter] += count
        self.data["events"].append(
            {
                "counter": counter,
                "count": count,
                "stage": stage,
                "orientation": orientation,
                "path": path,
                "token_count": token_count,
                "at": utc_now(),
            }
        )
        self.data["updated_at"] = utc_now()
        validate_document(self.data, "execution_metrics.schema.json")
        save_json(self.path, self.data)

    def assert_auto_repair_available(self, orientation: str) -> None:
        used = sum(
            event["count"]
            for event in self.data["events"]
            if event["counter"] == "auto_repair_calls" and event["orientation"] == orientation
        )
        if used >= 1:
            raise ValueError(f"{orientation} 已使用一次自动修正，必须暂停并请用户决定")


def main() -> int:
    parser = argparse.ArgumentParser(description="记录工作流计数，不保存用户内容。")
    parser.add_argument("metrics", type=Path)
    parser.add_argument("--counter", required=True, choices=COUNTERS)
    parser.add_argument("--count", type=int, default=1)
    parser.add_argument("--stage")
    parser.add_argument("--orientation", choices=["landscape", "portrait"])
    parser.add_argument("--path")
    parser.add_argument("--token-count", type=int)
    args = parser.parse_args()
    recorder = MetricsRecorder(args.metrics)
    if args.counter == "auto_repair_calls" and args.orientation:
        recorder.assert_auto_repair_available(args.orientation)
    recorder.increment(
        args.counter,
        args.count,
        stage=args.stage,
        orientation=args.orientation,
        path=args.path,
        token_count=args.token_count,
    )
    print(args.metrics.expanduser().resolve())
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"错误：{exc}")
        raise SystemExit(1)
