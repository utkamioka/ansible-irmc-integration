#!/usr/bin/python

# Copyright 2018-2026 Fsas Technologies Inc.
# GNU General Public License v3.0+ (see LICENSE.md or https://www.gnu.org/licenses/gpl-3.0.txt)

DOCUMENTATION = r'''
---
module: irmc_ntp

short_description: manage iRMC time options

description:
    - Ansible module to manage iRMC time options via iRMC Redfish interface.
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
        description: NTP management to be executed.
        required:    false
        default:     get
        choices:     ['get', 'set']
    time_mode:
        type:        str
        description:
            - Defines how iRMC synchronizes its real-time clock (RTC).
            - Both the legacy values and the Redfish values are accepted.
              'System RTC' is equivalent to 'iRMC'.
        required:    false
        choices:     ['System RTC', 'NTP', 'iRMC']
    rtc_mode:
        type:        str
        description:
            - Defines how iRMC interprets the system's hardware RTC time.
            - Both the legacy values and the Redfish values are accepted.
              'local time' is equivalent to 'LocalTime', and 'UTC/GMT' is equivalent to 'UTC'.
        required:    false
        choices:     ['local time', 'UTC/GMT', 'LocalTime', 'UTC']
    time_zone_location:
        type:        str
        description: iRMC time zone (e.g. 'Europe/Berlin'; based on Linux 'tzdata').
        required:    false
    ntp_server_primary:
        type:        str
        description: IP address (IPv4 or IPv6) or DNS name of primary NTP server.
        required:    false
    ntp_server_secondary:
        type:        str
        description: IP address (IPv4 or IPv6) or DNS name of secondary NTP server.
        required:    false
    legacy_output:
        type:        bool
        description:
            - Return 'time_mode' and 'rtc_mode' in 'time_settings' with the legacy values
              ('System RTC', 'local time', 'UTC/GMT') instead of the Redfish values
              ('iRMC', 'LocalTime', 'UTC').
            - Use this option to keep playbooks which expect the output of the previous module version working.
        required:    false
        default:     false

notes:
    - Command 'set' changes only the options which differ from the current settings.
      If all specified options already have the requested values, or no option to change is specified,
      nothing is changed.
    - The values of 'time_mode' and 'rtc_mode' in 'time_settings' are the Redfish values by default.
      Set 'legacy_output' to true to get the legacy values.
'''

EXAMPLES = r'''
# Get iRMC time settings
- name: Get and show iRMC time settings
  tags:
    - get
  block:
    - name: Get iRMC time settings
      fsas.primergy.irmc_ntp:
        irmc_url: "{{ inventory_hostname }}"
        irmc_username: "{{ irmc_user }}"
        irmc_password: "{{ irmc_password }}"
        validate_certs: "{{ validate_certificate }}"
        command: "get"
      register: time
      delegate_to: localhost
    - name: Show iRMC time settings
      ansible.builtin.debug:
        var: time.time_settings

# Set iRMC time option(s)
- name: Set iRMC time option(s)
  fsas.primergy.irmc_ntp:
    irmc_url: "{{ inventory_hostname }}"
    irmc_username: "{{ irmc_user }}"
    irmc_password: "{{ irmc_password }}"
    validate_certs: "{{ validate_certificate }}"
    command: "set"
    time_mode: "System RTC"
    time_zone_location: "Asia/Tokyo"
    rtc_mode: "local time"
  delegate_to: localhost
  tags:
    - set
'''

RETURN = r'''
time_settings:
    description: Current iRMC time settings (after the change for command "set").
    returned: always
    type: dict
    contains:
        ntp_server_primary:
            description: primary NTP server
            returned: always
            type: str
            sample: pool.ntp.org
        ntp_server_secondary:
            description: secondary NTP server
            returned: always
            type: str
            sample: pool.ntp.org
        rtc_mode:
            description:
                - Defines how iRMC interprets the system's hardware RTC time
                - Redfish value ('LocalTime' or 'UTC'), or legacy value ('local time' or 'UTC/GMT')
                  if 'legacy_output' is true
            returned: always
            type: str
            sample: LocalTime
        time_mode:
            description:
                - Defines how iRMC synchronizes its real-time clock (RTC)
                - Redfish value ('iRMC' or 'NTP'), or legacy value ('System RTC' or 'NTP')
                  if 'legacy_output' is true
            returned: always
            type: str
            sample: iRMC
        time_zone_location:
            description: iRMC time zone
            returned: always
            type: str
            sample: Europe/Berlin
'''


