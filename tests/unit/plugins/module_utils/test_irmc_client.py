#!/usr/bin/python

# Copyright 2018-2026 Fsas Technologies Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""iRMCクライアントクラスのユニットテスト"""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from unittest.mock import Mock, patch, MagicMock
from requests.structures import CaseInsensitiveDict

from ansible_collections.fsas.primergy.plugins.module_utils.irmc_client import (
    iRMC,
    Response,
    _parse_irmc_version_from_server_header,
)
from ansible_collections.fsas.primergy.plugins.module_utils.logger import MockLogger


class TestResponse:
    """Responseクラスのテスト"""

    def test_response_attributes(self):
        """Responseオブジェクトの属性にアクセスできる"""
        response = Response(
            {'data': 'test'}, {'Content-Type': 'application/json'}, 200
        )
        assert response.body == {'data': 'test'}
        assert response.headers == {'Content-Type': 'application/json'}
        assert response.status == 200

    def test_response_tuple_unpacking(self):
        """Responseオブジェクトはタプルとして展開できる"""
        response = Response(
            {'data': 'test'}, {'Content-Type': 'application/json'}, 200
        )
        body, headers, status = response

        assert body == {'data': 'test'}
        assert headers == {'Content-Type': 'application/json'}
        assert status == 200


class TestIRMCInit:
    """iRMCクラスの初期化テスト"""

    def test_init_required_params(self):
        """必須パラメータのみで初期化"""
        irmc = iRMC('192.0.2.1', 'admin', 'password')
        assert irmc.ipaddress == '192.0.2.1'
        assert irmc.username == 'admin'
        assert irmc.password == 'password'
        assert irmc.port == 443  # デフォルト
        assert irmc.validate_certs is True  # デフォルト

    def test_init_with_port(self):
        """ポート番号を指定して初期化"""
        irmc = iRMC('192.0.2.1', 'admin', 'password', port=8443)
        assert irmc.port == 8443

    def test_init_with_validate_certs_false(self):
        """SSL証明書検証を無効にして初期化"""
        irmc = iRMC('192.0.2.1', 'admin', 'password', validate_certs=False)
        assert irmc.validate_certs is False

    def test_build_url(self):
        """URLの構築"""
        irmc = iRMC('192.0.2.1', 'admin', 'password')
        url = irmc._build_url('/redfish/v1')
        assert url == 'https://192.0.2.1:443/redfish/v1'

    def test_build_url_without_leading_slash(self):
        """先頭のスラッシュなしでURLを構築"""
        irmc = iRMC('192.0.2.1', 'admin', 'password')
        url = irmc._build_url('redfish/v1')
        assert url == 'https://192.0.2.1:443/redfish/v1'

    def test_normalize_path(self):
        """パスの正規化（先頭にスラッシュを追加、末尾のスラッシュを削除）"""
        irmc = iRMC('192.0.2.1', 'admin', 'password')
        assert irmc._normalize_path('/redfish/v1/') == '/redfish/v1'
        assert irmc._normalize_path('/redfish/v1') == '/redfish/v1'
        assert irmc._normalize_path('redfish/v1/') == '/redfish/v1'
        assert irmc._normalize_path('redfish/v1') == '/redfish/v1'


class TestIRMCCacheKey:
    """キャッシュキー生成のテスト"""

    def test_make_cache_key_no_query(self):
        """クエリパラメータなしのキャッシュキー生成"""
        irmc = iRMC('192.0.2.1', 'admin', 'password')
        key = irmc._make_cache_key('/redfish/v1', None)
        assert key is not None
        assert key[0] == '/redfish/v1'

    def test_make_cache_key_with_query(self):
        """クエリパラメータありの場合はNoneを返す"""
        irmc = iRMC('192.0.2.1', 'admin', 'password')
        key = irmc._make_cache_key('/redfish/v1?filter=all', None)
        assert key is None

    def test_make_cache_key_normalizes_trailing_slash(self):
        """先頭と末尾のスラッシュが正規化される"""
        irmc = iRMC('192.0.2.1', 'admin', 'password')
        key1 = irmc._make_cache_key('/redfish/v1/', None)
        key2 = irmc._make_cache_key('/redfish/v1', None)
        key3 = irmc._make_cache_key('redfish/v1', None)
        key4 = irmc._make_cache_key('redfish/v1/', None)
        # すべてのパターンで同じキャッシュキーになる
        assert key1 == key2 == key3 == key4
        # 正規化後のパスは '/redfish/v1'
        assert key1[0] == '/redfish/v1'

    def test_make_cache_key_with_headers(self):
        """ヘッダーを含むキャッシュキー"""
        irmc = iRMC('192.0.2.1', 'admin', 'password')
        key1 = irmc._make_cache_key('/redfish/v1', {'Accept': 'text/plain'})
        key2 = irmc._make_cache_key(
            '/redfish/v1', {'Accept': 'application/json'}
        )
        assert key1 != key2


