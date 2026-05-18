from coding_scaffold.credentials import load_local_credentials, write_local_credential_file


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
