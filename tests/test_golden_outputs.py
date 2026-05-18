from pathlib import Path

from coding_scaffold.adapters import write_tool_adapter
from coding_scaffold.cli import main
from coding_scaffold.knowledge import write_knowledge_base


GOLDEN = Path(__file__).parent / "fixtures" / "golden"


def test_adapter_output_paths_match_golden(tmp_path) -> None:
    for tool in ("opencode", "claude-code", "codex"):
        write_tool_adapter(tmp_path, tool)

    paths = _file_list(tmp_path)
    assert _casefold_collisions(paths) == {}
    assert paths == _golden_lines("adapter_paths.txt")


def test_knowledge_output_paths_match_golden(tmp_path) -> None:
    write_knowledge_base(tmp_path)

    paths = _file_list(tmp_path)
    assert _casefold_collisions(paths) == {}
    assert paths == _golden_lines("knowledge_paths.txt")


def test_setup_output_paths_match_golden(tmp_path, capsys) -> None:
    assert main(["setup", "run", "--target", str(tmp_path), "--language", "python", "--non-interactive"]) == 0
    capsys.readouterr()

    generated = [
        path
        for path in _file_list(tmp_path)
        if path.startswith(".coding-scaffold/") or path.startswith(".opencode/") or path == "opencode.json"
    ]
    assert _casefold_collisions(generated) == {}
    assert generated == _golden_lines("scaffold_paths.txt")


def _file_list(root: Path) -> list[str]:
    return sorted(path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file())


def _golden_lines(name: str) -> list[str]:
    return (GOLDEN / name).read_text(encoding="utf-8").splitlines()


def _casefold_collisions(paths: list[str]) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {}
    for path in paths:
        grouped.setdefault(path.casefold(), []).append(path)
    return {key: values for key, values in grouped.items() if len(values) > 1}
