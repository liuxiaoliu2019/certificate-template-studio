from __future__ import annotations

import pytest

from metrics import MetricsRecorder


def test_cache_and_call_counts_are_exact(tmp_path) -> None:
    recorder = MetricsRecorder(tmp_path / "metrics.json")
    recorder.increment("analysis_calls")
    recorder.increment("cache_hits", 2, stage="analysis")
    assert recorder.data["counters"]["analysis_calls"] == 1
    assert recorder.data["counters"]["cache_hits"] == 2


def test_auto_repair_limit_is_per_orientation(tmp_path) -> None:
    recorder = MetricsRecorder(tmp_path / "metrics.json")
    recorder.assert_auto_repair_available("landscape")
    recorder.increment("auto_repair_calls", orientation="landscape")
    with pytest.raises(ValueError, match="必须暂停"):
        recorder.assert_auto_repair_available("landscape")
    recorder.assert_auto_repair_available("portrait")


def test_title_derivative_does_not_increment_analysis_or_three_concepts(tmp_path) -> None:
    recorder = MetricsRecorder(tmp_path / "metrics.json")
    recorder.increment("title_derivatives")
    assert recorder.data["counters"]["title_derivatives"] == 1
    assert recorder.data["counters"]["analysis_calls"] == 0
    assert recorder.data["counters"]["three_concept_generations"] == 0


def test_optional_token_count_can_be_absent(tmp_path) -> None:
    recorder = MetricsRecorder(tmp_path / "metrics.json")
    recorder.increment("planning_calls", stage="planning")
    assert recorder.data["events"][-1]["token_count"] is None