class TestIRMCGet:
    """GETメソッドのテスト"""

    @patch('requests.Session')
    def test_get_basic(self, mock_session_class):
        """基本的なGETリクエスト"""
        # モックの設定
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'data': 'test'}
        mock_response.headers = {'Content-Type': 'application/json'}
        mock_response.text = '{"data": "test"}'
        mock_response.connection = Mock()
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        # テスト実行
        irmc = iRMC('192.0.2.1', 'admin', 'password', validate_certs=False)
        response = irmc.get('/redfish/v1')

        # 検証
        assert response.status == 200
        assert response.body == {'data': 'test'}
        assert isinstance(response, Response)

    @patch('requests.Session')
    def test_get_tuple_unpacking(self, mock_session_class):
        """タプルとして展開できる"""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'data': 'test'}
        mock_response.headers = {}
        mock_response.text = '{"data": "test"}'
        mock_response.connection = Mock()
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        irmc = iRMC('192.0.2.1', 'admin', 'password')
        body, headers, status = irmc.get('/redfish/v1')

        assert status == 200
        assert body == {'data': 'test'}

    @patch('requests.Session')
    def test_get_cache_same_path(self, mock_session_class):
        """同じパスへのリクエストはキャッシュされる"""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'data': 'cached'}
        mock_response.headers = {}
        mock_response.text = '{"data": "cached"}'
        mock_response.connection = Mock()
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        irmc = iRMC('192.0.2.1', 'admin', 'password')

        # 1回目
        response1 = irmc.get('/redfish/v1')
        # 2回目（キャッシュ使用）
        response2 = irmc.get('/redfish/v1')

        # APIは1回だけ呼ばれる
        assert mock_session.request.call_count == 1
        assert response1.body == response2.body

    @patch('requests.Session')
    def test_get_cache_trailing_slash(self, mock_session_class):
        """末尾のスラッシュは正規化される"""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'data': 'test'}
        mock_response.headers = {}
        mock_response.text = '{"data": "test"}'
        mock_response.connection = Mock()
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        irmc = iRMC('192.0.2.1', 'admin', 'password')

        # 末尾にスラッシュあり
        response1 = irmc.get('/redfish/v1/')
        # 末尾にスラッシュなし
        response2 = irmc.get('/redfish/v1')

        # 同じキャッシュが使われる
        assert mock_session.request.call_count == 1
        assert response1.body == response2.body

    @patch('requests.Session')
    def test_get_no_cache_with_query(self, mock_session_class):
        """クエリパラメータがある場合はキャッシュされない"""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'data': 'test'}
        mock_response.headers = {}
        mock_response.text = '{"data": "test"}'
        mock_response.connection = Mock()
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        irmc = iRMC('192.0.2.1', 'admin', 'password')

        # クエリパラメータ付き
        response1 = irmc.get('/redfish/v1?filter=all')
        response2 = irmc.get('/redfish/v1?filter=all')

        # 毎回APIが呼ばれる
        assert mock_session.request.call_count == 2

    @patch('requests.Session')
    def test_get_use_cache_false(self, mock_session_class):
        """use_cache=Falseでキャッシュを無視"""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'data': 'test'}
        mock_response.headers = {}
        mock_response.text = '{"data": "test"}'
        mock_response.connection = Mock()
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        irmc = iRMC('192.0.2.1', 'admin', 'password')

        response1 = irmc.get('/redfish/v1', use_cache=True)
        response2 = irmc.get('/redfish/v1', use_cache=False)

        # 2回APIが呼ばれる
        assert mock_session.request.call_count == 2


class TestIRMCPost:
    """POSTメソッドのテスト"""

    @patch('requests.Session')
    def test_post_basic(self, mock_session_class):
        """基本的なPOSTリクエスト"""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {'created': True}
        mock_response.headers = {}
        mock_response.text = '{"created": true}'
        mock_response.connection = Mock()
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        irmc = iRMC('192.0.2.1', 'admin', 'password')
        response = irmc.post('/redfish/v1/Actions', {'action': 'reset'})

        assert response.status == 201
        assert response.body == {'created': True}
        assert isinstance(response, Response)

    @patch('requests.Session')
    def test_post_tuple_unpacking(self, mock_session_class):
        """POSTレスポンスをタプルとして展開"""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {'created': True}
        mock_response.headers = {}
        mock_response.text = '{"created": true}'
        mock_response.connection = Mock()
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        irmc = iRMC('192.0.2.1', 'admin', 'password')
        body, headers, status = irmc.post(
            '/redfish/v1/Actions', {'action': 'reset'}
        )

        assert status == 201
        assert body == {'created': True}


