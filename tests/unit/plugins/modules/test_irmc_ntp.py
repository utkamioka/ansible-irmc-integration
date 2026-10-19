#!/usr/bin/python

# Copyright 2018-2026 Fsas Technologies Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""irmc_ntpモジュールのユニットテストです。"""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import copy
from unittest.mock import Mock, call, patch

import pytest

from ansible_collections.fsas.primergy.plugins.module_utils.errors import HttpError, ModuleError
from ansible_collections.fsas.primergy.plugins.module_utils.irmc_client import Request, Response
from ansible_collections.fsas.primergy.plugins.modules.irmc_ntp import NtpController

# vendorごとのテスト（ts_fujitsu: M7以前、Fsas: M8以降）
VENDORS = [
    pytest.param('ts_fujitsu', id='ts_fujitsu'),
    pytest.param('Fsas', id='Fsas'),
]


def time_path(vendor):
    """時刻設定リソースのパスを返します。"""
    return f'/redfish/v1/Managers/iRMC/Oem/{vendor}/iRMCConfiguration/Time'


def ntp_server_path(vendor, index):
    """NTPサーバー設定リソースのパスを返します。"""
    return f'{time_path(vendor)}/NtpServers/{index}'


def initial_state(vendor):
    """iRMCの初期状態（実機データ、68の時刻設定）を返します。"""
    return {
        time_path(vendor): {
            'TimeZoneOffset': 0,
            'SyncSource': 'iRMC',
            'TimeZone': 'Asia/Tokyo',
            'RtcMode': 'LocalTime',
            '@odata.etag': '1792432309',
        },
        ntp_server_path(vendor, 0): {
            'Id': '0',
            'NtpServerName': '10.118.65.1',
            '@odata.etag': '1792187880',
        },
        ntp_server_path(vendor, 1): {
            'Id': '1',
            'NtpServerName': '10.1.0.67',
            '@odata.etag': '1792187880',
        },
    }


class FakeIrmc:
    """リソースの状態を保持し、PATCHで状態が変わるモックiRMCクライアントです。

    get / patch はMockなので、呼び出し内容をアサートできます。
    """

    def __init__(self, vendor, state=None, patch_status=None):
        """FakeIrmcを初期化します。

        引数:
            vendor - ベンダー名（"ts_fujitsu" または "Fsas"）
            state - パスごとのリソースのボディ（省略時は initial_state()）
            patch_status - パスごとのPATCHのステータス（省略時は200）
        """
        self.vendor = vendor
        self.oem_prefix = 'FTS' if vendor == 'ts_fujitsu' else 'Fsas'
        self.state = state if state is not None else initial_state(vendor)
        self.patch_status = patch_status or {}
        self.get = Mock(side_effect=self._get)
        self.patch = Mock(side_effect=self._patch)

    def _get(self, path, use_cache=True):
        if path not in self.state:
            return Response(body={}, headers={}, status=404, request=Request('GET', path))
        return Response(body=copy.deepcopy(self.state[path]), headers={}, status=200, request=Request('GET', path))

    def _patch(self, path, body, headers=None):
        status = self.patch_status.get(path, 200)
        if status != 200:
            return Response(
                body={'error': {'code': 'Fsas.1.0.PropertyValueNotInList', 'message': 'The value is not allowed.'}},
                headers={},
                status=status,
                request=Request('PATCH', path),
            )
        self.state[path].update(body)
        return Response(body=copy.deepcopy(self.state[path]), headers={}, status=200, request=Request('PATCH', path))

    def patched_paths(self):
        """PATCHされたパスを順番に返します。"""
        return [c.args[0] for c in self.patch.call_args_list]


