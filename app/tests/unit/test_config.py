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


# UT-31: WORKSPACE_LIST が未設定 → ValueError
def test_from_env_missing_workspace_list(monkeypatch):
    _set_all_env(monkeypatch)
    monkeypatch.delenv("WORKSPACE_LIST")

    with pytest.raises(ValueError, match="WORKSPACE_LIST"):
        Config.from_env()


# UT-32: DCR_IMMUTABLE_ID が未設定 → ValueError
def test_from_env_missing_dcr_immutable_id(monkeypatch):
    _set_all_env(monkeypatch)
    monkeypatch.delenv("DCR_IMMUTABLE_ID")

    with pytest.raises(ValueError, match="DCR_IMMUTABLE_ID"):
        Config.from_env()


# UT-33: DCR_STREAM_NAME が未設定 → ValueError
def test_from_env_missing_dcr_stream_name(monkeypatch):
    _set_all_env(monkeypatch)
    monkeypatch.delenv("DCR_STREAM_NAME")

    with pytest.raises(ValueError, match="DCR_STREAM_NAME"):
        Config.from_env()


# UT-34: WORKSPACE_LIST 要素に workspace_id が欠落 → ValueError
def test_from_env_workspace_missing_workspace_id(monkeypatch):
    _set_all_env(
        monkeypatch,
        workspace_list='[{"workspace_url":"https://adb-1.azuredatabricks.net","monitor_enabled":true}]',
    )

    with pytest.raises(ValueError, match="必須フィールドがありません"):
        Config.from_env()


# UT-35: WORKSPACE_LIST 要素に monitor_enabled が欠落 → ValueError
def test_from_env_workspace_missing_monitor_enabled(monkeypatch):
    _set_all_env(
        monkeypatch,
        workspace_list='[{"workspace_id":"1","workspace_url":"https://adb-1.azuredatabricks.net"}]',
    )

    with pytest.raises(ValueError, match="必須フィールドがありません"):
        Config.from_env()


# UT-43: WORKSPACE_LIST 要素に workspace_url が欠落 → ValueError
def test_from_env_workspace_missing_workspace_url(monkeypatch):
    _set_all_env(
        monkeypatch,
        workspace_list='[{"workspace_id":"1","monitor_enabled":true}]',
    )

    with pytest.raises(ValueError, match="必須フィールドがありません"):
        Config.from_env()


# UT-44: WORKSPACE_LIST が2件 → 両方のワークスペースが正しく読み込まれる
def test_from_env_multiple_workspaces(monkeypatch):
    workspace_list = (
        '[{"workspace_id":"ws1","workspace_url":"https://adb-1.azuredatabricks.net","monitor_enabled":true},'
        '{"workspace_id":"ws2","workspace_url":"https://adb-2.azuredatabricks.net","monitor_enabled":false}]'
    )
    _set_all_env(monkeypatch, workspace_list=workspace_list)
    config = Config.from_env()

    assert len(config.workspace_list) == 2
    assert config.workspace_list[0].workspace_id == "ws1"
    assert config.workspace_list[0].monitor_enabled is True
    assert config.workspace_list[1].workspace_id == "ws2"
    assert config.workspace_list[1].monitor_enabled is False