class TestIRMCOtherMethods:
    """その他のHTTPメソッドのテスト"""

    @patch('requests.Session')
    def test_put(self, mock_session_class):
        """PUTリクエスト"""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'updated': True}
        mock_response.headers = {}
        mock_response.text = '{"updated": true}'
        mock_response.connection = Mock()
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        irmc = iRMC('192.0.2.1', 'admin', 'password')
        response = irmc.put('/redfish/v1/Resource', {'data': 'updated'})

        assert response.status == 200
        assert isinstance(response, Response)

    @patch('requests.Session')
    def test_patch(self, mock_session_class):
        """PATCHリクエスト"""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'patched': True}
        mock_response.headers = {}
        mock_response.text = '{"patched": true}'
        mock_response.connection = Mock()
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        irmc = iRMC('192.0.2.1', 'admin', 'password')
        response = irmc.patch('/redfish/v1/Resource', {'data': 'patched'})

        assert response.status == 200
        assert isinstance(response, Response)

    @patch('requests.Session')
    def test_delete(self, mock_session_class):
        """DELETEリクエスト"""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 204
        mock_response.json.side_effect = ValueError()  # No content
        mock_response.headers = {}
        mock_response.text = ''
        mock_response.connection = Mock()
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        irmc = iRMC('192.0.2.1', 'admin', 'password')
        response = irmc.delete('/redfish/v1/Resource')

        assert response.status == 204
        assert isinstance(response, Response)

    @patch('requests.Session')
    def test_head(self, mock_session_class):
        """HEADリクエスト"""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError()  # No content
        mock_response.headers = {'Content-Length': '1234'}
        mock_response.text = ''
        mock_response.connection = Mock()
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        irmc = iRMC('192.0.2.1', 'admin', 'password')
        response = irmc.head('/redfish/v1')

        assert response.status == 200
        assert isinstance(response, Response)

    @patch('requests.Session')
    def test_options(self, mock_session_class):
        """OPTIONSリクエスト"""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError()
        mock_response.headers = {'Allow': 'GET, POST, PUT, DELETE'}
        mock_response.text = ''
        mock_response.connection = Mock()
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        irmc = iRMC('192.0.2.1', 'admin', 'password')
        response = irmc.options('/redfish/v1')

        assert response.status == 200
        assert isinstance(response, Response)


class TestIRMCCustomHeaders:
    """カスタムヘッダーのテスト"""

    @patch('requests.Session')
    def test_get_with_custom_accept_header(self, mock_session_class):
        """カスタムAcceptヘッダーが使用される"""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200

        # JSONとしてパースできないテキストを設定
        def json_side_effect():
            raise ValueError("Not JSON")

        mock_response.json.side_effect = json_side_effect
        mock_response.text = 'plain text'
        mock_response.headers = {}
        mock_response.connection = Mock()
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        irmc = iRMC('192.0.2.1', 'admin', 'password')
        response = irmc.get('/redfish/v1', headers={'Accept': 'text/plain'})

        # request呼び出し時のheadersを確認
        call_kwargs = mock_session.request.call_args.kwargs
        assert call_kwargs['headers']['Accept'] == 'text/plain'
        assert response.body == 'plain text'


