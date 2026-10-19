#!/usr/bin/python

# Copyright 2018-2026 Fsas Technologies Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""irmc_licenseモジュールのユニットテストです。"""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from unittest.mock import Mock, patch

import pytest

from ansible_collections.fsas.primergy.plugins.module_utils.errors import HttpError, ModuleError, ValidationError
from ansible_collections.fsas.primergy.plugins.module_utils.irmc_client import Request, Response
from ansible_collections.fsas.primergy.plugins.modules.irmc_license import LicenseController

# vendorごとの (vendor, oem_prefix)（ts_fujitsu: M7以前、Fsas: M8以降）
GENERATIONS = [
    pytest.param(('ts_fujitsu', 'FTS'), id='ts_fujitsu'),
    pytest.param(('Fsas', 'Fsas'), id='Fsas'),
]


def licenses_path(vendor):
    """ライセンス一覧リソースのパスを返します。"""
    return f'/redfish/v1/Managers/iRMC/Oem/{vendor}/iRMCConfiguration/Licenses'


def add_license_path(oem_prefix):
    """ライセンス追加アクションのパスを返します。"""
    return f'/redfish/v1/Managers/iRMC/Actions/Oem/{oem_prefix}Manager.AddLicense'


def licenses_response(vendor, keys):
    """ライセンス一覧のレスポンスを返します。"""
    return Response(
        body={'Keys@odata.count': len(keys), 'Keys': keys},
        headers={},
        status=200,
        request=Request('GET', licenses_path(vendor)),
    )


def invalid_license_response(oem_prefix):
    """不正なライセンスキーを指定した場合のレスポンス（実機データ）を返します。"""
    vendor_code = 'Fujitsu' if oem_prefix == 'FTS' else 'Fsas'
    return Response(
        body={
            'error': {
                '@Message.ExtendedInfo': [
                    {
                        'MessageId': f'{vendor_code}.1.0.InvalidLicenseKey',
                        'Message': 'Invalid license key value provided.',
                        'Severity': 'Critical',
                    },
                ],
                'code': f'{vendor_code}.1.0.InvalidLicenseKey',
                'message': 'Invalid license key value provided.',
            },
        },
        headers={},
        status=400,
        request=Request('POST', add_license_path(oem_prefix)),
    )


