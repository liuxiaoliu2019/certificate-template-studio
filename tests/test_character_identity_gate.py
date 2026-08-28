from __future__ import annotations

import json

import pytest

from quality_gate import build_character_identity_report, build_quality_gate


FEATURES = {"hair_or_head": True, "face": True, "clothing_or_surface": True, "accessories": True, "species": True, "proportions": True}


def _files(tmp_path):
    crop = tmp_path / "hero.png"; crop.write_bytes(b"hero-source")
    candidate = tmp_path / "candidate.png"; candidate.write_bytes(b"candidate")
    return crop, candidate


@pytest.mark.parametrize("failed_feature", list(FEATURES))
def test_every_immutable_feature_can_hard_fail(tmp_path, failed_feature) -> None:
    crop, candidate = _files(tmp_path)
    features = dict(FEATURES); features[failed_feature] = False
    report = build_character_identity_report("hero", crop, candidate, 95, features)
    assert report["status"] == "hard_fail"


def test_pose_or_medium_change_is_not_an_identity_failure(tmp_path) -> None:
    crop, candidate = _files(tmp_path)
    report = build_character_identity_report("hero", crop, candidate, 90, FEATURES)
    assert report["status"] == "passed"


def test_insufficient_source_blocks_candidate(tmp_path) -> None:
    crop, candidate_path = _files(tmp_path)
    identity = build_character_identity_report("hero", crop, candidate_path, 90, FEATURES, source_sufficient=False)
    report_path = tmp_path / "identity.json"; report_path.write_text(json.dumps(identity), encoding="utf-8")
    scores = {"style_dna": 20, "certificate_style": 20, "composition": 20, "title": 15, "safe_zones": 10, "orientation_consistency": 10, "text_cleanliness": 5}
    gate = build_quality_gate("landscape", [{"candidate_id": "one", "artifact": candidate_path, "scores": scores, "used_character_ids": ["hero"], "character_identity_reports": [report_path]}], regeneration_used=True)
    assert gate["action"] == "blocked"
    assert "identity_source_insufficient" in gate["candidates"][0]["hard_failures"]


def test_candidate_without_characters_needs_no_identity_report(tmp_path) -> None:
    _, candidate_path = _files(tmp_path)
    scores = {"style_dna": 20, "certificate_style": 20, "composition": 20, "title": 15, "safe_zones": 10, "orientation_consistency": 10, "text_cleanliness": 5}
    gate = build_quality_gate("landscape", [{"candidate_id": "frame", "artifact": candidate_path, "scores": scores}])
    assert gate["action"] == "submit_best"
