# tests/unit/test_databricks_adapter.py
"""
adapters/databricks_adapter.py のユニットテスト。
対象: DatabricksAdapter.fetch_endpoints()
"""
from unittest.mock import MagicMock, patch

import pytest
import requests as req

from adapters.databricks_adapter import (
    AZURE_DATABRICKS_RESOURCE_ID,
    HTTP_TIMEOUT_SECONDS,
    DatabricksAdapter,
)
from domain.model import WorkspaceConfig

WS = WorkspaceConfig(
    workspace_id="1234567890123456",
    workspace_url="https://adb-1234567890123456.7.azuredatabricks.net",
    monitor_enabled=True,
)


def _make_credential(token_str="fake-token"):
    credential = MagicMock()
    token = MagicMock()
    token.token = token_str
    credential.get_token.return_value = token
    return credential


def _mock_response(status_code=200, json_data=None):
    """requests.Response モックを生成する。"""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    if status_code >= 400:
        http_err = req.HTTPError(response=resp)
        resp.raise_for_status.side_effect = http_err
    else:
        resp.raise_for_status.return_value = None
    return resp


# UT-16: 正常 — エンドポイント 2 件を返す
def test_fetch_endpoints_normal():
    credential = _make_credential()
    endpoints = [
        {"name": "ep1", "state": {"ready": "READY"}},
        {"name": "ep2", "state": {"ready": "NOT_READY"}},
    ]

    with patch("adapters.databricks_adapter.requests.get") as mock_get:
        mock_get.return_value = _mock_response(json_data={"endpoints": endpoints})
        adapter = DatabricksAdapter(credential)
        result = adapter.fetch_endpoints(WS)

    assert len(result) == 2
    assert result[0] == {"name": "ep1", "state": {"ready": "READY"}}
    assert result[1] == {"name": "ep2", "state": {"ready": "NOT_READY"}}


# UT-extra: get_token に Databricks リソース ID が渡される
def test_fetch_endpoints_uses_databricks_resource_id():
    credential = _make_credential()

    with patch("adapters.databricks_adapter.requests.get") as mock_get:
        mock_get.return_value = _mock_response(json_data={})
        adapter = DatabricksAdapter(credential)
        adapter.fetch_endpoints(WS)

    credential.get_token.assert_called_once_with(f"{AZURE_DATABRICKS_RESOURCE_ID}/.default")


# UT-23: requests.get に workspace_url ベースの URL と timeout が渡される
def test_fetch_endpoints_passes_url_and_timeout():
    credential = _make_credential()

    with patch("adapters.databricks_adapter.requests.get") as mock_get:
        mock_get.return_value = _mock_response(json_data={})
        adapter = DatabricksAdapter(credential)
        adapter.fetch_endpoints(WS)

    mock_get.assert_called_once()
    args, kwargs = mock_get.call_args
    assert args[0] == f"{WS.workspace_url}/api/2.0/serving-endpoints"
    assert kwargs["timeout"] == HTTP_TIMEOUT_SECONDS


# UT-extra: Authorization: Bearer ヘッダーが設定される
def test_fetch_endpoints_sets_bearer_header():
    credential = _make_credential(token_str="my-token")

    with patch("adapters.databricks_adapter.requests.get") as mock_get:
        mock_get.return_value = _mock_response(json_data={})
        adapter = DatabricksAdapter(credential)
        adapter.fetch_endpoints(WS)

    _, kwargs = mock_get.call_args
    assert kwargs["headers"]["Authorization"] == "Bearer my-token"


# UT-24: requests.Timeout 発生 → TimeoutError に変換して送出
def test_fetch_endpoints_raises_timeout_error():
    credential = _make_credential()

    with patch("adapters.databricks_adapter.requests.get") as mock_get:
        mock_get.side_effect = req.Timeout()
        adapter = DatabricksAdapter(credential)

        with pytest.raises(TimeoutError):
            adapter.fetch_endpoints(WS)


# UT-17: HTTP 403 → requests.HTTPError に status_code 属性を付与して伝播
def test_fetch_endpoints_raises_http_error_with_status_code():
    credential = _make_credential()

    with patch("adapters.databricks_adapter.requests.get") as mock_get:
        mock_get.return_value = _mock_response(status_code=403)
        adapter = DatabricksAdapter(credential)

        with pytest.raises(req.HTTPError) as exc_info:
            adapter.fetch_endpoints(WS)

    assert exc_info.value.status_code == 403


# UT-extra: エンドポイントが 0 件でも空リストを返す
def test_fetch_endpoints_empty():
    credential = _make_credential()

    with patch("adapters.databricks_adapter.requests.get") as mock_get:
        mock_get.return_value = _mock_response(json_data={"endpoints": []})
        adapter = DatabricksAdapter(credential)
        result = adapter.fetch_endpoints(WS)

    assert result == []


# UT-extra: レスポンスに "endpoints" キーがない場合も空リストを返す
def test_fetch_endpoints_missing_endpoints_key():
    credential = _make_credential()

    with patch("adapters.databricks_adapter.requests.get") as mock_get:
        mock_get.return_value = _mock_response(json_data={})
        adapter = DatabricksAdapter(credential)
        result = adapter.fetch_endpoints(WS)

    assert result == []