import traceback
from typing import Any, Mapping

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.fsas.primergy.plugins.module_utils.controller_result import ControllerResult
from ansible_collections.fsas.primergy.plugins.module_utils.errors import HttpError, ModuleError, ValidationError
from ansible_collections.fsas.primergy.plugins.module_utils.helpers import dig
from ansible_collections.fsas.primergy.plugins.module_utils.irmc_client import iRMC
from ansible_collections.fsas.primergy.plugins.module_utils.logger import AnsibleLogger, Logger

# 旧仕様(SCCI版)の表記からRedfishの値への変換表
# 旧仕様との互換性を保つためのもの。Redfishの値("iRMC", "NTP", "LocalTime", "UTC")はそのまま受け付ける
# "NTP"は旧仕様とRedfishで同じ表記なので変換表には含めない
# 旧仕様の"MMB NTP"はPRIMERGYに存在しない機能のため廃止した
LEGACY_TIME_MODE = {
    'System RTC': 'iRMC',
}
LEGACY_RTC_MODE = {
    'local time': 'LocalTime',
    'UTC/GMT': 'UTC',
}

# Redfishの値から旧仕様の表記への変換表
# 旧仕様との互換性を保つためのもの。legacy_output=trueのときだけ戻り値の変換に使う
TIME_MODE_TO_LEGACY = {v: k for k, v in LEGACY_TIME_MODE.items()} | {'NTP': 'NTP'}
RTC_MODE_TO_LEGACY = {v: k for k, v in LEGACY_RTC_MODE.items()}

# モジュールのパラメータとTimeリソースのプロパティの対応
TIME_PROPERTIES = {
    'time_mode': 'SyncSource',
    'rtc_mode': 'RtcMode',
    'time_zone_location': 'TimeZone',
}

# モジュールのパラメータとNtpServersのメンバーIDの対応
NTP_SERVER_INDEXES = {
    'ntp_server_primary': 0,
    'ntp_server_secondary': 1,
}

SET_PARAMETERS = list(TIME_PROPERTIES) + list(NTP_SERVER_INDEXES)