class TestIRMCLogging:
    """ログ機能のテスト"""

    @patch('requests.Session')
    def test_logger_called_on_request(self, mock_session_class):
        """リクエスト時にloggerが呼ばれる"""
        # モックの設定
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'data': 'test'}
        mock_response.headers = {}
        mock_response.text = '{"data": "test"}'
        mock_response.connection = Mock()
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        # MockLoggerを使用
        logger = MockLogger()

        # テスト実行
        irmc = iRMC('192.0.2.1', 'admin', 'password', logger=logger)
        response = irmc.get('/redfish/v1')

        # debugレベルでログが記録されることを確認
        assert len(logger.messages['debug']) == 2
        assert 'iRMC Request: GET /redfish/v1' in logger.messages['debug'][0]
        assert 'iRMC Response: GET /redfish/v1' in logger.messages['debug'][1]
        assert 'Status: 200' in logger.messages['debug'][1]
        assert 'Time:' in logger.messages['debug'][1]

    @patch('requests.Session')
    def test_logger_not_called_without_logger(self, mock_session_class):
        """loggerがない場合はログが出力されない"""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'data': 'test'}
        mock_response.headers = {}
        mock_response.text = '{"data": "test"}'
        mock_response.connection = Mock()
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        # loggerなしでインスタンス作成
        irmc = iRMC('192.0.2.1', 'admin', 'password')
        response = irmc.get('/redfish/v1')

        # エラーが発生しないことを確認
        assert response.status == 200

    @patch('requests.Session')
    def test_logger_called_on_post(self, mock_session_class):
        """POSTリクエスト時にログが出力される"""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {'created': True}
        mock_response.headers = {}
        mock_response.text = '{"created": true}'
        mock_response.connection = Mock()
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        logger = MockLogger()
        irmc = iRMC('192.0.2.1', 'admin', 'password', logger=logger)
        response = irmc.post('/redfish/v1/Actions', {'action': 'reset'})

        # debugレベルでログが記録されることを確認
        assert len(logger.messages['debug']) == 2
        assert 'iRMC Request: POST /redfish/v1/Actions' in logger.messages['debug'][0]
        assert 'iRMC Response: POST /redfish/v1/Actions' in logger.messages['debug'][1]
        assert 'Status: 201' in logger.messages['debug'][1]

    @patch('requests.Session')
    def test_logger_called_on_error(self, mock_session_class):
        """エラー時にログが出力される"""
        mock_session = Mock()
        mock_session.request.side_effect = Exception('Connection error')
        mock_session_class.return_value = mock_session

        logger = MockLogger()
        irmc = iRMC('192.0.2.1', 'admin', 'password', logger=logger)
        response = irmc.get('/redfish/v1')

        # debugレベルでリクエストログ、warnレベルでエラーログが記録されることを確認
        assert len(logger.messages['debug']) == 1
        assert 'iRMC Request: GET /redfish/v1' in logger.messages['debug'][0]
        assert len(logger.messages['warn']) == 1
        assert 'iRMC Request Error' in logger.messages['warn'][0]
        assert 'Connection error' in logger.messages['warn'][0]
        assert response.status == 99

    @patch('requests.Session')
    def test_log_levels_on_request(self, mock_session_class):
        """リクエスト/レスポンス成功時にdebugレベルを使用する"""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'data': 'test'}
        mock_response.headers = {}
        mock_response.text = '{"data": "test"}'
        mock_response.connection = Mock()
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        logger = MockLogger()
        irmc = iRMC('192.0.2.1', 'admin', 'password', logger=logger)
        irmc.get('/redfish/v1')

        # debugレベルのみが使用され、warnやlogは使用されない
        assert len(logger.messages['debug']) == 2
        assert len(logger.messages['warn']) == 0
        assert len(logger.messages['log']) == 0

    @patch('requests.Session')
    def test_log_levels_on_error(self, mock_session_class):
        """エラー時にwarnレベルを使用する"""
        mock_session = Mock()
        mock_session.request.side_effect = Exception('Test error')
        mock_session_class.return_value = mock_session

        logger = MockLogger()
        irmc = iRMC('192.0.2.1', 'admin', 'password', logger=logger)
        irmc.get('/redfish/v1')

        # debugレベルでリクエスト開始、warnレベルでエラー
        assert len(logger.messages['debug']) == 1
        assert len(logger.messages['warn']) == 1
        assert len(logger.messages['log']) == 0

    @patch('requests.Session')
    def test_vendor_detection_uses_debug(self, mock_session_class):
        """vendor検出成功時にdebugレベルを使用する"""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'Vendor': 'ts_fujitsu'}
        mock_response.headers = {}
        mock_response.text = '{"Vendor": "ts_fujitsu"}'
        mock_response.connection = Mock()
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        logger = MockLogger()
        irmc = iRMC('192.0.2.1', 'admin', 'password', logger=logger)
        vendor = irmc.vendor

        # 正常系（status=200でvendor検出）の場合はログが出力されない
        vendor_logs = [msg for msg in logger.messages['debug'] if 'Vendor detected' in msg]
        assert len(vendor_logs) == 0
        assert len(logger.messages['warn']) == 0

    @patch('requests.Session')
    def test_vendor_detection_error_uses_warn(self, mock_session_class):
        """vendor検出失敗時にwarnレベルを使用する"""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.json.return_value = {}
        mock_response.headers = {}
        mock_response.text = 'Internal Server Error'
        mock_response.connection = Mock()
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        logger = MockLogger()
        irmc = iRMC('192.0.2.1', 'admin', 'password', logger=logger)
        vendor = irmc.vendor

        # vendor検出失敗ログがwarnレベルに含まれる
        vendor_logs = [msg for msg in logger.messages['warn'] if 'Vendor detection failed' in msg]
        assert len(vendor_logs) == 1

    @patch('requests.Session')
    def test_version_detection_uses_debug(self, mock_session_class):
        """version検出成功時にdebugレベルを使用する"""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'RedfishVersion': '1.15.0'}
        mock_response.headers = CaseInsensitiveDict({'Server': 'iRMC S6 Server'})
        mock_response.text = '{"RedfishVersion": "1.15.0"}'
        mock_response.connection = Mock()
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        logger = MockLogger()
        irmc = iRMC('192.0.2.1', 'admin', 'password', logger=logger)
        version = irmc.version

        # version検出ログがdebugレベルに含まれる
        version_logs = [msg for msg in logger.messages['debug'] if 'Server Version detected' in msg]
        assert len(version_logs) == 1
        assert 'S6' in version_logs[0]
        assert len(logger.messages['warn']) == 0


