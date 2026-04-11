# tests/unit/test_config.py
"""
config.py のユニットテスト。
対象: Config.from_env()
"""
import pytest

from config import Config

VALID_WORKSPACE_LIST = (
    '[{"workspace_id":"1234567890123456",'
    '"workspace_url":"https://adb-1234567890123456.7.azuredatabricks.net",'
    '"monitor_enabled":true}]'
)


def _set_all_env(monkeypatch, workspace_list=VALID_WORKSPACE_LIST):
    monkeypatch.setenv("WORKSPACE_LIST", workspace_list)
    monkeypatch.setenv("DCE_ENDPOINT", "https://dce-example.eastus-1.ingest.monitor.azure.com")
    monkeypatch.setenv("DCR_IMMUTABLE_ID", "dcr-abc123")
    monkeypatch.setenv("DCR_STREAM_NAME", "Custom-AppLogs")


# UT-07: 全環境変数が正しく設定されている場合
def test_from_env_normal(monkeypatch):
    _set_all_env(monkeypatch)
    config = Config.from_env()

    assert len(config.workspace_list) == 1
    assert config.workspace_list[0].workspace_id == "1234567890123456"
    assert config.workspace_list[0].workspace_url == "https://adb-1234567890123456.7.azuredatabricks.net"
    assert config.workspace_list[0].monitor_enabled is True
    assert config.dce_endpoint == "https://dce-example.eastus-1.ingest.monitor.azure.com"
    assert config.dcr_immutable_id == "dcr-abc123"
    assert config.dcr_stream_name == "Custom-AppLogs"


# UT-08: DCE_ENDPOINT が未設定
def test_from_env_missing_dce_endpoint(monkeypatch):
    _set_all_env(monkeypatch)
    monkeypatch.delenv("DCE_ENDPOINT")

    with pytest.raises(ValueError, match="DCE_ENDPOINT"):
        Config.from_env()


# UT-09: WORKSPACE_LIST が不正な JSON
def test_from_env_invalid_json(monkeypatch):
    _set_all_env(monkeypatch, workspace_list="not-valid-json")

    with pytest.raises(ValueError, match="不正な JSON"):
        Config.from_env()


# UT-10: WORKSPACE_LIST が空配列
def test_from_env_empty_workspace_list(monkeypatch):
    _set_all_env(monkeypatch, workspace_list="[]")
    config = Config.from_env()

    assert config.workspace_list == []


# UT-extra: WORKSPACE_LIST の要素に必須フィールドが欠落
def test_from_env_workspace_missing_field(monkeypatch):
    _set_all_env(monkeypatch, workspace_list='[{"workspace_id":"1"}]')

    with pytest.raises(ValueError, match="必須フィールドがありません"):
        Config.from_env()


# UT-extra: WORKSPACE_LIST が配列でない
def test_from_env_workspace_list_not_array(monkeypatch):
    _set_all_env(monkeypatch, workspace_list='{"workspace_id":"1"}')

    with pytest.raises(ValueError, match="JSON 配列"):
        Config.from_env()