class TestLicenseController:
    """LicenseControllerクラスのテストです。"""

    @pytest.fixture(params=GENERATIONS)
    def generation(self, request):
        """(vendor, oem_prefix) を返すfixtureです。"""
        return request.param

    @pytest.fixture
    def mock_irmc(self, generation):
        """vendorごとのvendor/oem_prefixを持つモックiRMCクライアントを返すfixtureです。"""
        vendor, oem_prefix = generation
        irmc = Mock()
        irmc.vendor = vendor
        irmc.oem_prefix = oem_prefix
        return irmc

    @pytest.fixture
    def mock_logger(self):
        """モックLoggerを返すfixtureです。"""
        return Mock()

    @pytest.fixture
    def controller(self, mock_irmc, mock_logger):
        """LicenseControllerインスタンスを返すfixtureです。"""
        return LicenseController(mock_irmc, mock_logger)

    def test_get_state_permanent(self, controller, mock_irmc, generation):
        """get_state: 永続ライセンス（RemainingTimeHなし）の正常系テストです。"""
        vendor, _ = generation
        mock_irmc.get.return_value = licenses_response(vendor, [
            {'Name': 'KVM', 'Type': 'Permanent'},
            {'Name': 'MEDIA', 'Type': 'Permanent'},
            {'Name': 'eLCM', 'Type': 'Permanent'},
        ])

        result = controller.get_state()

        assert result.changed is False
        assert result.extra_fields['licenses'] == [
            {'name': 'KVM', 'type': 'Permanent'},
            {'name': 'MEDIA', 'type': 'Permanent'},
            {'name': 'eLCM', 'type': 'Permanent'},
        ]
        mock_irmc.get.assert_called_once_with(licenses_path(vendor))

    def test_get_state_temporary(self, controller, mock_irmc, generation):
        """get_state: 一時ライセンス（RemainingTimeHあり）の正常系テストです。"""
        vendor, _ = generation
        mock_irmc.get.return_value = licenses_response(vendor, [
            {'Name': 'KVM', 'Type': 'Temporary', 'RemainingTimeH': 22562},
        ])

        result = controller.get_state()

        assert result.extra_fields['licenses'] == [
            {'name': 'KVM', 'type': 'Temporary', 'remaining_time_h': 22562},
        ]

    def test_get_state_empty(self, controller, mock_irmc, generation):
        """get_state: ライセンスが1つも無い場合のテストです。"""
        vendor, _ = generation
        mock_irmc.get.return_value = licenses_response(vendor, [])

        result = controller.get_state()

        assert result.extra_fields['licenses'] == []

    def test_get_state_http_error(self, controller, mock_irmc, generation):
        """get_state: HTTPエラーのテストです。"""
        vendor, _ = generation
        mock_irmc.get.return_value = Response(
            body='',
            headers={},
            status=500,
            request=Request('GET', licenses_path(vendor)),
        )

        with pytest.raises(HttpError) as exc_info:
            controller.get_state()

        assert exc_info.value.status == 500
        assert f'Failed to GET {licenses_path(vendor)}' in exc_info.value.message

    def test_get_state_missing_field(self, controller, mock_irmc, generation):
        """get_state: Keysフィールドが存在しない場合のテストです。"""
        vendor, _ = generation
        mock_irmc.get.return_value = Response(
            body={},
            headers={},
            status=200,
            request=Request('GET', licenses_path(vendor)),
        )

        with pytest.raises(ModuleError) as exc_info:
            controller.get_state()

        assert "'Keys' field not found" in exc_info.value.message

    def test_get_state_vendor_unknown(self, controller, mock_irmc):
        """get_state: ベンダーを判別できない場合のテストです。"""
        mock_irmc.vendor = None

        with pytest.raises(ModuleError) as exc_info:
            controller.get_state()

        assert 'vendor' in exc_info.value.message
        mock_irmc.get.assert_not_called()

    @pytest.mark.parametrize('status', [200, 202, 204])
    def test_set_state_success(self, controller, mock_irmc, generation, status):
        """set_state: 正常系テストです。"""
        _, oem_prefix = generation
        mock_irmc.post.return_value = Response(
            body=None,
            headers={},
            status=status,
            request=Request('POST', add_license_path(oem_prefix)),
        )

        result = controller.set_state({'license_key': 'ABCD-EFGH'})

        assert result.changed is True
        mock_irmc.post.assert_called_once_with(add_license_path(oem_prefix), {'LicenseKey': 'ABCD-EFGH'})

    def test_set_state_invalid_license_key(self, controller, mock_irmc, generation):
        """set_state: 不正なライセンスキーを指定した場合のテストです。"""
        _, oem_prefix = generation
        mock_irmc.post.return_value = invalid_license_response(oem_prefix)

        with pytest.raises(HttpError) as exc_info:
            controller.set_state({'license_key': 'INVALID-KEY'})

        assert exc_info.value.status == 400
        assert 'Invalid license key value provided.' in exc_info.value.message
        # ライセンスキーがメッセージに含まれないこと
        assert 'INVALID-KEY' not in exc_info.value.message

    @pytest.mark.parametrize('license_key', [None, ''])
    def test_set_state_missing_parameter(self, controller, mock_irmc, license_key):
        """set_state: license_keyパラメータがない場合のテストです。"""
        with pytest.raises(ValidationError) as exc_info:
            controller.set_state({'license_key': license_key})

        assert 'license_key' in exc_info.value.message
        assert 'required' in exc_info.value.message
        mock_irmc.post.assert_not_called()

    def test_set_state_vendor_unknown(self, controller, mock_irmc):
        """set_state: ベンダーを判別できない場合のテストです。"""
        mock_irmc.oem_prefix = None

        with pytest.raises(ModuleError) as exc_info:
            controller.set_state({'license_key': 'ABCD-EFGH'})

        assert 'vendor' in exc_info.value.message
        mock_irmc.post.assert_not_called()


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
            'license_key': None,
        }
        module._verbosity = 0
        return module

    @pytest.fixture
    def mock_logger(self):
        """to_logs_dict()が空辞書を返すモックLoggerを返すfixtureです。"""
        logger = Mock()
        logger.to_logs_dict.return_value = {}
        return logger

    @pytest.fixture
    def mock_irmc(self):
        """vendorがFsasのモックiRMCクライアントを返すfixtureです。"""
        irmc = Mock()
        irmc.vendor = 'Fsas'
        irmc.oem_prefix = 'Fsas'
        return irmc

    @patch('ansible_collections.fsas.primergy.plugins.modules.irmc_license.iRMC')
    @patch('ansible_collections.fsas.primergy.plugins.modules.irmc_license.AnsibleLogger')
    def test_get_command_success(self, mock_logger_class, mock_irmc_class, mock_module, mock_logger, mock_irmc):
        """get command: 正常系の統合テストです。"""
        from ansible_collections.fsas.primergy.plugins.modules.irmc_license import irmc_license

        mock_logger_class.return_value = mock_logger
        mock_irmc.get.return_value = licenses_response('Fsas', [
            {'Name': 'KVM', 'Type': 'Temporary', 'RemainingTimeH': 22562},
        ])
        mock_irmc_class.return_value = mock_irmc

        irmc_license(mock_module)

        mock_module.exit_json.assert_called_once()
        call_kwargs = mock_module.exit_json.call_args[1]
        assert call_kwargs['changed'] is False
        assert call_kwargs['licenses'] == [{'name': 'KVM', 'type': 'Temporary', 'remaining_time_h': 22562}]
        assert 'license_key' not in call_kwargs
        mock_module.fail_json.assert_not_called()

    @patch('ansible_collections.fsas.primergy.plugins.modules.irmc_license.iRMC')
    @patch('ansible_collections.fsas.primergy.plugins.modules.irmc_license.AnsibleLogger')
    def test_set_command_success(self, mock_logger_class, mock_irmc_class, mock_module, mock_logger, mock_irmc):
        """set command: 正常系の統合テストです。"""
        from ansible_collections.fsas.primergy.plugins.modules.irmc_license import irmc_license

        mock_module.params['command'] = 'set'
        mock_module.params['license_key'] = 'ABCD-EFGH'
        mock_logger_class.return_value = mock_logger
        mock_irmc.post.return_value = Response(
            body=None,
            headers={},
            status=204,
            request=Request('POST', add_license_path('Fsas')),
        )
        mock_irmc_class.return_value = mock_irmc

        irmc_license(mock_module)

        mock_module.exit_json.assert_called_once()
        call_kwargs = mock_module.exit_json.call_args[1]
        assert call_kwargs['changed'] is True
        mock_module.fail_json.assert_not_called()

    @patch('ansible_collections.fsas.primergy.plugins.modules.irmc_license.iRMC')
    @patch('ansible_collections.fsas.primergy.plugins.modules.irmc_license.AnsibleLogger')
    def test_http_error_handling(self, mock_logger_class, mock_irmc_class, mock_module, mock_logger, mock_irmc):
        """HTTPエラーハンドリングのテストです。"""
        from ansible_collections.fsas.primergy.plugins.modules.irmc_license import irmc_license

        mock_module.params['command'] = 'set'
        mock_module.params['license_key'] = 'INVALID-KEY'
        mock_logger_class.return_value = mock_logger
        mock_irmc.post.return_value = invalid_license_response('Fsas')
        mock_irmc_class.return_value = mock_irmc

        irmc_license(mock_module)

        mock_module.fail_json.assert_called_once()
        call_kwargs = mock_module.fail_json.call_args[1]
        assert call_kwargs['status'] == 400
        assert 'Invalid license key value provided.' in call_kwargs['msg']
        mock_module.exit_json.assert_not_called()

    @patch('ansible_collections.fsas.primergy.plugins.modules.irmc_license.iRMC')
    @patch('ansible_collections.fsas.primergy.plugins.modules.irmc_license.AnsibleLogger')
    def test_unexpected_error_handling(self, mock_logger_class, mock_irmc_class, mock_module, mock_logger, mock_irmc):
        """予期しない例外（接続エラー等）のハンドリングのテストです。"""
        from ansible_collections.fsas.primergy.plugins.modules.irmc_license import irmc_license

        mock_logger_class.return_value = mock_logger
        mock_irmc.get.side_effect = ConnectionError('connection refused')
        mock_irmc_class.return_value = mock_irmc

        irmc_license(mock_module)

        mock_module.fail_json.assert_called_once()
        call_kwargs = mock_module.fail_json.call_args[1]
        assert 'Unexpected error: connection refused' in call_kwargs['msg']
        assert 'exception' in call_kwargs

    @patch('ansible_collections.fsas.primergy.plugins.modules.irmc_license.iRMC')
    @patch('ansible_collections.fsas.primergy.plugins.modules.irmc_license.AnsibleLogger')
    def test_check_mode(self, mock_logger_class, mock_irmc_class, mock_module):
        """check_mode時はiRMCにアクセスせずに終了することのテストです。"""
        from ansible_collections.fsas.primergy.plugins.modules.irmc_license import irmc_license

        mock_module.check_mode = True
        # 実際のexit_json()と同様に処理を終了させる
        mock_module.exit_json.side_effect = SystemExit

        with pytest.raises(SystemExit):
            irmc_license(mock_module)

        mock_module.exit_json.assert_called_once_with(changed=False, msg='module was not run')
        mock_irmc_class.assert_not_called()
