# tests/unit/test_databricks_adapter.py
"""
adapters/databricks_adapter.py のユニットテスト。
対象: DatabricksAdapter.fetch_endpoints()
"""
from unittest.mock import MagicMock, patch

import pytest

from adapters.databricks_adapter import AZURE_DATABRICKS_RESOURCE_ID, DatabricksAdapter
from domain.model import WorkspaceConfig

WS = WorkspaceConfig(
    workspace_id="1991908275471167",
    workspace_url="https://adb-1991908275471167.7.azuredatabricks.net",
    monitor_enabled=True,
)


def _make_credential(token_str="fake-token"):
    credential = MagicMock()
    token = MagicMock()
    token.token = token_str
    credential.get_token.return_value = token
    return credential


# UT-16: 正常 — WorkspaceClient がエンドポイント 2 件を返す
def test_fetch_endpoints_normal():
    credential = _make_credential()
    ep1 = MagicMock()
    ep1.as_dict.return_value = {"name": "ep1", "state": {"ready": "READY"}}
    ep2 = MagicMock()
    ep2.as_dict.return_value = {"name": "ep2", "state": {"ready": "NOT_READY"}}

    with patch("adapters.databricks_adapter.WorkspaceClient") as mock_wc_cls:
        mock_wc_cls.return_value.serving_endpoints.list.return_value = [ep1, ep2]
        adapter = DatabricksAdapter(credential)
        result = adapter.fetch_endpoints(WS)

    assert len(result) == 2
    assert result[0] == {"name": "ep1", "state": {"ready": "READY"}}
    assert result[1] == {"name": "ep2", "state": {"ready": "NOT_READY"}}


# UT-extra: get_token の呼び出し引数に Databricks リソース ID が含まれる
def test_fetch_endpoints_uses_databricks_resource_id():
    credential = _make_credential()

    with patch("adapters.databricks_adapter.WorkspaceClient") as mock_wc_cls:
        mock_wc_cls.return_value.serving_endpoints.list.return_value = []
        adapter = DatabricksAdapter(credential)
        adapter.fetch_endpoints(WS)

    credential.get_token.assert_called_once_with(f"{AZURE_DATABRICKS_RESOURCE_ID}/.default")


# UT-extra: WorkspaceClient の host に workspace_url が渡される
def test_fetch_endpoints_passes_workspace_url_as_host():
    credential = _make_credential()

    with patch("adapters.databricks_adapter.WorkspaceClient") as mock_wc_cls:
        mock_wc_cls.return_value.serving_endpoints.list.return_value = []
        adapter = DatabricksAdapter(credential)
        adapter.fetch_endpoints(WS)

    mock_wc_cls.assert_called_once_with(host=WS.workspace_url, token="fake-token")


# UT-17: 異常 — WorkspaceClient.list() が例外を raise → そのまま伝播
def test_fetch_endpoints_raises_on_error():
    credential = _make_credential()

    with patch("adapters.databricks_adapter.WorkspaceClient") as mock_wc_cls:
        mock_wc_cls.return_value.serving_endpoints.list.side_effect = Exception("API error")
        adapter = DatabricksAdapter(credential)

        with pytest.raises(Exception, match="API error"):
            adapter.fetch_endpoints(WS)


# UT-extra: エンドポイントが 0 件でも空リストを返す
def test_fetch_endpoints_empty():
    credential = _make_credential()

    with patch("adapters.databricks_adapter.WorkspaceClient") as mock_wc_cls:
        mock_wc_cls.return_value.serving_endpoints.list.return_value = []
        adapter = DatabricksAdapter(credential)
        result = adapter.fetch_endpoints(WS)

    assert result == []