class NtpController:
    """iRMCの時刻設定を管理するControllerクラスです。
    """

    def __init__(self, irmc: iRMC, logger: Logger):
        """NtpControllerを初期化します。

        引数:
            irmc - iRMCクライアントインスタンス
            logger - ログ出力用のLoggerインスタンス
        """
        self.irmc = irmc
        self.logger = logger

    def _time_path(self) -> str:
        """時刻設定リソースのパスを返します。

        戻り値:
            時刻設定リソースのパス

        例外:
            ModuleError - iRMCのベンダーを判別できない場合
        """
        # 以下のリンクを辿って得られるパスを組み立てる
        #   GET /redfish/v1/Managers/iRMC
        #     -> .Oem.{vendor}.iRMCConfiguration."@odata.id"
        #        (/redfish/v1/Managers/iRMC/Oem/{vendor}/iRMCConfiguration)
        #   GET /redfish/v1/Managers/iRMC/Oem/{vendor}/iRMCConfiguration
        #     -> .Time."@odata.id"
        #        (/redfish/v1/Managers/iRMC/Oem/{vendor}/iRMCConfiguration/Time)
        # vendorはM7以前が"ts_fujitsu"、M8以降が"Fsas"
        vendor = self.irmc.vendor
        if vendor is None:
            raise ModuleError("Failed to detect iRMC vendor")
        return f'/redfish/v1/Managers/iRMC/Oem/{vendor}/iRMCConfiguration/Time'

    def _ntp_server_path(self, index: int) -> str:
        """NTPサーバー設定リソースのパスを返します。

        引数:
            index - NtpServersのメンバーID（0: プライマリ、1: セカンダリ）

        戻り値:
            NTPサーバー設定リソースのパス

        例外:
            ModuleError - iRMCのベンダーを判別できない場合
        """
        # 以下のリンクを辿って得られるパスを組み立てる
        #   GET /redfish/v1/Managers/iRMC/Oem/{vendor}/iRMCConfiguration/Time
        #     -> .Ntp.NtpServers."@odata.id"
        #        (/redfish/v1/Managers/iRMC/Oem/{vendor}/iRMCConfiguration/Time/NtpServers)
        #   GET /redfish/v1/Managers/iRMC/Oem/{vendor}/iRMCConfiguration/Time/NtpServers
        #     -> .Members[]."@odata.id"
        #        (.../Time/NtpServers/0 と .../Time/NtpServers/1 の2件)
        return f'{self._time_path()}/NtpServers/{index}'

    def _fetch(self, path: str, use_cache: bool = True) -> dict:
        """リソースを取得します。

        引数:
            path - 取得するリソースのパス
            use_cache - iRMCクライアントのレスポンスキャッシュを使うか

        戻り値:
            レスポンスボディ

        例外:
            HttpError - HTTPリクエストが失敗した場合
        """
        response = self.irmc.get(path, use_cache=use_cache)
        if response.status != 200:
            msg = f"Failed to {response.request.method} {response.request.path}"
            self.logger.warn(msg)
            raise HttpError(msg, status=response.status)
        return response.body

    def _to_legacy(self, value: Any, table: Mapping[str, str], name: str) -> Any:
        """Redfishの値を旧仕様の表記に変換します。

        引数:
            value - Redfishの値
            table - Redfishの値から旧仕様の表記への変換表
            name - 警告メッセージに使うプロパティ名

        戻り値:
            旧仕様の表記（変換表にない値はそのまま）
        """
        if value in table:
            return table[value]
        if value is not None:
            self.logger.warn(f"Unknown {name} value {value!r} returned by iRMC")
        return value

    def _collect_settings(self, use_cache: bool = True, legacy_output: bool = False) -> dict:
        """現在の時刻設定を取得し、戻り値の形式にまとめます。

        引数:
            use_cache - iRMCクライアントのレスポンスキャッシュを使うか
            legacy_output - time_modeとrtc_modeを旧仕様の表記に変換するか（既定はRedfishの値のまま）

        戻り値:
            時刻設定（旧仕様と同じ5項目のキー）

        例外:
            HttpError - HTTPリクエストが失敗した場合
            ModuleError - iRMCのベンダーを判別できない場合
        """
        time = self._fetch(self._time_path(), use_cache=use_cache)
        primary = self._fetch(self._ntp_server_path(0), use_cache=use_cache)
        secondary = self._fetch(self._ntp_server_path(1), use_cache=use_cache)
        time_mode = dig(time, 'SyncSource')
        rtc_mode = dig(time, 'RtcMode')
        if legacy_output:
            time_mode = self._to_legacy(time_mode, TIME_MODE_TO_LEGACY, 'SyncSource')
            rtc_mode = self._to_legacy(rtc_mode, RTC_MODE_TO_LEGACY, 'RtcMode')
        return {
            'time_mode': time_mode,
            'rtc_mode': rtc_mode,
            'time_zone_location': dig(time, 'TimeZone'),
            'ntp_server_primary': dig(primary, 'NtpServerName'),
            'ntp_server_secondary': dig(secondary, 'NtpServerName'),
        }

    def _patch(self, path: str, body: dict, changed_paths: list[str]) -> None:
        """ETagを取り直してリソースをPATCHします。

        引数:
            path - 変更するリソースのパス
            body - PATCHのボディ（変更する項目のみ）
            changed_paths - これまでに変更済みのリソースのパス（失敗時のメッセージに使用）

        例外:
            HttpError - HTTPリクエストが失敗した場合
        """
        # ETagは送信直前に取得する
        # use_cache=Falseが必須。iRMCクライアントのキャッシュはPATCHで無効化されないため
        current = self._fetch(path, use_cache=False)
        etag = dig(current, '@odata.etag')
        headers = {'If-Match': str(etag)} if etag else None

        self.logger.debug(f"Patching {path} with {body}")
        response = self.irmc.patch(path, body, headers=headers)
        if response.status != 200:
            error_message = dig(response.body, 'error', 'message') if isinstance(response.body, dict) else None
            msg = (
                f"Failed to {response.request.method} {response.request.path} with body {body}: "
                f"{error_message or response.body}"
            )
            # TimeとNtpServersは別リソースのため、途中で失敗すると一部だけ変更された状態になる
            if changed_paths:
                msg += f" (already changed: {', '.join(changed_paths)})"
            self.logger.warn(msg)
            raise HttpError(msg, status=response.status)

    def get_state(self, params: Mapping[str, Any]) -> ControllerResult:
        """時刻設定を取得します。

        引数:
            params - パラメータ辞書（任意: 'legacy_output'）

        戻り値:
            ControllerResult（changed=False, time_settings属性を含む）

        例外:
            HttpError - HTTPリクエストが失敗した場合
            ModuleError - iRMCのベンダーを判別できない場合
        """
        self.logger.debug("Getting time settings from iRMC")
        return ControllerResult.unchanged(
            time_settings=self._collect_settings(legacy_output=bool(params.get('legacy_output'))),
        )

    def set_state(self, params: Mapping[str, Any]) -> ControllerResult:
        """時刻設定を変更します。

        指定されたパラメータのうち、現在値と異なるものだけを変更します。
        変更はTime、プライマリNTPサーバー、セカンダリNTPサーバーの順に行います。
        変更対象のパラメータが1つも指定されていない場合は、何も変更せずにchanged=Falseを返します。

        引数:
            params - パラメータ辞書（任意: time_mode, rtc_mode, time_zone_location,
                     ntp_server_primary, ntp_server_secondary, legacy_output）

        戻り値:
            ControllerResult（changed=TrueまたはFalse, time_settings属性を含む）

        例外:
            HttpError - HTTPリクエストが失敗した場合
            ModuleError - iRMCのベンダーを判別できない場合
        """
        legacy_output = bool(params.get('legacy_output'))

        # 変更対象のパラメータが1つも無い場合は、何もせず変更なしとして終える
        # (roleの変数はすべて任意なので、変数を指定せずにroleを呼んでもエラーにしないため)
        if all(params.get(name) is None for name in SET_PARAMETERS):
            return ControllerResult.unchanged(
                msg=f"No option to change was specified ({', '.join(SET_PARAMETERS)})",
                time_settings=self._collect_settings(legacy_output=legacy_output),
            )

        # 旧仕様の表記をRedfishの値に変換する
        requested = {
            'time_mode': LEGACY_TIME_MODE.get(params.get('time_mode'), params.get('time_mode')),
            'rtc_mode': LEGACY_RTC_MODE.get(params.get('rtc_mode'), params.get('rtc_mode')),
            'time_zone_location': params.get('time_zone_location'),
            'ntp_server_primary': params.get('ntp_server_primary'),
            'ntp_server_secondary': params.get('ntp_server_secondary'),
        }

        # 変更が必要なリソースとボディを順番に並べる(Time -> プライマリ -> セカンダリ)
        patches = []

        if any(requested[name] is not None for name in TIME_PROPERTIES):
            time_path = self._time_path()
            time = self._fetch(time_path)
            time_body = {
                prop: requested[name]
                for name, prop in TIME_PROPERTIES.items()
                if requested[name] is not None and requested[name] != dig(time, prop)
            }
            if time_body:
                patches.append((time_path, time_body))

        for name, index in NTP_SERVER_INDEXES.items():
            if requested[name] is None:
                continue
            path = self._ntp_server_path(index)
            server = self._fetch(path)
            if requested[name] != dig(server, 'NtpServerName'):
                patches.append((path, {'NtpServerName': requested[name]}))

        if not patches:
            return ControllerResult.unchanged(
                msg="Time settings are already in the requested state",
                time_settings=self._collect_settings(legacy_output=legacy_output),
            )

        changed_paths = []
        for path, body in patches:
            self._patch(path, body, changed_paths)
            changed_paths.append(path)

        self.logger.log(f"Time settings changed: {', '.join(changed_paths)}")

        # 変更後の状態は再取得する
        # use_cache=Falseが必須。iRMCクライアントのキャッシュはPATCHで無効化されないため
        return ControllerResult.changed_success(
            time_settings=self._collect_settings(use_cache=False, legacy_output=legacy_output),
        )


def irmc_ntp(module: AnsibleModule) -> None:
    """irmc_ntpモジュールのメイン処理です。

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
    controller = NtpController(irmc, logger)

    # ビジネスロジック実行
    try:
        if module.params['command'] == 'get':
            controller_result = controller.get_state(module.params)
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
        time_mode=dict(required=False, type='str', choices=['System RTC', 'NTP', 'iRMC']),
        rtc_mode=dict(required=False, type='str', choices=['local time', 'UTC/GMT', 'LocalTime', 'UTC']),
        time_zone_location=dict(required=False, type='str'),
        ntp_server_primary=dict(required=False, type='str'),
        ntp_server_secondary=dict(required=False, type='str'),
        legacy_output=dict(required=False, type='bool', default=False),
    )
    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=False,
    )

    irmc_ntp(module)


if __name__ == '__main__':
    main()