class TestIRMCVendor:
    """vendorプロパティのテスト"""

    @patch('requests.Session')
    def test_vendor_ts_fujitsu(self, mock_session_class):
        """Vendor属性が"ts_fujitsu"の場合"""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'Vendor': 'ts_fujitsu',
            'RedfishVersion': '1.15.0',
        }
        mock_response.headers = {}
        mock_response.text = '{"Vendor": "ts_fujitsu"}'
        mock_response.connection = Mock()
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        irmc = iRMC('192.0.2.1', 'admin', 'password')
        vendor = irmc.vendor

        assert vendor == 'ts_fujitsu'
        # /redfish/v1がGETされたことを確認
        assert mock_session.request.call_count == 1

    @patch('requests.Session')
    def test_vendor_fsas(self, mock_session_class):
        """Vendor属性が"Fsas"の場合（M8世代）"""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'Vendor': 'Fsas',
            'RedfishVersion': '1.20.0',
        }
        mock_response.headers = {}
        mock_response.text = '{"Vendor": "Fsas"}'
        mock_response.connection = Mock()
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        irmc = iRMC('192.0.2.1', 'admin', 'password')
        vendor = irmc.vendor

        assert vendor == 'Fsas'

    @patch('requests.Session')
    def test_vendor_not_found(self, mock_session_class):
        """ステータス200だがVendor属性が存在しない場合（S5想定、ts_fujitsuにフォールバック）"""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'RedfishVersion': '1.15.0',
            # Vendorキーなし（S5想定）
        }
        mock_response.headers = {}
        mock_response.text = '{"RedfishVersion": "1.15.0"}'
        mock_response.connection = Mock()
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        irmc = iRMC('192.0.2.1', 'admin', 'password')

        # 初回アクセス（ts_fujitsuにフォールバック）
        vendor1 = irmc.vendor
        assert vendor1 == 'ts_fujitsu'

        # 2回目アクセス（再GETしない）
        vendor2 = irmc.vendor
        assert vendor2 == 'ts_fujitsu'

        # /redfish/v1は1回だけGETされる
        assert mock_session.request.call_count == 1

    @patch('requests.Session')
    def test_vendor_connection_error(self, mock_session_class):
        """接続エラーの場合（次回再試行可能）"""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.json.return_value = {}
        mock_response.headers = {}
        mock_response.text = 'Internal Server Error'
        mock_response.connection = Mock()
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        irmc = iRMC('192.0.2.1', 'admin', 'password')

        # 初回アクセス（エラー）
        vendor1 = irmc.vendor
        assert vendor1 is None

        # 2回目アクセス（再GETする）
        vendor2 = irmc.vendor
        assert vendor2 is None

        # /redfish/v1は2回GETされる
        assert mock_session.request.call_count == 2

    @patch('requests.Session')
    def test_vendor_cached(self, mock_session_class):
        """取得成功後、キャッシュされる"""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'Vendor': 'ts_fujitsu'}
        mock_response.headers = {}
        mock_response.text = '{"Vendor": "ts_fujitsu"}'
        mock_response.connection = Mock()
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        irmc = iRMC('192.0.2.1', 'admin', 'password')

        # 複数回アクセス
        vendor1 = irmc.vendor
        vendor2 = irmc.vendor
        vendor3 = irmc.vendor

        assert vendor1 == 'ts_fujitsu'
        assert vendor2 == 'ts_fujitsu'
        assert vendor3 == 'ts_fujitsu'

        # /redfish/v1は1回だけGETされる
        assert mock_session.request.call_count == 1

    @patch('requests.Session')
    def test_vendor_with_logger(self, mock_session_class):
        """ログ機能と連携して動作する"""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'Vendor': 'ts_fujitsu'}
        mock_response.headers = {}
        mock_response.text = '{"Vendor": "ts_fujitsu"}'
        mock_response.connection = Mock()
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        logger = MockLogger()
        irmc = iRMC('192.0.2.1', 'admin', 'password', logger=logger)
        vendor = irmc.vendor

        assert vendor == 'ts_fujitsu'

        # 正常系（status=200でvendor検出）の場合はログが出力されないことを確認
        vendor_logs = [msg for msg in logger.messages['debug'] if 'Vendor detected' in msg]
        assert len(vendor_logs) == 0


