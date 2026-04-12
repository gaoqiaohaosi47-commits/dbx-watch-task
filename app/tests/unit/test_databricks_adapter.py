# tests/unit/test_databricks_adapter.py
"""
adapters/databricks_adapter.py のユニットテスト。
対象: DatabricksAdapter.fetch_endpoints()
"""
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest
from databricks.sdk.errors.platform import PermissionDenied

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


@contextmanager
def _patch_sdk(list_return=None, list_side_effect=None):
    """WorkspaceClient と Config を同時に patch するヘルパー。

    Config の実体化を防ぐことで DNS 解決等の副作用なしにテストを実行できる。
    """
    with patch("adapters.databricks_adapter.WorkspaceClient") as mock_wc, \
         patch("adapters.databricks_adapter.Config") as mock_cfg:
        if list_side_effect is not None:
            mock_wc.return_value.serving_endpoints.list.side_effect = list_side_effect
        else:
            mock_wc.return_value.serving_endpoints.list.return_value = (
                list_return if list_return is not None else []
            )
        yield mock_wc, mock_cfg


# UT-16: 正常 — WorkspaceClient がエンドポイント 2 件を返す
def test_fetch_endpoints_normal():
    credential = _make_credential()
    ep1 = MagicMock()
    ep1.as_dict.return_value = {"name": "ep1", "state": {"ready": "READY"}}
    ep2 = MagicMock()
    ep2.as_dict.return_value = {"name": "ep2", "state": {"ready": "NOT_READY"}}

    with _patch_sdk(list_return=[ep1, ep2]):
        adapter = DatabricksAdapter(credential)
        result = adapter.fetch_endpoints(WS)

    assert len(result) == 2
    assert result[0] == {"name": "ep1", "state": {"ready": "READY"}}
    assert result[1] == {"name": "ep2", "state": {"ready": "NOT_READY"}}


# UT-extra: get_token の呼び出し引数に Databricks リソース ID が含まれる
def test_fetch_endpoints_uses_databricks_resource_id():
    credential = _make_credential()

    with _patch_sdk():
        adapter = DatabricksAdapter(credential)
        adapter.fetch_endpoints(WS)

    credential.get_token.assert_called_once_with(f"{AZURE_DATABRICKS_RESOURCE_ID}/.default")


# UT-23: Config に workspace_url・token・http_timeout_seconds・retry_timeout_seconds が渡され
#         WorkspaceClient が config= で初期化される
def test_fetch_endpoints_passes_workspace_url_as_host():
    credential = _make_credential()

    with _patch_sdk() as (mock_wc, mock_cfg):
        adapter = DatabricksAdapter(credential)
        adapter.fetch_endpoints(WS)

    mock_cfg.assert_called_once_with(
        host=WS.workspace_url,
        token="fake-token",
        http_timeout_seconds=HTTP_TIMEOUT_SECONDS,
        retry_timeout_seconds=HTTP_TIMEOUT_SECONDS,
    )
    mock_wc.assert_called_once_with(config=mock_cfg.return_value)


# UT-extra: Config に http_timeout_seconds=HTTP_TIMEOUT_SECONDS が渡される
def test_fetch_endpoints_passes_http_timeout():
    credential = _make_credential()

    with _patch_sdk() as (_, mock_cfg):
        adapter = DatabricksAdapter(credential)
        adapter.fetch_endpoints(WS)

    _, kwargs = mock_cfg.call_args
    assert kwargs["http_timeout_seconds"] == HTTP_TIMEOUT_SECONDS


# UT-extra: Config に retry_timeout_seconds=HTTP_TIMEOUT_SECONDS が渡される
def test_fetch_endpoints_passes_retry_timeout():
    credential = _make_credential()

    with _patch_sdk() as (_, mock_cfg):
        adapter = DatabricksAdapter(credential)
        adapter.fetch_endpoints(WS)

    _, kwargs = mock_cfg.call_args
    assert kwargs["retry_timeout_seconds"] == HTTP_TIMEOUT_SECONDS


# UT-24: タイムアウト例外（TimeoutError）が発生した場合に伝播する
def test_fetch_endpoints_raises_on_timeout():
    credential = _make_credential()

    with _patch_sdk(list_side_effect=TimeoutError("Connection timed out")):
        adapter = DatabricksAdapter(credential)

        with pytest.raises(TimeoutError, match="Connection timed out"):
            adapter.fetch_endpoints(WS)


# UT-17: 異常 — WorkspaceClient.list() が例外を raise → そのまま伝播
def test_fetch_endpoints_raises_on_error():
    credential = _make_credential()

    with _patch_sdk(list_side_effect=Exception("API error")):
        adapter = DatabricksAdapter(credential)

        with pytest.raises(Exception, match="API error"):
            adapter.fetch_endpoints(WS)


# UT-extra: エンドポイントが 0 件でも空リストを返す
def test_fetch_endpoints_empty():
    credential = _make_credential()

    with _patch_sdk(list_return=[]):
        adapter = DatabricksAdapter(credential)
        result = adapter.fetch_endpoints(WS)

    assert result == []


# UT-39: 各エンドポイントオブジェクトに対して as_dict() が呼ばれる
def test_fetch_endpoints_calls_as_dict_for_each():
    credential = _make_credential()
    ep1 = MagicMock()
    ep1.as_dict.return_value = {"name": "ep1"}
    ep2 = MagicMock()
    ep2.as_dict.return_value = {"name": "ep2"}

    with _patch_sdk(list_return=[ep1, ep2]):
        adapter = DatabricksAdapter(credential)
        adapter.fetch_endpoints(WS)

    ep1.as_dict.assert_called_once()
    ep2.as_dict.assert_called_once()


# UT-45: DatabricksError 発生時に adapter が status_code 属性を付与して再送出する
def test_fetch_endpoints_sets_status_code_on_databricks_error():
    credential = _make_credential()

    with _patch_sdk(list_side_effect=PermissionDenied("denied")):
        adapter = DatabricksAdapter(credential)

        with pytest.raises(PermissionDenied) as exc_info:
            adapter.fetch_endpoints(WS)

    assert exc_info.value.status_code == 403
