# tests/unit/test_log_analytics_adapter.py
"""
adapters/log_analytics_adapter.py のユニットテスト。
対象: LogAnalyticsAdapter.send()
"""
from unittest.mock import MagicMock, patch

import pytest
from azure.core.exceptions import HttpResponseError

from adapters.log_analytics_adapter import LogAnalyticsAdapter
from domain.model import EndpointRecord

DCE = "https://dce-example.eastus-1.ingest.monitor.azure.com"
DCR_ID = "dcr-abc123"
STREAM = "Custom-AppLogs"
TIMESTAMP = "2026-04-11T10:00:00+00:00"
WS_URL = "https://adb-1234567890123456.7.azuredatabricks.net"


def _make_record(status=200):
    return EndpointRecord(
        time_generated=TIMESTAMP,
        workspace_url=WS_URL,
        api_status_code=status,
        api_error_message=None if status == 200 else "error",
        endpoint_name="ep1" if status == 200 else None,
        endpoint_state="READY" if status == 200 else None,
        endpoint_raw_data={"name": "ep1"} if status == 200 else None,
    )


def _make_adapter(mock_client):
    credential = MagicMock()
    with patch("adapters.log_analytics_adapter.LogsIngestionClient", return_value=mock_client):
        return LogAnalyticsAdapter(
            credential=credential,
            dce_endpoint=DCE,
            dcr_immutable_id=DCR_ID,
            dcr_stream_name=STREAM,
        )


# UT-18: 正常 — upload() が 1 回呼ばれ、3 件分の dict が渡される
def test_send_normal_3_records():
    mock_client = MagicMock()
    adapter = _make_adapter(mock_client)

    adapter.send([_make_record(), _make_record(), _make_record()])

    mock_client.upload.assert_called_once()
    _, kwargs = mock_client.upload.call_args
    assert len(kwargs["logs"]) == 3
    assert kwargs["rule_id"] == DCR_ID
    assert kwargs["stream_name"] == STREAM


# UT-19: 境界 — 空リストの場合 upload() は呼ばれない
def test_send_empty_records_no_upload():
    mock_client = MagicMock()
    adapter = _make_adapter(mock_client)

    adapter.send([])

    mock_client.upload.assert_not_called()


# UT-20: 異常 — upload() が HttpResponseError を raise → 伝播する
def test_send_raises_http_response_error():
    mock_client = MagicMock()
    mock_client.upload.side_effect = HttpResponseError(message="ingest failed")
    adapter = _make_adapter(mock_client)

    with pytest.raises(HttpResponseError):
        adapter.send([_make_record()])


# UT-extra: upload に渡される logs の各要素に TimeGenerated が含まれる
def test_send_logs_contain_time_generated():
    mock_client = MagicMock()
    adapter = _make_adapter(mock_client)

    adapter.send([_make_record()])

    _, kwargs = mock_client.upload.call_args
    assert "TimeGenerated" in kwargs["logs"][0]
    assert kwargs["logs"][0]["TimeGenerated"] == TIMESTAMP
