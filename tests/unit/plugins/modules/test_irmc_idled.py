#!/usr/bin/python

# Copyright 2018-2026 Fsas Technologies Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""irmc_idledモジュールのユニットテストです。"""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from unittest.mock import Mock, patch

import pytest

from ansible_collections.fsas.primergy.plugins.module_utils.controller_result import ControllerResult
from ansible_collections.fsas.primergy.plugins.module_utils.errors import HttpError, ModuleError, ValidationError
from ansible_collections.fsas.primergy.plugins.module_utils.irmc_client import Request, Response
from ansible_collections.fsas.primergy.plugins.modules.irmc_idled import IdLedController


class TestIdLedController:
    """IdLedControllerクラスのテストです。"""

    @pytest.fixture
    def mock_irmc(self):
        """モックiRMCクライアントを返すfixtureです。"""
        return Mock()

    @pytest.fixture
    def mock_logger(self):
        """モックLoggerを返すfixtureです。"""
        return Mock()

    @pytest.fixture
    def controller(self, mock_irmc, mock_logger):
        """IdLedControllerインスタンスを返すfixtureです。"""
        return IdLedController(mock_irmc, mock_logger)

    @pytest.fixture
    def system_response_lit(self):
        """LED状態='Lit'のシステムレスポンスを返すfixtureです。"""
        return Response(
            body={
                'IndicatorLED': 'Lit',
                'IndicatorLED@Redfish.AllowableValues': ['Off', 'Lit', 'Blinking'],
                '@odata.etag': 'W/"12345"',
            },
            headers={},
            status=200,
            request=Request('GET', '/redfish/v1/Systems/0'),
        )

    @pytest.fixture
    def system_response_off(self):
        """LED状態='Off'のシステムレスポンスを返すfixtureです。"""
        return Response(
            body={
                'IndicatorLED': 'Off',
                'IndicatorLED@Redfish.AllowableValues': ['Off', 'Lit', 'Blinking'],
                '@odata.etag': 'W/"12345"',
            },
            headers={},
            status=200,
            request=Request('GET', '/redfish/v1/Systems/0'),
        )

    def test_fetch_current_led_state_success(self, controller, mock_irmc, system_response_lit):
        """_fetch_current_led_state: 正常系テストです。"""
        mock_irmc.get.return_value = system_response_lit

        state = controller._fetch_current_led_state()

        assert state == 'Lit'
        mock_irmc.get.assert_called_once_with('/redfish/v1/Systems/0')

    def test_fetch_current_led_state_http_error(self, controller, mock_irmc):
        """_fetch_current_led_state: HTTPエラーのテストです。"""
        mock_irmc.get.return_value = Response(
            body='',
            headers={},
            status=500,
            request=Request('GET', '/redfish/v1/Systems/0'),
        )

        with pytest.raises(HttpError) as exc_info:
            controller._fetch_current_led_state()

        assert exc_info.value.status == 500
        assert 'Failed to GET /redfish/v1/Systems/0' in exc_info.value.message

    def test_fetch_current_led_state_missing_field(self, controller, mock_irmc):
        """_fetch_current_led_state: IndicatorLEDフィールドが存在しない場合のテストです。"""
        mock_irmc.get.return_value = Response(
            body={},
            headers={},
            status=200,
            request=Request('GET', '/redfish/v1/Systems/0'),
        )

        with pytest.raises(ModuleError) as exc_info:
            controller._fetch_current_led_state()

        assert "'IndicatorLED' field not found" in exc_info.value.message

    def test_fetch_allowable_led_states_success(self, controller, mock_irmc, system_response_off):
        """_fetch_allowable_led_states: 正常系テストです。"""
        mock_irmc.get.return_value = system_response_off

        allowed = controller._fetch_allowable_led_states()

        assert allowed == ['Off', 'Lit', 'Blinking']
        mock_irmc.get.assert_called_once_with('/redfish/v1/Systems/0')

    def test_fetch_allowable_led_states_http_error(self, controller, mock_irmc):
        """_fetch_allowable_led_states: HTTPエラーのテストです。"""
        mock_irmc.get.return_value = Response(
            body='',
            headers={},
            status=500,
            request=Request('GET', '/redfish/v1/Systems/0'),
        )

        with pytest.raises(HttpError) as exc_info:
            controller._fetch_allowable_led_states()

        assert exc_info.value.status == 500
        assert 'Failed to GET /redfish/v1/Systems/0' in exc_info.value.message

    def test_fetch_allowable_led_states_missing_field(self, controller, mock_irmc):
        """_fetch_allowable_led_states: AllowableValuesフィールドが存在しない場合のテストです。"""
        mock_irmc.get.return_value = Response(
            body={'IndicatorLED': 'Off'},
            headers={},
            status=200,
            request=Request('GET', '/redfish/v1/Systems/0'),
        )

        with pytest.raises(ModuleError) as exc_info:
            controller._fetch_allowable_led_states()

        assert 'field not found' in exc_info.value.message

    def test_get_state_success(self, controller, mock_irmc, system_response_lit):
        """get_state: 正常系テストです。"""
        mock_irmc.get.return_value = system_response_lit

        result = controller.get_state()

        assert isinstance(result, ControllerResult)
        assert result.changed is False
        assert result.skipped is False
        assert result.msg is None
        assert result.extra_fields['idled_state'] == 'Lit'

    def test_set_state_success(self, controller, mock_irmc, system_response_off):
        """set_state: 状態変更成功のテストです。"""
        mock_irmc.get.return_value = system_response_off
        mock_irmc.patch.return_value = Response(body={}, headers={}, status=200)

        result = controller.set_state({'state': 'Lit'})

        assert isinstance(result, ControllerResult)
        assert result.changed is True
        assert result.skipped is False
        assert result.msg is None
        assert mock_irmc.get.call_count == 3
        mock_irmc.patch.assert_called_once()
        patch_call_args = mock_irmc.patch.call_args
        assert patch_call_args[0][0] == '/redfish/v1/Systems/0'
        assert patch_call_args[0][1] == {'IndicatorLED': 'Lit'}
        assert patch_call_args[1]['headers'] == {'If-Match': 'W/"12345"'}

    def test_set_state_already_set(self, controller, mock_irmc, system_response_lit):
        """set_state: 既に目的の状態の場合のテストです。"""
        mock_irmc.get.return_value = system_response_lit

        result = controller.set_state({'state': 'Lit'})

        assert isinstance(result, ControllerResult)
        assert result.changed is False
        assert result.skipped is True
        assert 'already in state' in result.msg
        mock_irmc.patch.assert_not_called()

    def test_set_state_invalid_value(self, controller, mock_irmc, system_response_off):
        """set_state: 無効な状態値のテストです。"""
        mock_irmc.get.return_value = system_response_off

        with pytest.raises(ValidationError) as exc_info:
            controller.set_state({'state': 'Invalid'})

        assert 'Invalid state' in exc_info.value.message
        assert 'Invalid' in exc_info.value.message
        mock_irmc.patch.assert_not_called()

    def test_set_state_patch_failure(self, controller, mock_irmc, system_response_off):
        """set_state: PATCH失敗のテストです。"""
        mock_irmc.get.return_value = system_response_off
        mock_irmc.patch.return_value = Response(
            body='',
            headers={},
            status=500,
            request=Request('PATCH', '/redfish/v1/Systems/0'),
        )

        with pytest.raises(HttpError) as exc_info:
            controller.set_state({'state': 'Lit'})

        assert exc_info.value.status == 500
        assert 'Failed to PATCH /redfish/v1/Systems/0' in exc_info.value.message

    def test_set_state_missing_parameter(self, controller, mock_irmc):
        """set_state: stateパラメータがない場合のテストです。"""
        with pytest.raises(ValidationError) as exc_info:
            controller.set_state({'state': None})

        assert 'state' in exc_info.value.message
        assert 'required' in exc_info.value.message
        mock_irmc.get.assert_not_called()