class TestIRMCOemPrefix:
    """iRMC.oem_prefixプロパティのテストクラス"""

    def test_oem_prefix_m7(self):
        """M7: vendor="ts_fujitsu" → oem_prefix="FTS" """
        with patch('plugins.module_utils.irmc_client.requests.Session') as mock_session:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = '{"Vendor": "ts_fujitsu"}'
            mock_response.json.return_value = {"Vendor": "ts_fujitsu"}
            mock_response.headers = CaseInsensitiveDict({})
            mock_session.return_value.request.return_value = mock_response

            irmc = iRMC('192.0.2.1', 'admin', 'password')
            prefix = irmc.oem_prefix

            assert prefix == 'FTS'

    def test_oem_prefix_m8(self):
        """M8: vendor="Fsas" → oem_prefix="Fsas" """
        with patch('plugins.module_utils.irmc_client.requests.Session') as mock_session:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = '{"Vendor": "Fsas"}'
            mock_response.json.return_value = {"Vendor": "Fsas"}
            mock_response.headers = CaseInsensitiveDict({})
            mock_session.return_value.request.return_value = mock_response

            irmc = iRMC('192.0.2.1', 'admin', 'password')
            prefix = irmc.oem_prefix

            assert prefix == 'Fsas'

    def test_oem_prefix_vendor_not_found(self):
        """Vendor属性がない場合（S5想定）→ ts_fujitsuにフォールバック → oem_prefix=FTS"""
        with patch('plugins.module_utils.irmc_client.requests.Session') as mock_session:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = '{}'
            mock_response.json.return_value = {}
            mock_response.headers = CaseInsensitiveDict({})
            mock_session.return_value.request.return_value = mock_response

            irmc = iRMC('192.0.2.1', 'admin', 'password')
            prefix = irmc.oem_prefix

            # vendorがts_fujitsuにフォールバックするため、oem_prefixはFTSになる
            assert prefix == 'FTS'

    def test_oem_prefix_connection_error(self):
        """接続エラー → oem_prefix=None"""
        with patch('plugins.module_utils.irmc_client.requests.Session') as mock_session:
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.text = 'Internal Server Error'
            mock_response.headers = CaseInsensitiveDict({})
            mock_session.return_value.request.return_value = mock_response

            irmc = iRMC('192.0.2.1', 'admin', 'password')
            prefix = irmc.oem_prefix

            assert prefix is None

    def test_oem_prefix_cached_with_vendor(self):
        """vendorとoem_prefixは同じキャッシュを使用"""
        with patch('plugins.module_utils.irmc_client.requests.Session') as mock_session:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = '{"Vendor": "ts_fujitsu"}'
            mock_response.json.return_value = {"Vendor": "ts_fujitsu"}
            mock_response.headers = CaseInsensitiveDict({})
            mock_session.return_value.request.return_value = mock_response

            irmc = iRMC('192.0.2.1', 'admin', 'password')

            # vendor取得
            vendor = irmc.vendor
            assert vendor == 'ts_fujitsu'

            # oem_prefix取得（キャッシュから）
            prefix = irmc.oem_prefix
            assert prefix == 'FTS'

            # GETは1回のみ
            assert mock_session.return_value.request.call_count == 1


class TestParseIRMCVersionFromServerHeader:
    """_parse_irmc_version_from_server_header()のテストクラス"""

    def test_standard_format(self):
        """標準的なフォーマット: "iRMC S6 Server" → "S6" """
        result = _parse_irmc_version_from_server_header('iRMC S6 Server')
        assert result == 'S6'

    def test_uppercase(self):
        """大文字フォーマット: "IRMC S7 SERVER" → "S7" """
        result = _parse_irmc_version_from_server_header('IRMC S7 SERVER')
        assert result == 'S7'

    def test_lowercase(self):
        """小文字フォーマット: "irmc s8 server" → "S8" """
        result = _parse_irmc_version_from_server_header('irmc s8 server')
        assert result == 'S8'

    def test_multiple_whitespace(self):
        """複数の空白を含むフォーマット: "irmc  s10  server" → "S10" """
        result = _parse_irmc_version_from_server_header('irmc  s10  server')
        assert result == 'S10'

    def test_multi_digit_version(self):
        """2桁以上のバージョン番号: "iRMC S12 Server" → "S12" """
        result = _parse_irmc_version_from_server_header('iRMC S12 Server')
        assert result == 'S12'

    def test_trailing_chars(self):
        """後続文字列を含む: "iRMC S6 Server/12345" → "S6" """
        result = _parse_irmc_version_from_server_header('iRMC S6 Server/12345')
        assert result == 'S6'

    def test_none_input(self):
        """None入力 → None"""
        result = _parse_irmc_version_from_server_header(None)
        assert result is None

    def test_empty_string(self):
        """空文字列 → None"""
        result = _parse_irmc_version_from_server_header('')
        assert result is None

    def test_no_match(self):
        """パターンにマッチしない文字列 → None"""
        result = _parse_irmc_version_from_server_header('Apache/2.4.41')
        assert result is None

    def test_only_irmc(self):
        """iRMCのみでバージョン番号なし → None"""
        result = _parse_irmc_version_from_server_header('iRMC')
        assert result is None


