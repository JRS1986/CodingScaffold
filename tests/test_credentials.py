from coding_scaffold.credentials import (
    load_local_credentials,
    scaffold_dir,
    write_local_credential_file,
)


def test_write_and_load_local_env_credentials(tmp_path) -> None:
    path = write_local_credential_file(tmp_path, "env")
    path.write_text("OPENAI_API_KEY=test-value\nANTHROPIC_API_KEY=\n")

    values = load_local_credentials(tmp_path)

    assert values == {"OPENAI_API_KEY": "test-value"}


def test_write_and_load_local_json_credentials(tmp_path) -> None:
    path = write_local_credential_file(tmp_path, "json")
    path.write_text('{"OPENROUTER_API_KEY": "router-value", "GROQ_API_KEY": ""}\n')

    values = load_local_credentials(tmp_path)

    assert values == {"OPENROUTER_API_KEY": "router-value"}


def _write_env(tmp_path, contents: str):
    directory = scaffold_dir(tmp_path)
    directory.mkdir(parents=True, exist_ok=True)
    env_path = directory / ".env.local"
    env_path.write_text(contents, encoding="utf-8")
    return env_path


def test_env_parser_handles_export_prefix(tmp_path) -> None:
    _write_env(tmp_path, "export OPENAI_API_KEY=val\n")
    assert load_local_credentials(tmp_path) == {"OPENAI_API_KEY": "val"}


def test_env_parser_strips_trailing_comment(tmp_path) -> None:
    _write_env(tmp_path, "OPENAI_API_KEY=sk-abc # trailing comment\n")
    assert load_local_credentials(tmp_path) == {"OPENAI_API_KEY": "sk-abc"}


def test_env_parser_double_quoted_preserves_hash_and_spaces(tmp_path) -> None:
    _write_env(tmp_path, 'OPENAI_API_KEY="value with spaces and # hash"\n')
    assert load_local_credentials(tmp_path) == {
        "OPENAI_API_KEY": "value with spaces and # hash"
    }


def test_env_parser_single_quoted_preserves_inner_double_quote(tmp_path) -> None:
    _write_env(tmp_path, "OPENAI_API_KEY='abc\"def'\n")
    assert load_local_credentials(tmp_path) == {"OPENAI_API_KEY": 'abc"def'}


def test_env_parser_double_quoted_preserves_inner_single_quote(tmp_path) -> None:
    _write_env(tmp_path, 'OPENAI_API_KEY="abc\'def"\n')
    assert load_local_credentials(tmp_path) == {"OPENAI_API_KEY": "abc'def"}


def test_env_parser_empty_value_is_dropped_after_filter(tmp_path) -> None:
    # load_local_credentials filters empty values; verify it's parsed as empty (no crash).
    _write_env(tmp_path, "OPENAI_API_KEY=\nANTHROPIC_API_KEY=set\n")
    assert load_local_credentials(tmp_path) == {"ANTHROPIC_API_KEY": "set"}


def test_env_parser_skips_malformed_and_blank_lines(tmp_path) -> None:
    _write_env(
        tmp_path,
        "\n"
        "   \n"
        "# only a comment\n"
        "MALFORMED_NO_EQUALS\n"
        "OPENAI_API_KEY=ok\n",
    )
    assert load_local_credentials(tmp_path) == {"OPENAI_API_KEY": "ok"}


def test_secret_env_names_separates_keys_from_azure_config():
    from coding_scaffold.credentials import (
        AZURE_NONKEY_ENV_NAMES,
        SECRET_ENV_NAMES,
        SECRET_KEY_ENV_NAMES,
    )

    assert "OPENAI_API_KEY" in SECRET_KEY_ENV_NAMES
    assert "AZURE_OPENAI_ENDPOINT" in AZURE_NONKEY_ENV_NAMES
    assert "AZURE_OPENAI_ENDPOINT" not in SECRET_KEY_ENV_NAMES
    # Backwards-compat: the union is still importable under the old name.
    assert set(SECRET_KEY_ENV_NAMES) <= set(SECRET_ENV_NAMES)
    assert set(AZURE_NONKEY_ENV_NAMES) <= set(SECRET_ENV_NAMES)
