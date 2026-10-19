#!/usr/bin/python

# Copyright 2018-2026 Fsas Technologies Inc.
# GNU General Public License v3.0+ (see LICENSE.md or https://www.gnu.org/licenses/gpl-3.0.txt)

DOCUMENTATION = r'''
---
module: irmc_license

short_description: manage iRMC license keys

description:
    - Ansible module to get or add iRMC license keys via iRMC Redfish interface.
    - Module Version V2.0.0.

requirements:
    - The module needs to run locally.
    - Python >= 3.14
    - Python modules 'requests', 'urllib3'

version_added: "2.4"

author:
    - Yutaka Kamioka (<yutaka.kamioka@fujitsu.com>)

options:
    irmc_url:
        type:        str
        description: IP address of the iRMC to be requested for data.
        required:    true
    irmc_username:
        type:        str
        description: iRMC user for basic authentication.
        required:    true
    irmc_password:
        type:        str
        description: Password for iRMC user for basic authentication.
        required:    true
    validate_certs:
        type:        bool
        description: Evaluate SSL certificate (set to false for self-signed certificate).
        required:    false
        default:     true
    command:
        type:        str
        description: License key management to be executed.
        required:    false
        default:     get
        choices:     ['get', 'set']
    license_key:
        type:        str
        description: iRMC license key to be added. Required for command 'set'.
        required:    false

notes:
    - The license key string itself cannot be read from the iRMC.
      Command 'get' returns the list of licensed features instead.
    - Command 'set' always reports 'changed', because the registered license keys cannot be compared.
'''

EXAMPLES = r'''
# Get iRMC licenses
- name: Get and show iRMC licenses
  tags:
    - get
  block:
    - name: Get iRMC licenses
      fsas.primergy.irmc_license:
        irmc_url: "{{ inventory_hostname }}"
        irmc_username: "{{ irmc_user }}"
        irmc_password: "{{ irmc_password }}"
        validate_certs: "{{ validate_certificate }}"
        command: "get"
      register: license
      delegate_to: localhost

    - name: Show iRMC licenses
      ansible.builtin.debug:
        var: license.licenses

# Set iRMC license key
- name: Set iRMC license key
  fsas.primergy.irmc_license:
    irmc_url: "{{ inventory_hostname }}"
    irmc_username: "{{ irmc_user }}"
    irmc_password: "{{ irmc_password }}"
    validate_certs: "{{ validate_certificate }}"
    command: "set"
    license_key: "{{ license_key }}"
  delegate_to: localhost
  tags:
    - set
'''

RETURN = r'''
licenses:
    description: List of licensed features registered in the iRMC.
    returned: when command is "get"
    type: list
    elements: dict
    contains:
        name:
            description: Licensed feature name
            returned: always
            type: str
            sample: KVM
        type:
            description: License type
            returned: always
            type: str
            sample: Permanent
        remaining_time_h:
            description: Remaining validity in hours (temporary licenses only)
            returned: when provided by the iRMC
            type: int
            sample: 22562
'''


import traceback
from typing import Any, Mapping

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.fsas.primergy.plugins.module_utils.controller_result import ControllerResult
from ansible_collections.fsas.primergy.plugins.module_utils.errors import HttpError, ModuleError, ValidationError
from ansible_collections.fsas.primergy.plugins.module_utils.helpers import dig
from ansible_collections.fsas.primergy.plugins.module_utils.irmc_client import iRMC
from ansible_collections.fsas.primergy.plugins.module_utils.logger import AnsibleLogger, Logger


