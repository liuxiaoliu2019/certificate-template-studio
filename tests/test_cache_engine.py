from __future__ import annotations

from cache_engine import CacheEngine, build_source_fingerprint


def _project(tmp_path):
    project = tmp_path / "project"
    for directory in ("input", "controls", "analysis", "configs", "selected"):
        (project / directory).mkdir(parents=True, exist_ok=True)
    (project / "input/cover.png").write_bytes(b"cover-v1")
    (project / "controls/landscape_v3.png").write_bytes(b"landscape-control")
    (project / "controls/portrait_v3.png").write_bytes(b"portrait-control")
    return project


def test_same_inputs_hit_cache(tmp_path) -> None:
    project = _project(tmp_path)
    artifact = project / "analysis/style.json"
    artifact.write_text("{}", encoding="utf-8")
    engine = CacheEngine(project)
    inputs = {"source": "abc", "prompt": "v1"}
    engine.record("analysis", inputs, ["analysis/style.json"])
    assert engine.lookup("analysis", inputs) is not None
    assert engine.lookup("analysis", {"source": "changed"}) is None


def test_title_change_keeps_analysis_and_candidates(tmp_path) -> None:
    project = _project(tmp_path)
    engine = CacheEngine(project)
    for stage, relative in (
        ("analysis", "analysis/a.json"),
        ("landscape_candidates", "selected/candidate.png"),
        ("title_plan", "analysis/title.json"),
        ("title_render", "selected/master.png"),
    ):
        path = project / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(stage.encode())
        engine.record(stage, {"stage": stage}, [relative])
    engine.invalidate_change("title")
    assert "analysis" in engine.state["entries"]
    assert "landscape_candidates" in engine.state["entries"]
    assert "title_plan" not in engine.state["entries"]
    assert "title_render" not in engine.state["entries"]


def test_source_change_invalidates_every_stage(tmp_path) -> None:
    project = _project(tmp_path)
    artifact = project / "analysis/a.json"
    artifact.write_text("{}", encoding="utf-8")
    engine = CacheEngine(project)
    engine.record("analysis", {"source": "old"}, ["analysis/a.json"])
    engine.invalidate_change("source")
    assert engine.state["entries"] == {}


def test_control_change_is_orientation_scoped(tmp_path) -> None:
    project = _project(tmp_path)
    engine = CacheEngine(project)
    for stage in ("analysis", "master_landscape", "master_portrait"):
        relative = f"analysis/{stage}.json"
        (project / relative).write_text("{}", encoding="utf-8")
        engine.record(stage, {"stage": stage}, [relative])
    engine.invalidate_change("control", orientation="portrait")
    assert "analysis" in engine.state["entries"]
    assert "master_landscape" in engine.state["entries"]
    assert "master_portrait" not in engine.state["entries"]


def test_fingerprint_records_source_and_control_hashes(tmp_path) -> None:
    project = _project(tmp_path)
    first = build_source_fingerprint(project, mode="textbook_cover", source="input/cover.png")
    second = build_source_fingerprint(project, mode="textbook_cover", source="input/cover.png")
    assert first["source"]["sha256"] == second["source"]["sha256"]
    assert first["controls"]["landscape"]["sha256"]


def test_unused_character_change_does_not_invalidate(tmp_path) -> None:
    project = _project(tmp_path)
    engine = CacheEngine(project)
    assert engine.invalidate_change(
        "character", character_id="unused", character_usage={"unused": []}
    ) == []