class TestIRMCVersion:
    """iRMC.versionプロパティのテストクラス"""

    def test_version_success(self):
        """正常系: Serverヘッダーから"S6"を抽出"""
        with patch('plugins.module_utils.irmc_client.requests.Session') as mock_session:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = '{"Name": "iRMC"}'
            mock_response.json.return_value = {"Name": "iRMC"}
            mock_response.headers = CaseInsensitiveDict({'Server': 'iRMC S6 Server'})
            mock_session.return_value.request.return_value = mock_response

            irmc = iRMC('192.0.2.1', 'admin', 'password')
            version = irmc.version

            assert version == 'S6'

    def test_version_connection_error(self):
        """接続エラー → None（リトライ）"""
        with patch('plugins.module_utils.irmc_client.requests.Session') as mock_session:
            # 1回目: エラー
            mock_response1 = MagicMock()
            mock_response1.status_code = 500
            mock_response1.text = 'Internal Server Error'
            mock_response1.headers = CaseInsensitiveDict({'Server': 'iRMC S6 Server'})

            # 2回目: 成功
            mock_response2 = MagicMock()
            mock_response2.status_code = 200
            mock_response2.text = '{"Name": "iRMC"}'
            mock_response2.json.return_value = {"Name": "iRMC"}
            mock_response2.headers = CaseInsensitiveDict({'Server': 'iRMC S6 Server'})

            mock_session.return_value.request.side_effect = [mock_response1, mock_response2]

            irmc = iRMC('192.0.2.1', 'admin', 'password')

            # 1回目の呼び出し: エラーなのでNone
            version1 = irmc.version
            assert version1 is None

            # 2回目の呼び出し: リトライして成功
            version2 = irmc.version
            assert version2 == 'S6'

            # GETが2回実行されたことを確認（エラー時はキャッシュされない）
            assert mock_session.return_value.request.call_count == 2

    def test_version_cache(self):
        """キャッシュ動作確認: 2回目のアクセスでGETされない"""
        with patch('plugins.module_utils.irmc_client.requests.Session') as mock_session:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = '{"Name": "iRMC"}'
            mock_response.json.return_value = {"Name": "iRMC"}
            mock_response.headers = CaseInsensitiveDict({'Server': 'iRMC S6 Server'})
            mock_session.return_value.request.return_value = mock_response

            irmc = iRMC('192.0.2.1', 'admin', 'password')

            # 1回目
            version1 = irmc.version
            assert version1 == 'S6'

            # 2回目
            version2 = irmc.version
            assert version2 == 'S6'

            # GETは1回のみ実行される（2回目はキャッシュから取得）
            assert mock_session.return_value.request.call_count == 1

    def test_version_and_vendor_together(self):
        """vendorとversionの同時使用: 同じGETをキャッシュから取得"""
        with patch('plugins.module_utils.irmc_client.requests.Session') as mock_session:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = '{"Name": "iRMC", "Vendor": "ts_fujitsu"}'
            mock_response.json.return_value = {"Name": "iRMC", "Vendor": "ts_fujitsu"}
            mock_response.headers = CaseInsensitiveDict({'Server': 'iRMC S6 Server'})
            mock_session.return_value.request.return_value = mock_response

            irmc = iRMC('192.0.2.1', 'admin', 'password')

            # vendorを取得
            vendor = irmc.vendor
            assert vendor == 'ts_fujitsu'

            # versionを取得（同じ /redfish/v1 なのでキャッシュから取得）
            version = irmc.version
            assert version == 'S6'

            # GETは1回のみ実行される（vendorとversionで共有）
            assert mock_session.return_value.request.call_count == 1


