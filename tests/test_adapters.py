import json

from coding_scaffold.adapters import write_route_backend, write_tool_adapter


def test_write_opencode_adapter_creates_native_files(tmp_path) -> None:
    scaffold = tmp_path / ".coding-scaffold"
    scaffold.mkdir()
    (scaffold / "routing.json").write_text(
        json.dumps({"weak_model": "qwen-small", "strong_model": "qwen-large"})
    )

    result = write_tool_adapter(tmp_path, "opencode")

    names = {path.name for path in result.files}
    assert "opencode.json" in names
    assert "reviewer.md" in names
    assert "first-session.md" in names
    assert "agentic-change.md" in names
    assert (tmp_path / ".opencode" / "agents" / "reviewer.md").exists()


def test_write_routellm_backend_creates_docs_and_config(tmp_path) -> None:
    result = write_route_backend(tmp_path, "routellm")

    names = {path.name for path in result.files}
    assert "ROUTELLM.md" in names
    assert "routellm.config.yaml" in names