class TestNtpController:
    """NtpControllerクラスのテストです。"""

    @pytest.fixture(params=VENDORS)
    def vendor(self, request):
        """ベンダー名を返すfixtureです。"""
        return request.param

    @pytest.fixture
    def irmc(self, vendor):
        """初期状態のFakeIrmcを返すfixtureです。"""
        return FakeIrmc(vendor)

    @pytest.fixture
    def mock_logger(self):
        """モックLoggerを返すfixtureです。"""
        return Mock()

    @pytest.fixture
    def controller(self, irmc, mock_logger):
        """NtpControllerインスタンスを返すfixtureです。"""
        return NtpController(irmc, mock_logger)

    # ---- get ----

    def test_get_state_redfish_values(self, controller, irmc):
        """get_state: 既定ではRedfishの値がそのまま返ることのテストです。"""
        result = controller.get_state({})

        assert result.changed is False
        assert result.extra_fields['time_settings'] == {
            'time_mode': 'iRMC',
            'rtc_mode': 'LocalTime',
            'time_zone_location': 'Asia/Tokyo',
            'ntp_server_primary': '10.118.65.1',
            'ntp_server_secondary': '10.1.0.67',
        }
        irmc.patch.assert_not_called()

    def test_get_state_legacy_output(self, controller, irmc):
        """get_state: legacy_output=trueでRedfishの値が旧仕様の表記に変換されることのテストです。"""
        result = controller.get_state({'legacy_output': True})

        assert result.extra_fields['time_settings'] == {
            'time_mode': 'System RTC',
            'rtc_mode': 'local time',
            'time_zone_location': 'Asia/Tokyo',
            'ntp_server_primary': '10.118.65.1',
            'ntp_server_secondary': '10.1.0.67',
        }

    @pytest.mark.parametrize(('legacy_output', 'expected'), [
        (False, ('NTP', 'UTC')),
        (True, ('NTP', 'UTC/GMT')),
    ], ids=['redfish', 'legacy'])
    def test_get_state_ntp_utc(self, controller, irmc, vendor, legacy_output, expected):
        """get_state: SyncSource=NTP、RtcMode=UTCの出力のテストです。"""
        irmc.state[time_path(vendor)].update({'SyncSource': 'NTP', 'RtcMode': 'UTC'})

        settings = controller.get_state({'legacy_output': legacy_output}).extra_fields['time_settings']

        assert (settings['time_mode'], settings['rtc_mode']) == expected

    def test_get_state_unknown_value_legacy(self, controller, irmc, vendor, mock_logger):
        """get_state: legacy_output=trueで変換表にない値はそのまま返し、警告を出すことのテストです。"""
        irmc.state[time_path(vendor)]['SyncSource'] = 'MMB'

        settings = controller.get_state({'legacy_output': True}).extra_fields['time_settings']

        assert settings['time_mode'] == 'MMB'
        mock_logger.warn.assert_called_once()
        assert "'MMB'" in mock_logger.warn.call_args.args[0]

    def test_get_state_unknown_value_redfish(self, controller, irmc, vendor, mock_logger):
        """get_state: 既定ではRedfishの値をそのまま返すので、未知の値でも警告しないことのテストです。"""
        irmc.state[time_path(vendor)]['SyncSource'] = 'MMB'

        settings = controller.get_state({}).extra_fields['time_settings']

        assert settings['time_mode'] == 'MMB'
        mock_logger.warn.assert_not_called()

    def test_get_state_http_error(self, controller, irmc, vendor):
        """get_state: GETが失敗した場合のテストです。"""
        del irmc.state[ntp_server_path(vendor, 1)]

        with pytest.raises(HttpError) as exc_info:
            controller.get_state({})

        assert exc_info.value.status == 404
        assert f'Failed to GET {ntp_server_path(vendor, 1)}' in exc_info.value.message

    def test_get_state_vendor_unknown(self, controller, irmc):
        """get_state: ベンダーを判別できない場合のテストです。"""
        irmc.vendor = None

        with pytest.raises(ModuleError) as exc_info:
            controller.get_state({})

        assert 'vendor' in exc_info.value.message
        irmc.get.assert_not_called()

    # ---- set ----

    def test_set_state_no_parameter(self, controller, irmc):
        """set_state: 変更対象のパラメータが1つもない場合は、何もせずchanged=Falseになることのテストです。"""
        result = controller.set_state({'time_mode': None, 'ntp_server_primary': None})

        assert result.changed is False
        assert result.skipped is False
        assert 'No option to change' in result.msg
        assert result.extra_fields['time_settings']['time_mode'] == 'iRMC'
        irmc.patch.assert_not_called()

    def test_set_state_no_change(self, controller, irmc):
        """set_state: すべて現在値と同じ場合はPATCHせずchanged=Falseになることのテストです。"""
        result = controller.set_state({
            'time_mode': 'System RTC',
            'rtc_mode': 'local time',
            'time_zone_location': 'Asia/Tokyo',
            'ntp_server_primary': '10.118.65.1',
            'ntp_server_secondary': '10.1.0.67',
        })

        assert result.changed is False
        assert result.skipped is False
        assert 'already' in result.msg
        assert result.extra_fields['time_settings']['time_mode'] == 'iRMC'
        irmc.patch.assert_not_called()

    def test_set_state_no_change_legacy_output(self, controller, irmc):
        """set_state: legacy_output=trueでは、変更なしの場合も旧仕様の表記で返すことのテストです。"""
        result = controller.set_state({'time_mode': 'System RTC', 'legacy_output': True})

        assert result.changed is False
        assert result.extra_fields['time_settings']['time_mode'] == 'System RTC'
        assert result.extra_fields['time_settings']['rtc_mode'] == 'local time'

    @pytest.mark.parametrize(('time_mode', 'rtc_mode'), [
        ('System RTC', 'local time'),
        ('iRMC', 'LocalTime'),
    ], ids=['legacy', 'redfish'])
    def test_set_state_no_change_either_notation(self, controller, irmc, time_mode, rtc_mode):
        """set_state: 旧仕様とRedfishのどちらの表記でも、現在値と同じなら差分なしになることのテストです。"""
        result = controller.set_state({'time_mode': time_mode, 'rtc_mode': rtc_mode})

        assert result.changed is False
        irmc.patch.assert_not_called()

    @pytest.mark.parametrize(('time_mode', 'rtc_mode'), [
        ('NTP', 'UTC/GMT'),
        ('NTP', 'UTC'),
    ], ids=['legacy', 'redfish'])
    def test_set_state_time_only(self, controller, irmc, vendor, time_mode, rtc_mode):
        """set_state: Timeだけ差分がある場合、差分の項目だけをRedfishの値でPATCHすることのテストです。"""
        result = controller.set_state({
            'time_mode': time_mode,
            'rtc_mode': rtc_mode,
            'time_zone_location': 'Asia/Tokyo',  # 現在値と同じ
        })

        assert result.changed is True
        irmc.patch.assert_called_once_with(
            time_path(vendor),
            {'SyncSource': 'NTP', 'RtcMode': 'UTC'},
            headers={'If-Match': '1792432309'},
        )
        assert result.extra_fields['time_settings']['time_mode'] == 'NTP'
        assert result.extra_fields['time_settings']['rtc_mode'] == 'UTC'

    def test_set_state_ntp_server_only(self, controller, irmc, vendor):
        """set_state: NTPサーバーだけ差分がある場合、該当するリソースだけPATCHすることのテストです。"""
        result = controller.set_state({
            'ntp_server_primary': '10.118.65.1',  # 現在値と同じ
            'ntp_server_secondary': '192.0.2.2',
        })

        assert result.changed is True
        irmc.patch.assert_called_once_with(
            ntp_server_path(vendor, 1),
            {'NtpServerName': '192.0.2.2'},
            headers={'If-Match': '1792187880'},
        )

    def test_set_state_ntp_server_empty_string(self, controller, irmc, vendor):
        """set_state: NTPサーバーに空文字を指定した場合はそのままPATCHすることのテストです。"""
        result = controller.set_state({'ntp_server_secondary': ''})

        assert result.changed is True
        irmc.patch.assert_called_once_with(
            ntp_server_path(vendor, 1),
            {'NtpServerName': ''},
            headers={'If-Match': '1792187880'},
        )

    def test_set_state_all_changed(self, controller, irmc, vendor):
        """set_state: すべて差分がある場合、Time -> プライマリ -> セカンダリの順にPATCHすることのテストです。"""
        result = controller.set_state({
            'time_mode': 'NTP',
            'rtc_mode': 'UTC/GMT',
            'time_zone_location': 'Europe/Berlin',
            'ntp_server_primary': '192.0.2.1',
            'ntp_server_secondary': '192.0.2.2',
        })

        assert result.changed is True
        assert irmc.patched_paths() == [
            time_path(vendor),
            ntp_server_path(vendor, 0),
            ntp_server_path(vendor, 1),
        ]
        assert irmc.patch.call_args_list[0] == call(
            time_path(vendor),
            {'SyncSource': 'NTP', 'RtcMode': 'UTC', 'TimeZone': 'Europe/Berlin'},
            headers={'If-Match': '1792432309'},
        )
        assert result.extra_fields['time_settings'] == {
            'time_mode': 'NTP',
            'rtc_mode': 'UTC',
            'time_zone_location': 'Europe/Berlin',
            'ntp_server_primary': '192.0.2.1',
            'ntp_server_secondary': '192.0.2.2',
        }

    def test_set_state_changed_legacy_output(self, controller, irmc):
        """set_state: legacy_output=trueでは、変更後の値を旧仕様の表記で返すことのテストです。"""
        result = controller.set_state({'rtc_mode': 'UTC', 'legacy_output': True})

        assert result.changed is True
        assert result.extra_fields['time_settings']['time_mode'] == 'System RTC'
        assert result.extra_fields['time_settings']['rtc_mode'] == 'UTC/GMT'

    def test_set_state_refetch_without_cache(self, controller, irmc, vendor):
        """set_state: ETagと変更後の値はキャッシュを使わずに取得することのテストです。"""
        controller.set_state({'time_mode': 'NTP'})

        uncached = [c.args[0] for c in irmc.get.call_args_list if c.kwargs.get('use_cache') is False]
        # ETag取得のためのTime、変更後の値の取得のためのTime / プライマリ / セカンダリ
        assert uncached == [
            time_path(vendor),
            time_path(vendor),
            ntp_server_path(vendor, 0),
            ntp_server_path(vendor, 1),
        ]

    def test_set_state_patch_failure(self, controller, irmc, vendor):
        """set_state: PATCHが失敗した場合のテストです。"""
        irmc.patch_status[time_path(vendor)] = 400

        with pytest.raises(HttpError) as exc_info:
            controller.set_state({'time_zone_location': 'Invalid/Zone'})

        assert exc_info.value.status == 400
        assert f'Failed to PATCH {time_path(vendor)}' in exc_info.value.message
        assert 'The value is not allowed.' in exc_info.value.message
        assert 'already changed' not in exc_info.value.message

    def test_set_state_partial_failure(self, controller, irmc, vendor):
        """set_state: 途中のPATCHが失敗した場合、変更済みのリソースがメッセージに含まれることのテストです。"""
        irmc.patch_status[ntp_server_path(vendor, 1)] = 400

        with pytest.raises(HttpError) as exc_info:
            controller.set_state({
                'time_mode': 'NTP',
                'ntp_server_primary': '192.0.2.1',
                'ntp_server_secondary': '192.0.2.2',
            })

        message = exc_info.value.message
        assert f'Failed to PATCH {ntp_server_path(vendor, 1)}' in message
        assert f'already changed: {time_path(vendor)}, {ntp_server_path(vendor, 0)}' in message

    def test_set_state_vendor_unknown(self, controller, irmc):
        """set_state: ベンダーを判別できない場合のテストです。"""
        irmc.vendor = None

        with pytest.raises(ModuleError) as exc_info:
            controller.set_state({'time_mode': 'NTP'})

        assert 'vendor' in exc_info.value.message
        irmc.patch.assert_not_called()


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
            'time_mode': None,
            'rtc_mode': None,
            'time_zone_location': None,
            'ntp_server_primary': None,
            'ntp_server_secondary': None,
            'legacy_output': False,
        }
        module._verbosity = 0
        return module

    @pytest.fixture
    def mock_logger(self):
        """to_logs_dict()が空辞書を返すモックLoggerを返すfixtureです。"""
        logger = Mock()
        logger.to_logs_dict.return_value = {}
        return logger

    @patch('ansible_collections.fsas.primergy.plugins.modules.irmc_ntp.iRMC')
    @patch('ansible_collections.fsas.primergy.plugins.modules.irmc_ntp.AnsibleLogger')
    def test_get_command_success(self, mock_logger_class, mock_irmc_class, mock_module, mock_logger):
        """get command: 正常系の統合テストです。"""
        from ansible_collections.fsas.primergy.plugins.modules.irmc_ntp import irmc_ntp

        mock_logger_class.return_value = mock_logger
        mock_irmc_class.return_value = FakeIrmc('Fsas')

        irmc_ntp(mock_module)

        mock_module.exit_json.assert_called_once()
        call_kwargs = mock_module.exit_json.call_args[1]
        assert call_kwargs['changed'] is False
        assert call_kwargs['time_settings']['time_mode'] == 'iRMC'
        mock_module.fail_json.assert_not_called()

    @patch('ansible_collections.fsas.primergy.plugins.modules.irmc_ntp.iRMC')
    @patch('ansible_collections.fsas.primergy.plugins.modules.irmc_ntp.AnsibleLogger')
    def test_get_command_legacy_output(self, mock_logger_class, mock_irmc_class, mock_module, mock_logger):
        """get command: legacy_output=trueで旧仕様の表記が返ることの統合テストです。"""
        from ansible_collections.fsas.primergy.plugins.modules.irmc_ntp import irmc_ntp

        mock_module.params['legacy_output'] = True
        mock_logger_class.return_value = mock_logger
        mock_irmc_class.return_value = FakeIrmc('Fsas')

        irmc_ntp(mock_module)

        call_kwargs = mock_module.exit_json.call_args[1]
        assert call_kwargs['time_settings']['time_mode'] == 'System RTC'
        assert call_kwargs['time_settings']['rtc_mode'] == 'local time'

    @patch('ansible_collections.fsas.primergy.plugins.modules.irmc_ntp.iRMC')
    @patch('ansible_collections.fsas.primergy.plugins.modules.irmc_ntp.AnsibleLogger')
    def test_set_command_success(self, mock_logger_class, mock_irmc_class, mock_module, mock_logger):
        """set command: 正常系の統合テストです。"""
        from ansible_collections.fsas.primergy.plugins.modules.irmc_ntp import irmc_ntp

        mock_module.params['command'] = 'set'
        mock_module.params['time_mode'] = 'NTP'
        mock_logger_class.return_value = mock_logger
        mock_irmc_class.return_value = FakeIrmc('Fsas')

        irmc_ntp(mock_module)

        mock_module.exit_json.assert_called_once()
        call_kwargs = mock_module.exit_json.call_args[1]
        assert call_kwargs['changed'] is True
        assert call_kwargs['time_settings']['time_mode'] == 'NTP'
        mock_module.fail_json.assert_not_called()

    @patch('ansible_collections.fsas.primergy.plugins.modules.irmc_ntp.iRMC')
    @patch('ansible_collections.fsas.primergy.plugins.modules.irmc_ntp.AnsibleLogger')
    def test_set_command_no_parameter(self, mock_logger_class, mock_irmc_class, mock_module, mock_logger):
        """set command: パラメータ未指定（変数なしでroleを呼んだ場合）はok（changed=False）になることのテストです。"""
        from ansible_collections.fsas.primergy.plugins.modules.irmc_ntp import irmc_ntp

        mock_module.params['command'] = 'set'
        mock_logger_class.return_value = mock_logger
        irmc = FakeIrmc('Fsas')
        mock_irmc_class.return_value = irmc

        irmc_ntp(mock_module)

        mock_module.exit_json.assert_called_once()
        call_kwargs = mock_module.exit_json.call_args[1]
        assert call_kwargs['changed'] is False
        assert 'No option to change' in call_kwargs['msg']
        irmc.patch.assert_not_called()
        mock_module.fail_json.assert_not_called()

    @patch('ansible_collections.fsas.primergy.plugins.modules.irmc_ntp.iRMC')
    @patch('ansible_collections.fsas.primergy.plugins.modules.irmc_ntp.AnsibleLogger')
    def test_http_error_handling(self, mock_logger_class, mock_irmc_class, mock_module, mock_logger):
        """HTTPエラーハンドリングのテストです。"""
        from ansible_collections.fsas.primergy.plugins.modules.irmc_ntp import irmc_ntp

        mock_module.params['command'] = 'set'
        mock_module.params['time_zone_location'] = 'Invalid/Zone'
        mock_logger_class.return_value = mock_logger
        mock_irmc_class.return_value = FakeIrmc('Fsas', patch_status={time_path('Fsas'): 400})

        irmc_ntp(mock_module)

        mock_module.fail_json.assert_called_once()
        call_kwargs = mock_module.fail_json.call_args[1]
        assert call_kwargs['status'] == 400
        assert 'The value is not allowed.' in call_kwargs['msg']
        mock_module.exit_json.assert_not_called()

    @patch('ansible_collections.fsas.primergy.plugins.modules.irmc_ntp.iRMC')
    @patch('ansible_collections.fsas.primergy.plugins.modules.irmc_ntp.AnsibleLogger')
    def test_unexpected_error_handling(self, mock_logger_class, mock_irmc_class, mock_module, mock_logger):
        """予期しない例外（接続エラー等）のハンドリングのテストです。"""
        from ansible_collections.fsas.primergy.plugins.modules.irmc_ntp import irmc_ntp

        mock_logger_class.return_value = mock_logger
        irmc = FakeIrmc('Fsas')
        irmc.get.side_effect = ConnectionError('connection refused')
        mock_irmc_class.return_value = irmc

        irmc_ntp(mock_module)

        mock_module.fail_json.assert_called_once()
        call_kwargs = mock_module.fail_json.call_args[1]
        assert 'Unexpected error: connection refused' in call_kwargs['msg']
        assert 'exception' in call_kwargs

    @patch('ansible_collections.fsas.primergy.plugins.modules.irmc_ntp.iRMC')
    @patch('ansible_collections.fsas.primergy.plugins.modules.irmc_ntp.AnsibleLogger')
    def test_check_mode(self, mock_logger_class, mock_irmc_class, mock_module):
        """check_mode時はiRMCにアクセスせずに終了することのテストです。"""
        from ansible_collections.fsas.primergy.plugins.modules.irmc_ntp import irmc_ntp

        mock_module.check_mode = True
        # 実際のexit_json()と同様に処理を終了させる
        mock_module.exit_json.side_effect = SystemExit

        with pytest.raises(SystemExit):
            irmc_ntp(mock_module)

        mock_module.exit_json.assert_called_once_with(changed=False, msg='module was not run')
        mock_irmc_class.assert_not_called()
