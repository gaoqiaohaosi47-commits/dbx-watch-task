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
