# tests/unit/test_service.py
"""
domain/service.py のユニットテスト。
対象: EndpointMonitorService.run(), _process_workspace()
"""
from unittest.mock import MagicMock

import pytest

from domain.model import WorkspaceConfig
from domain.service import EndpointMonitorService


def _make_ws(url="https://adb-1.azuredatabricks.net", monitor_enabled=True):
    return WorkspaceConfig(workspace_id="1", workspace_url=url, monitor_enabled=monitor_enabled)


def _make_ep_dict(name="ep1", state="READY"):
    return {"name": name, "state": {"ready": state}}


# UT-11: 正常 — モックが 2 件のエンドポイントを返す
def test_run_normal_2_endpoints():
    mock_port = MagicMock()
    mock_port.fetch_endpoints.return_value = [_make_ep_dict("ep1"), _make_ep_dict("ep2")]

    service = EndpointMonitorService(endpoint_port=mock_port)
    records = service.run([_make_ws()])

    assert len(records) == 2
    assert all(r.api_status_code == 200 for r in records)
    assert records[0].endpoint_name == "ep1"
    assert records[1].endpoint_name == "ep2"
    assert all(r.api_error_message is None for r in records)


# UT-12: 異常 — モックが例外を発生 → エラーレコード 1 件・処理継続
def test_run_workspace_exception_returns_error_record():
    mock_port = MagicMock()
    mock_port.fetch_endpoints.side_effect = Exception("connection timeout")

    service = EndpointMonitorService(endpoint_port=mock_port)
    records = service.run([_make_ws()])

    assert len(records) == 1
    assert records[0].api_status_code == 0
    assert "connection timeout" in records[0].api_error_message
    assert records[0].endpoint_name is None
    assert records[0].endpoint_state is None
    assert records[0].endpoint_raw_data is None


# UT-13: 正常 — monitor_enabled=False のワークスペースはスキップ
def test_run_skips_disabled_workspace():
    mock_port = MagicMock()
    service = EndpointMonitorService(endpoint_port=mock_port)
    records = service.run([_make_ws(monitor_enabled=False)])

    mock_port.fetch_endpoints.assert_not_called()
    assert records == []


# UT-14: 正常 — 2 ワークスペース・各 2 エンドポイント → 計 4 件
def test_run_2_workspaces_4_records():
    mock_port = MagicMock()
    mock_port.fetch_endpoints.return_value = [_make_ep_dict("ep1"), _make_ep_dict("ep2")]

    ws1 = WorkspaceConfig("1", "https://adb-1.azuredatabricks.net", True)
    ws2 = WorkspaceConfig("2", "https://adb-2.azuredatabricks.net", True)
    service = EndpointMonitorService(endpoint_port=mock_port)
    records = service.run([ws1, ws2])

    assert len(records) == 4
    assert mock_port.fetch_endpoints.call_count == 2


# UT-15: 異常 — WS1 失敗・WS2 成功 → エラー 1 件 + 正常 1 件
def test_run_partial_failure_continues():
    mock_port = MagicMock()
    mock_port.fetch_endpoints.side_effect = [
        Exception("auth error"),
        [_make_ep_dict("ep1")],
    ]

    ws1 = WorkspaceConfig("1", "https://adb-1.azuredatabricks.net", True)
    ws2 = WorkspaceConfig("2", "https://adb-2.azuredatabricks.net", True)
    service = EndpointMonitorService(endpoint_port=mock_port)
    records = service.run([ws1, ws2])

    assert len(records) == 2
    error_records = [r for r in records if r.api_status_code != 200]
    success_records = [r for r in records if r.api_status_code == 200]
    assert len(error_records) == 1
    assert len(success_records) == 1


# UT-extra: エンドポイントが 0 件のワークスペース → レコードなし
def test_run_zero_endpoints():
    mock_port = MagicMock()
    mock_port.fetch_endpoints.return_value = []

    service = EndpointMonitorService(endpoint_port=mock_port)
    records = service.run([_make_ws()])

    assert records == []


# UT-extra: workspace_url がレコードに正しく記録される
def test_run_workspace_url_in_record():
    mock_port = MagicMock()
    mock_port.fetch_endpoints.return_value = [_make_ep_dict()]

    ws = _make_ws(url="https://adb-9999.azuredatabricks.net")
    service = EndpointMonitorService(endpoint_port=mock_port)
    records = service.run([ws])

    assert records[0].workspace_url == "https://adb-9999.azuredatabricks.net"