class LicenseController:
    """iRMCのライセンスを管理するControllerクラスです。
    """

    def __init__(self, irmc: iRMC, logger: Logger):
        """LicenseControllerを初期化します。

        引数:
            irmc - iRMCクライアントインスタンス
            logger - ログ出力用のLoggerインスタンス
        """
        self.irmc = irmc
        self.logger = logger

    def _licenses_path(self) -> str:
        """ライセンス一覧リソースのパスを返します。

        戻り値:
            ライセンス一覧リソースのパス

        例外:
            ModuleError - iRMCのベンダーを判別できない場合
        """
        # 以下のリンクを辿って得られるパスを組み立てる
        #   GET /redfish/v1/Managers/iRMC
        #     -> .Oem.{vendor}.iRMCConfiguration."@odata.id"
        #        (/redfish/v1/Managers/iRMC/Oem/{vendor}/iRMCConfiguration)
        #   GET /redfish/v1/Managers/iRMC/Oem/{vendor}/iRMCConfiguration
        #     -> .Licenses."@odata.id"
        #        (/redfish/v1/Managers/iRMC/Oem/{vendor}/iRMCConfiguration/Licenses)
        # vendorはM7以前が"ts_fujitsu"、M8以降が"Fsas"
        vendor = self.irmc.vendor
        if vendor is None:
            raise ModuleError("Failed to detect iRMC vendor")
        return f'/redfish/v1/Managers/iRMC/Oem/{vendor}/iRMCConfiguration/Licenses'

    def _add_license_path(self) -> str:
        """ライセンス追加アクションのパスを返します。

        戻り値:
            ライセンス追加アクションのパス

        例外:
            ModuleError - iRMCのベンダーを判別できない場合
        """
        # 以下のリンクを辿って得られるパスを組み立てる
        #   GET /redfish/v1/Managers/iRMC
        #     -> .Actions.Oem."#{oem_prefix}Manager.AddLicense".target
        #        (/redfish/v1/Managers/iRMC/Actions/Oem/{oem_prefix}Manager.AddLicense)
        # oem_prefixはM7以前が"FTS"、M8以降が"Fsas"
        oem_prefix = self.irmc.oem_prefix
        if oem_prefix is None:
            raise ModuleError("Failed to detect iRMC vendor")
        return f'/redfish/v1/Managers/iRMC/Actions/Oem/{oem_prefix}Manager.AddLicense'

    def get_state(self) -> ControllerResult:
        """登録済みのライセンス一覧を取得します。

        戻り値:
            ControllerResult（changed=False, licenses属性を含む）

        例外:
            HttpError - HTTPリクエストが失敗した場合
            ModuleError - iRMCのベンダーを判別できない場合、またはレスポンスにKeysフィールドが存在しない場合
        """
        self.logger.debug("Getting licenses from iRMC")
        response = self.irmc.get(self._licenses_path())
        if response.status != 200:
            msg = f"Failed to {response.request.method} {response.request.path}"
            self.logger.warn(msg)
            raise HttpError(msg, status=response.status)

        fields = ['Keys']
        keys = dig(response.body, *fields)
        if keys is None:
            msg = f"{'.'.join(fields)!r} field not found in response"
            self.logger.warn(msg)
            raise ModuleError(msg)

        licenses = []
        for key in keys:
            license_info = {
                'name': key.get('Name'),
                'type': key.get('Type'),
            }
            # RemainingTimeHは一時ライセンスの場合のみ存在すると思われる
            if 'RemainingTimeH' in key:
                license_info['remaining_time_h'] = key['RemainingTimeH']
            licenses.append(license_info)

        return ControllerResult.unchanged(
            licenses=licenses,
        )

    def set_state(self, params: Mapping[str, Any]) -> ControllerResult:
        """ライセンスキーを追加します。

        登録済みのライセンスキー文字列はiRMCから取得できず比較できないため、
        成功時は常にchanged=Trueを返します。

        引数:
            params - パラメータ辞書（必須: 'license_key'）

        戻り値:
            ControllerResult（changed=True）

        例外:
            ValidationError - license_keyパラメータが不足している場合
            HttpError - HTTPリクエストが失敗した場合（不正なライセンスキーを含む）
            ModuleError - iRMCのベンダーを判別できない場合
        """
        license_key = params.get('license_key')
        if not license_key:
            raise ValidationError("'license_key' parameter is required for set command")

        self.logger.debug("Adding license key to iRMC")
        body = {'LicenseKey': license_key}
        response = self.irmc.post(self._add_license_path(), body)
        if response.status not in (200, 202, 204):
            # ライセンスキーを含むbodyはメッセージに含めない
            error_message = dig(response.body, 'error', 'message') if isinstance(response.body, dict) else None
            msg = f"Failed to {response.request.method} {response.request.path}: {error_message or response.body}"
            self.logger.warn(msg)
            raise HttpError(msg, status=response.status)

        self.logger.log("License key added")
        return ControllerResult.changed_success()


def irmc_license(module: AnsibleModule) -> None:
    """irmc_licenseモジュールのメイン処理です。

    引数:
        module - AnsibleModuleインスタンス
    """
    if module.check_mode:
        module.exit_json(changed=False, msg='module was not run')

    # ロガー初期化
    logger = AnsibleLogger(module)

    # iRMCクライアント初期化
    irmc = iRMC(
        ipaddress=module.params['irmc_url'],
        username=module.params['irmc_username'],
        password=module.params['irmc_password'],
        validate_certs=module.params['validate_certs'],
        logger=logger,
        raise_on_error=True,
    )

    # Controller初期化
    controller = LicenseController(irmc, logger)

    # ビジネスロジック実行
    try:
        if module.params['command'] == 'get':
            controller_result = controller.get_state()
        elif module.params['command'] == 'set':
            controller_result = controller.set_state(module.params)
        else:
            raise ValidationError(f"Unknown command: {module.params['command']}")

        result = controller_result.to_exit_dict() | logger.to_logs_dict()
        module.exit_json(**result)

    except ModuleError as e:
        result = e.to_fail_dict() | logger.to_logs_dict()
        module.fail_json(**result)

    except Exception as e:
        # 予期しないエラー（接続エラーを含む）
        result = {'msg': f"Unexpected error: {e}", 'exception': traceback.format_exc()} | logger.to_logs_dict()
        module.fail_json(**result)


def main() -> None:
    module_args = dict(
        irmc_url=dict(required=True, type='str'),
        irmc_username=dict(required=True, type='str'),
        irmc_password=dict(required=True, type='str', no_log=True),
        validate_certs=dict(required=False, type='bool', default=True),
        command=dict(required=False, type='str', default='get', choices=['get', 'set']),
        license_key=dict(required=False, type='str', no_log=True),
    )
    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=False,
    )

    irmc_license(module)


if __name__ == '__main__':
    main()