class TestContentTypeAutoDetection:
    """Content-Type自動判定のテスト"""

    @patch('requests.Session')
    def test_post_auto_detect_multipart(self, mock_session_class):
        """MultipartEncoderでContent-Type自動判定"""
        from requests_toolbelt import MultipartEncoder

        # モックの設定
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'status': 'success'}
        mock_response.headers = {'Content-Type': 'application/json'}
        mock_response.text = '{"status": "success"}'
        mock_response.connection = Mock()
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        # MultipartEncoderを作成
        multipart_data = MultipartEncoder(
            fields={'data': ('test.bin', b'binary data', 'application/octet-stream')}
        )

        # テスト実行
        irmc = iRMC('192.0.2.1', 'admin', 'password', validate_certs=False)
        response = irmc.post('/some/path', multipart_data)

        # 検証: リクエストが送信された
        assert mock_session.request.called
        call_kwargs = mock_session.request.call_args[1]

        # Content-Typeが自動設定されている
        assert 'Content-Type' in call_kwargs['headers']
        assert call_kwargs['headers']['Content-Type'].startswith('multipart/form-data')
        assert 'boundary=' in call_kwargs['headers']['Content-Type']

        # AcceptはJSON（iRMC仕様）
        assert call_kwargs['headers']['Accept'] == 'application/json'

        # bodyがMultipartEncoderのまま渡されている
        assert call_kwargs['data'] is multipart_data

        # レスポンスの検証
        assert response.status == 200
        assert response.body == {'status': 'success'}

    @patch('requests.Session')
    def test_post_auto_detect_xml(self, mock_session_class):
        """XML文字列でContent-Type自動判定"""
        # モックの設定
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '<?xml version="1.0"?><response>OK</response>'
        mock_response.json.side_effect = ValueError('Not JSON')  # XMLなのでJSONパースは失敗
        mock_response.headers = {'Content-Type': 'application/xml'}
        mock_response.connection = Mock()
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        # XML文字列
        xml_body = '<?xml version="1.0"?><ConfigSpace><Test>value</Test></ConfigSpace>'

        # テスト実行
        irmc = iRMC('192.0.2.1', 'admin', 'password', validate_certs=False)
        response = irmc.post('/config', xml_body)

        # 検証: リクエストが送信された
        assert mock_session.request.called
        call_kwargs = mock_session.request.call_args[1]

        # Content-TypeとAcceptが自動設定されている
        assert call_kwargs['headers']['Content-Type'] == 'application/xml'
        assert call_kwargs['headers']['Accept'] == 'application/xml'

        # bodyがそのまま渡されている
        assert call_kwargs['data'] == xml_body

        # レスポンスの検証
        assert response.status == 200
        assert response.body == '<?xml version="1.0"?><response>OK</response>'

    @patch('requests.Session')
    def test_post_override_content_type(self, mock_session_class):
        """ユーザー指定で自動判定を上書き"""
        # モックの設定
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = 'plain text response'
        mock_response.json.side_effect = ValueError('Not JSON')
        mock_response.headers = {'Content-Type': 'text/plain'}
        mock_response.connection = Mock()
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        # XML文字列（通常は application/xml になるはず）
        xml_body = '<?xml version="1.0"?><Test>value</Test>'

        # ユーザーが明示的にContent-Typeを指定
        custom_headers = {'Content-Type': 'text/plain'}

        # テスト実行
        irmc = iRMC('192.0.2.1', 'admin', 'password', validate_certs=False)
        response = irmc.post('/some/path', xml_body, headers=custom_headers)

        # 検証
        assert mock_session.request.called
        call_kwargs = mock_session.request.call_args[1]

        # ユーザー指定のContent-Typeが優先される（自動判定は無視）
        assert call_kwargs['headers']['Content-Type'] == 'text/plain'

        # レスポンスの検証
        assert response.status == 200

    @patch('requests.Session')
    def test_post_dict_uses_default_json(self, mock_session_class):
        """dictはデフォルトのapplication/jsonを使用（後方互換性）"""
        # モックの設定
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'result': 'OK'}
        mock_response.headers = {'Content-Type': 'application/json'}
        mock_response.text = '{"result": "OK"}'
        mock_response.connection = Mock()
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        # dictボディ
        dict_body = {'key': 'value', 'number': 123}

        # テスト実行
        irmc = iRMC('192.0.2.1', 'admin', 'password', validate_certs=False)
        response = irmc.post('/some/path', dict_body)

        # 検証
        assert mock_session.request.called
        call_kwargs = mock_session.request.call_args[1]

        # デフォルトのapplication/jsonが使用される
        assert call_kwargs['headers']['Content-Type'] == 'application/json'

        # bodyがJSON文字列化されている
        import json
        assert call_kwargs['data'] == json.dumps(dict_body)

        # レスポンスの検証
        assert response.status == 200
        assert response.body == {'result': 'OK'}

    @patch('requests.Session')
    def test_post_lowercase_headers_override(self, mock_session_class):
        """小文字ヘッダーでも正しく上書き（CaseInsensitiveDict動作確認）"""
        # モックの設定
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = 'plain text'
        mock_response.json.side_effect = ValueError('Not JSON')
        mock_response.headers = {'Content-Type': 'text/plain'}
        mock_response.connection = Mock()
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        # XML文字列（通常はContent-Type: application/xml, Accept: application/xml）
        xml_body = '<?xml version="1.0"?><Test>value</Test>'

        # ユーザーが小文字でヘッダーを指定
        custom_headers = {
            'content-type': 'text/plain',
            'accept': 'text/html'
        }

        # テスト実行
        irmc = iRMC('192.0.2.1', 'admin', 'password', validate_certs=False)
        response = irmc.post('/some/path', xml_body, headers=custom_headers)

        # 検証
        assert mock_session.request.called
        call_kwargs = mock_session.request.call_args[1]

        # 小文字で指定したヘッダーが優先される（CaseInsensitiveDictの動作）
        # ヘッダー名の大文字小文字は変わる可能性があるが、値は確実に上書きされる
        headers = call_kwargs['headers']
        # Content-Typeの値がtext/plain
        assert headers.get('Content-Type') == 'text/plain' or headers.get('content-type') == 'text/plain'
        # Acceptの値がtext/html
        assert headers.get('Accept') == 'text/html' or headers.get('accept') == 'text/html'

        # レスポンスの検証
        assert response.status == 200