# UT-extra: NOT_READY 状態のエンドポイントも正常レコードとして記録
def test_run_not_ready_endpoint():
    mock_port = MagicMock()
    mock_port.fetch_endpoints.return_value = [_make_ep_dict("ep1", "NOT_READY")]

    service = EndpointMonitorService(endpoint_port=mock_port)
    records = service.run([_make_ws()])

    assert records[0].api_status_code == 200
    assert records[0].endpoint_state == "NOT_READY"


# UT-25: workspace_id が成功レコードに正しく記録される
def test_run_workspace_id_in_success_record():
    mock_port = MagicMock()
    mock_port.fetch_endpoints.return_value = [_make_ep_dict()]

    ws = WorkspaceConfig("ws-id-9999", "https://adb-9999.azuredatabricks.net", True)
    service = EndpointMonitorService(endpoint_port=mock_port)
    records = service.run([ws])

    assert records[0].workspace_id == "ws-id-9999"


# UT-26: workspace_id が例外時（エラーレコード）にも記録される
def test_run_workspace_id_in_error_record():
    mock_port = MagicMock()
    mock_port.fetch_endpoints.side_effect = Exception("network error")

    ws = WorkspaceConfig("ws-id-error", "https://adb-error.azuredatabricks.net", True)
    service = EndpointMonitorService(endpoint_port=mock_port)
    records = service.run([ws])

    assert records[0].workspace_id == "ws-id-error"


# UT-27: status_code 属性を持つ例外 → api_status_code にそのコードが記録される
def test_run_error_record_uses_exception_status_code():
    mock_port = MagicMock()
    exc = Exception("permission denied")
    exc.status_code = 403
    mock_port.fetch_endpoints.side_effect = exc

    service = EndpointMonitorService(endpoint_port=mock_port)
    records = service.run([_make_ws()])

    assert records[0].api_status_code == 403


# UT-28: status_code 属性を持たない例外 → api_status_code=0 になる
def test_run_error_record_status_code_defaults_to_zero():
    mock_port = MagicMock()
    mock_port.fetch_endpoints.side_effect = ConnectionError("timeout")

    service = EndpointMonitorService(endpoint_port=mock_port)
    records = service.run([_make_ws()])

    assert records[0].api_status_code == 0


# UT-36: workspace_list が空リストのとき空リストを返す
def test_run_empty_workspace_list():
    mock_port = MagicMock()
    service = EndpointMonitorService(endpoint_port=mock_port)
    records = service.run([])

    assert records == []
    mock_port.fetch_endpoints.assert_not_called()


# UT-37: api_error_message が str(e) に変換されている
def test_run_error_message_is_stringified():
    mock_port = MagicMock()
    mock_port.fetch_endpoints.side_effect = RuntimeError("detailed error info")

    service = EndpointMonitorService(endpoint_port=mock_port)
    records = service.run([_make_ws()])

    assert records[0].api_error_message == "detailed error info"


# UT-38: time_generated が UTC ISO8601 形式（+00:00 を含む）になっている
def test_run_time_generated_is_utc_iso8601():
    mock_port = MagicMock()
    mock_port.fetch_endpoints.return_value = [_make_ep_dict()]

    service = EndpointMonitorService(endpoint_port=mock_port)
    records = service.run([_make_ws()])

    assert "+00:00" in records[0].time_generated


# UT-41: 3WSのうちmonitor_enabled=FalseのWSはスキップ → fetch_endpoints が2回だけ呼ばれる
def test_run_mixed_monitor_enabled_skips_disabled():
    mock_port = MagicMock()
    mock_port.fetch_endpoints.return_value = []

    ws1 = WorkspaceConfig("1", "https://adb-1.azuredatabricks.net", True)
    ws2 = WorkspaceConfig("2", "https://adb-2.azuredatabricks.net", False)
    ws3 = WorkspaceConfig("3", "https://adb-3.azuredatabricks.net", True)
    service = EndpointMonitorService(endpoint_port=mock_port)
    service.run([ws1, ws2, ws3])

    assert mock_port.fetch_endpoints.call_count == 2


# UT-42: fetch_endpoints に渡される引数が正しい WorkspaceConfig になっている
def test_run_passes_correct_workspace_to_adapter():
    mock_port = MagicMock()
    mock_port.fetch_endpoints.return_value = []

    ws = WorkspaceConfig("id-xyz", "https://adb-xyz.azuredatabricks.net", True)
    service = EndpointMonitorService(endpoint_port=mock_port)
    service.run([ws])

    mock_port.fetch_endpoints.assert_called_once_with(ws)
