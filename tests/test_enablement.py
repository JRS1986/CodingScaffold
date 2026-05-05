import json

from coding_scaffold.enablement import write_orchestration_plan, write_skill_template


def test_write_skill_template_slugifies_name(tmp_path) -> None:
    path = write_skill_template(tmp_path, "Release Review!", "Check a release candidate.")

    assert path.name == "release-review.md"
    assert "Check a release candidate." in path.read_text()


def test_write_orchestration_plan_uses_profile(tmp_path) -> None:
    path = write_orchestration_plan(tmp_path, "team")

    payload = json.loads(path.read_text())
    assert payload["profile"] == "team"
    assert [agent["name"] for agent in payload["agents"]] == [
        "Explorer",
        "Planner",
        "Implementer",
        "Verifier",
    ]
