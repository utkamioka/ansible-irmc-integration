#!/usr/bin/python

# Copyright 2018-2025 Fsas Technologies Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""SessionInformationクラスのユニットテスト"""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import pytest
from unittest.mock import Mock, MagicMock
from requests.structures import CaseInsensitiveDict

from ansible_collections.fujitsu.primergy.plugins.module_utils.irmc_client import iRMC, Response
from ansible_collections.fujitsu.primergy.plugins.module_utils.irmc_session_information import (
    Session,
    SessionInformation,
)


@pytest.fixture
def mock_irmc_client():
    """モックiRMCクライアントのフィクスチャ"""
    client = Mock(spec=iRMC)
    return client


class TestSession:
    """Sessionクラスのテスト"""

    def test_init(self, mock_irmc_client):
        """Sessionオブジェクトの初期化"""
        session = Session(mock_irmc_client, 123)
        assert session.id == 123
        assert session._session_id == 123
        assert session._irmc == mock_irmc_client

    def test_get_status(self, mock_irmc_client):
        """get_status()メソッドのテスト"""
        # モックレスポンスを設定
        mock_response = Response(
            {'Session': {'Id': 123, 'Status': 'terminated regularly'}},
            CaseInsensitiveDict(),
            200,
        )
        mock_irmc_client.get.return_value = mock_response

        session = Session(mock_irmc_client, 123)
        result = session.get_status()

        # 正しいパスでGETが呼ばれたか確認
        mock_irmc_client.get.assert_called_once_with('sessionInformation/123/status', use_cache=False)
        assert result.status == 200
        assert result.body == {'Session': {'Id': 123, 'Status': 'terminated regularly'}}

    def test_get_log(self, mock_irmc_client):
        """get_log()メソッドのテスト"""
        # モックレスポンスを設定
        mock_response = Response(
            {'SessionLog': {'Id': 123, 'Entries': {'Entry': []}}},
            CaseInsensitiveDict(),
            200,
        )
        mock_irmc_client.get.return_value = mock_response

        session = Session(mock_irmc_client, 123)
        result = session.get_log()

        # 正しいパスでGETが呼ばれたか確認
        mock_irmc_client.get.assert_called_once_with('sessionInformation/123/log', use_cache=False)
        assert result.status == 200

    def test_terminate(self, mock_irmc_client):
        """terminate()メソッドのテスト"""
        mock_response = Response({}, CaseInsensitiveDict(), 200)
        mock_irmc_client.delete.return_value = mock_response

        session = Session(mock_irmc_client, 123)
        result = session.terminate()

        # 正しいパスでDELETEが呼ばれたか確認
        mock_irmc_client.delete.assert_called_once_with('sessionInformation/123/terminate')
        assert result.status == 200

    def test_remove(self, mock_irmc_client):
        """remove()メソッドのテスト"""
        mock_response = Response({}, CaseInsensitiveDict(), 200)
        mock_irmc_client.delete.return_value = mock_response

        session = Session(mock_irmc_client, 123)
        result = session.remove()

        # 正しいパスでDELETEが呼ばれたか確認
        mock_irmc_client.delete.assert_called_once_with('sessionInformation/123/remove')
        assert result.status == 200

    def test_wait_for_finish_success(self, mock_irmc_client):
        """wait_for_finish()メソッドのテスト（正常終了）"""
        # 初回: 実行中
        response1 = Response(
            {'Session': {'Id': 123, 'Status': 'running'}}, CaseInsensitiveDict(), 200
        )
        # 2回目: 正常終了
        response2 = Response(
            {'Session': {'Id': 123, 'Status': 'terminated regularly'}},
            CaseInsensitiveDict(),
            200,
        )

        mock_irmc_client.get.side_effect = [response1, response2]

        session = Session(mock_irmc_client, 123)
        result = session.wait_for_finish(interval=0)  # intervalを0にしてすぐ完了

        assert result.status == 200
        assert result.body['Session']['Status'] == 'terminated regularly'

    def test_wait_for_finish_with_error(self, mock_irmc_client):
        """wait_for_finish()メソッドのテスト（エラー終了）"""
        # 初回: 実行中
        status_response = Response(
            {'Session': {'Id': 123, 'Status': 'running'}}, CaseInsensitiveDict(), 200
        )
        # 2回目: エラー終了
        error_status_response = Response(
            {'Session': {'Id': 123, 'Status': 'terminated with error'}},
            CaseInsensitiveDict(),
            200,
        )
        # 3回目: ログ取得
        log_response = Response(
            {
                'SessionLog': {
                    'Id': 123,
                    'Entries': {
                        'Entry': [
                            {'@date': '2025/10/31 09:57:15', '#text': 'Error occurred'}
                        ]
                    },
                }
            },
            CaseInsensitiveDict(),
            200,
        )

        mock_irmc_client.get.side_effect = [status_response, error_status_response, log_response]

        session = Session(mock_irmc_client, 123)
        result = session.wait_for_finish(interval=0)

        # エラー時はlogレスポンスが返される（status=29）
        assert result.status == 29
        assert 'SessionLog' in result.body

    def test_wait_for_finish_http_error(self, mock_irmc_client):
        """wait_for_finish()メソッドのテスト（HTTPエラー）"""
        error_response = Response('Not Found', CaseInsensitiveDict(), 404)
        mock_irmc_client.get.return_value = error_response

        session = Session(mock_irmc_client, 123)
        result = session.wait_for_finish()

        # エラーレスポンスがそのまま返される
        assert result.status == 404


class TestSessionInformation:
    """SessionInformationクラスのテスト"""

    def test_init(self, mock_irmc_client):
        """SessionInformationオブジェクトの初期化"""
        session_info = SessionInformation(mock_irmc_client)
        assert session_info._irmc == mock_irmc_client

    def test_get(self, mock_irmc_client):
        """get()メソッドのテスト"""
        session_info = SessionInformation(mock_irmc_client)
        session = session_info.get(123)

        # Sessionオブジェクトが返される
        assert isinstance(session, Session)
        assert session.id == 123


class TestSessionsPropertyInIRMC:
    """iRMC.sessionsプロパティのテスト"""

    def test_sessions_property(self):
        """sessionsプロパティが正しく動作する"""
        irmc = iRMC('192.0.2.1', 'admin', 'password')
        sessions = irmc.sessions

        # SessionInformationインスタンスが返される
        assert isinstance(sessions, SessionInformation)

    def test_sessions_property_caching(self):
        """sessionsプロパティが同じインスタンスを返す（キャッシュ）"""
        irmc = iRMC('192.0.2.1', 'admin', 'password')
        sessions1 = irmc.sessions
        sessions2 = irmc.sessions

        # 同じインスタンスが返される
        assert sessions1 is sessions2
