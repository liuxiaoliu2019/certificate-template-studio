from __future__ import annotations

from quality_gate import build_quality_gate, user_summary


def _candidate(tmp_path, candidate_id, total, hard=False):
    path = tmp_path / f"{candidate_id}.png"
    path.write_bytes(candidate_id.encode())
    scores = {
        "style_dna": 20,
        "certificate_style": 20,
        "composition": 20,
        "title": 15,
        "safe_zones": 10,
        "orientation_consistency": 10,
        "text_cleanliness": 5,
    }
    remaining = 100 - total
    for key in scores:
        deduction = min(scores[key], remaining)
        scores[key] -= deduction
        remaining -= deduction
        if remaining == 0:
            break
    return {"candidate_id": candidate_id, "artifact": path, "scores": scores, "hard_failures": ["identity_hard_fail"] if hard else []}


def test_qualified_best_skips_lower_candidate_repair(tmp_path) -> None:
    report = build_quality_gate("landscape", [_candidate(tmp_path, "one", 91), _candidate(tmp_path, "two", 80)])
    assert report["action"] == "submit_best"
    assert report["default_visible_candidate_ids"] == ["one"]


def test_75_to_84_repairs_only_best_once(tmp_path) -> None:
    report = build_quality_gate("landscape", [_candidate(tmp_path, "one", 82), _candidate(tmp_path, "two", 78)])
    assert report["action"] == "repair_best"
    assert report["selected_candidate_id"] == "one"
    blocked = build_quality_gate("landscape", [_candidate(tmp_path, "one", 82)], repair_used=True, regeneration_used=True)
    assert blocked["action"] == "blocked"


def test_all_low_regenerates_best_direction_once(tmp_path) -> None:
    report = build_quality_gate("landscape", [_candidate(tmp_path, "one", 70), _candidate(tmp_path, "two", 68)])
    assert report["action"] == "regenerate_best"
    assert report["selected_candidate_id"] == "one"


def test_hard_failure_never_wins_by_score(tmp_path) -> None:
    report = build_quality_gate("landscape", [_candidate(tmp_path, "bad", 99, hard=True), _candidate(tmp_path, "good", 88)])
    assert report["selected_candidate_id"] == "good"


def test_default_summary_hides_internal_analysis(tmp_path) -> None:
    report = build_quality_gate("landscape", [_candidate(tmp_path, "best", 90), _candidate(tmp_path, "other", 87)])
    summary = user_summary(report)
    assert "best" in summary
    assert "scores" not in summary
    assert "other" not in summary
    assert report["other_qualified_candidate_ids"] == ["other"]
