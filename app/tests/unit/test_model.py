# tests/unit/test_model.py
"""
domain/model.py のユニットテスト。
対象: WorkspaceConfig, EndpointRecord, EndpointRecord.to_log_dict()
"""
import pytest

from domain.model import EndpointRecord, WorkspaceConfig

WS_URL = "https://adb-1234567890123456.7.azuredatabricks.net"
TIMESTAMP = "2026-04-11T10:00:00+00:00"


# UT-01: WorkspaceConfig 正常生成
def test_workspace_config_normal():
    ws = WorkspaceConfig(workspace_id="1234567890123456", workspace_url=WS_URL, monitor_enabled=True)
    assert ws.workspace_id == "1234567890123456"
    assert ws.workspace_url == WS_URL
    assert ws.monitor_enabled is True


# UT-02: WorkspaceConfig monitor_enabled=False
def test_workspace_config_monitor_disabled():
    ws = WorkspaceConfig(workspace_id="x", workspace_url=WS_URL, monitor_enabled=False)
    assert ws.monitor_enabled is False


# UT-03: EndpointRecord 成功フィールド
def test_endpoint_record_success():
    rec = EndpointRecord(
        time_generated=TIMESTAMP,
        workspace_url=WS_URL,
        api_status_code=200,
        api_error_message=None,
        endpoint_name="my-endpoint",
        endpoint_state="READY",
        endpoint_raw_data={"name": "my-endpoint", "state": {"ready": "READY"}},
    )
    assert rec.api_status_code == 200
    assert rec.api_error_message is None
    assert rec.endpoint_name == "my-endpoint"
    assert rec.endpoint_state == "READY"


# UT-04: EndpointRecord 失敗フィールド（endpoint系はNone）
def test_endpoint_record_failure():
    rec = EndpointRecord(
        time_generated=TIMESTAMP,
        workspace_url=WS_URL,
        api_status_code=403,
        api_error_message="Permission denied",
        endpoint_name=None,
        endpoint_state=None,
        endpoint_raw_data=None,
    )
    assert rec.api_status_code == 403
    assert rec.api_error_message == "Permission denied"
    assert rec.endpoint_name is None
    assert rec.endpoint_state is None
    assert rec.endpoint_raw_data is None


# UT-05: to_log_dict() 成功レコード — TimeGenerated キー存在・値が正しい
def test_to_log_dict_success():
    raw = {"name": "my-endpoint", "state": {"ready": "READY"}}
    rec = EndpointRecord(
        time_generated=TIMESTAMP,
        workspace_url=WS_URL,
        api_status_code=200,
        api_error_message=None,
        endpoint_name="my-endpoint",
        endpoint_state="READY",
        endpoint_raw_data=raw,
    )
    d = rec.to_log_dict()

    assert d["TimeGenerated"] == TIMESTAMP
    assert d["workspace_url"] == WS_URL
    assert d["api_status_code"] == 200
    assert d["api_error_message"] is None
    assert d["endpoint_name"] == "my-endpoint"
    assert d["endpoint_state"] == "READY"
    assert d["endpoint_raw_data"] == raw


# UT-06: to_log_dict() 失敗レコード — endpoint 系フィールドが None
def test_to_log_dict_failure_null_fields():
    rec = EndpointRecord(
        time_generated=TIMESTAMP,
        workspace_url=WS_URL,
        api_status_code=500,
        api_error_message="Internal error",
        endpoint_name=None,
        endpoint_state=None,
        endpoint_raw_data=None,
    )
    d = rec.to_log_dict()

    assert d["api_status_code"] == 500
    assert d["api_error_message"] == "Internal error"
    assert d["endpoint_name"] is None
    assert d["endpoint_state"] is None
    assert d["endpoint_raw_data"] is None