class TestModuleIntegration:
    """モジュール全体の統合テストです。"""

    @pytest.fixture
    def mock_module(self):
        """モックAnsibleModuleを返すfixtureです。"""
        module = Mock()
        module.check_mode = False
        module.params = {
            'irmc_url': '192.0.2.1',
            'irmc_username': 'admin',
            'irmc_password': 'password',
            'validate_certs': False,
            'command': 'get',
            'state': None,
        }
        module._verbosity = 0
        return module

    @patch('ansible_collections.fsas.primergy.plugins.modules.irmc_idled.iRMC')
    @patch('ansible_collections.fsas.primergy.plugins.modules.irmc_idled.AnsibleLogger')
    def test_get_command_success(self, mock_logger_class, mock_irmc_class, mock_module):
        """get command: 正常系の統合テストです。"""
        from ansible_collections.fsas.primergy.plugins.modules.irmc_idled import irmc_idled

        # モックの設定
        mock_logger = Mock()
        mock_logger.to_logs_dict.return_value = {}
        mock_logger_class.return_value = mock_logger

        mock_irmc = Mock()
        mock_irmc.get.return_value = Response(
            body={'IndicatorLED': 'Blinking'},
            headers={},
            status=200,
            request=Request('GET', '/redfish/v1/Systems/0'),
        )
        mock_irmc_class.return_value = mock_irmc

        # テスト実行
        irmc_idled(mock_module)

        # exit_jsonが呼ばれたことを確認
        mock_module.exit_json.assert_called_once()
        call_kwargs = mock_module.exit_json.call_args[1]
        assert call_kwargs['changed'] is False
        assert call_kwargs['idled_state'] == 'Blinking'
        assert 'msg' not in call_kwargs

    @patch('ansible_collections.fsas.primergy.plugins.modules.irmc_idled.iRMC')
    @patch('ansible_collections.fsas.primergy.plugins.modules.irmc_idled.AnsibleLogger')
    def test_set_command_success(self, mock_logger_class, mock_irmc_class, mock_module):
        """set command: 正常系の統合テストです。"""
        from ansible_collections.fsas.primergy.plugins.modules.irmc_idled import irmc_idled

        # パラメータ変更
        mock_module.params['command'] = 'set'
        mock_module.params['state'] = 'Lit'

        # モックの設定
        mock_logger = Mock()
        mock_logger.to_logs_dict.return_value = {}
        mock_logger_class.return_value = mock_logger

        mock_irmc = Mock()
        mock_irmc.get.return_value = Response(
            body={
                'IndicatorLED': 'Off',
                'IndicatorLED@Redfish.AllowableValues': ['Off', 'Lit', 'Blinking'],
                '@odata.etag': 'W/"12345"',
            },
            headers={},
            status=200,
            request=Request('GET', '/redfish/v1/Systems/0'),
        )
        mock_irmc.patch.return_value = Response(
            body={},
            headers={},
            status=200,
            request=Request('PATCH', '/redfish/v1/Systems/0'),
        )
        mock_irmc_class.return_value = mock_irmc

        # テスト実行
        irmc_idled(mock_module)

        # exit_jsonが呼ばれたことを確認
        mock_module.exit_json.assert_called_once()
        call_kwargs = mock_module.exit_json.call_args[1]
        assert call_kwargs['changed'] is True

    @patch('ansible_collections.fsas.primergy.plugins.modules.irmc_idled.iRMC')
    @patch('ansible_collections.fsas.primergy.plugins.modules.irmc_idled.AnsibleLogger')
    def test_http_error_handling(self, mock_logger_class, mock_irmc_class, mock_module):
        """HTTPエラーハンドリングのテストです。"""
        from ansible_collections.fsas.primergy.plugins.modules.irmc_idled import irmc_idled

        # モックの設定
        mock_logger = Mock()
        mock_logger.to_logs_dict.return_value = {}
        mock_logger_class.return_value = mock_logger

        mock_irmc = Mock()
        mock_irmc.get.return_value = Response(
            body='',
            headers={},
            status=500,
            request=Request('GET', '/redfish/v1/Systems/0'),
        )
        mock_irmc_class.return_value = mock_irmc

        # テスト実行
        irmc_idled(mock_module)

        # fail_jsonが呼ばれたことを確認
        mock_module.fail_json.assert_called_once()
        call_kwargs = mock_module.fail_json.call_args[1]
        assert call_kwargs['status'] == 500
        assert 'Failed to GET /redfish/v1/Systems/0' in call_kwargs['msg']
