from __future__ import annotations

from start_router import MODE_MENU, route_start


def test_generic_start_returns_fixed_menu() -> None:
    result = route_start("使用 $certificate-template-studio 开始工作")
    assert result == {"action": "menu", "selected_mode": None, "message": MODE_MENU}


def test_explicit_textbook_mode_skips_menu() -> None:
    result = route_start("模式 1，用教材封面生成证书")
    assert result == {"action": "start", "selected_mode": "textbook_cover"}


def test_explicit_template_mode_skips_menu() -> None:
    result = route_start("把这个横版模板转换成横竖版")
    assert result == {"action": "start", "selected_mode": "template_bidirectional"}


def test_ambiguous_message_returns_menu() -> None:
    result = route_start("可以用教材封面，也可以用模板转换")
    assert result["action"] == "menu"


def test_existing_project_resumes_without_menu() -> None:
    result = route_start(
        "继续",
        {
            "selected_mode": "textbook_cover",
            "workflow": {"stage": "awaiting_landscape_approval"},
        },
    )
    assert result == {
        "action": "resume",
        "selected_mode": "textbook_cover",
        "stage": "awaiting_landscape_approval",
    }
