#!/usr/bin/python

# Copyright 2018-2025 Fsas Technologies Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


DOCUMENTATION = r'''
---
module: irmc_facts2

short_description: get or set PRIMERGY server and iRMC facts (refactored version)

description:
    - Ansible module to get or set basic iRMC and PRIMERGY server data via iRMC RedFish interface.
    - This is a refactored version of irmc_facts with improved code structure and M8 support.
    - Module Version V2.0.0.

requirements:
    - The module needs to run locally.
    - iRMC S6 or later.
    - Python >= 3.10
    - Python modules 'requests', 'urllib3'

version_added: "2.4"

author:
    - Yutaka Kamioka (<yutaka.kamioka@fujitsu.com>)

options:
    irmc_url:
        description: IP address of the iRMC to be requested for data.
        required:    true
    irmc_username:
        description: iRMC user for basic authentication.
        required:    true
    irmc_password:
        description: Password for iRMC user for basic authentication.
        required:    true
    validate_certs:
        description: Evaluate SSL certificate (set to false for self-signed certificate).
        type:        bool
        required:    false
        default:     true
    command:
        description: How to access server facts.
        required:    false
        default:     get
        choices:     ['get', 'set']
    asset_tag:
        description: Server asset tag.
        required:    false
    location:
        description: Server location.
        required:    false
    description:
        description: Server description.
        required:    false
    contact:
        description: System contact.
        required:    false
    helpdesk_message:
        description: Help desk message.
        required:    false
'''

EXAMPLES = r'''
# Get basic server and iRMC facts
- block:
  - name: Get basic server and iRMC facts
    fujitsu.primergy.irmc_facts2:
      irmc_url: "{{ inventory_hostname }}"
      irmc_username: "{{ irmc_user }}"
      irmc_password: "{{ irmc_password }}"
      validate_certs: "{{ validate_certificate }}"
      command: "get"
    register: result
    delegate_to: localhost
  - name: Show server and iRMC facts
    debug:
      var: result.facts
  tags:
    - get

# Set server asset tag
- name: Set server asset tag
  fujitsu.primergy.irmc_facts2:
    irmc_url: "{{ inventory_hostname }}"
    irmc_username: "{{ irmc_user }}"
    irmc_password: "{{ irmc_password }}"
    validate_certs: "{{ validate_certificate }}"
    command: "set"
    asset_tag: "Ansible test server"
  delegate_to: localhost
  tags:
    - set
'''

RETURN = r'''
details:
    description:
        If command is "get", the following values are returned.

        If command is "set", the default return value of Ansible (changed, failed, etc.) is returned.

    contains:
        hardware.ethernetinterfaces:
            description:
                dict with total number (count)
                and list of ethernet interfaces (devices)
                with relevant data (id, macaddress, name).
            returned: always
            type: dict
            sample:
                {
                    "count": 2,
                    "devices": [
                        { "id": "0", "macaddress": "01:02:03:04:05:06", "name": "eth0" },
                        { "id": "1", "macaddress": "01:02:03:04:05:06", "name": "eth1" }
                    ]
                }
        hardware.fans:
            description:
                dict with available fan slots (sockets)
                and total number (count)
                and list of existing fans (devices)
                with relevant data (id, manufacturer, name, size).
                note that fan devices are only returned if server is 'On'.
            returned: always
            type: dict
            sample:
                {
                    "count": 2,
                    "devices": [
                        { "id": "0", "manufacturer": "Micron Technology", "name": "DIMM-1A", "size": 8192 },
                        { "id": "12", "manufacturer": "SK Hynix", "name": "DIMM-1E", "size": 16384 }
                    ],
                    "sockets": 24
                }
        hardware.memory:
            description:
                dict with available memory slots (sockets)
                and total number (count)
                and list of existing memories (devices)
                with relevant data (id, manufacturer, name, size).
            returned: always
            type: dict
            sample:
                {
                    "count": 6,
                    "devices": [
                        { "id": "0", "location": "SystemBoard", "name": "FAN1 SYS" },
                        { "id": "1", "location": "SystemBoard", "name": "FAN2 SYS" },
                        { "id": "2", "location": "SystemBoard", "name": "FAN3 SYS" },
                        { "id": "3", "location": "SystemBoard", "name": "FAN4 SYS" },
                        { "id": "4", "location": "SystemBoard", "name": "FAN5 SYS" },
                        { "id": "5", "location": "PowerSupply", "name": "FAN PSU1" }
                    ],
                    "sockets": 7
                }
        hardware.powersupplies:
            description:
                dict with available power supply slots (sockets)
                and total number (count)
                and list of existing power supplies (devices)
                with relevant data (id, manufacturer, model, name).
            returned: always
            type: dict
            sample:
                {
                    "count": 1,
                    "devices": [
                        { "id": "0", "manufacturer": "CHICONY", "model": "S13-450P1A", "name": "PSU1" }
                    ],
                    "sockets": 2
                }
        hardware.processors:
            description:
                dict with available processor slots (sockets)
                and total number (count)
                and list of existing processors (devices)
                with relevant data (cores, id, name, threads).
            returned: always
            type: dict
            sample:
                {
                    "count": 2,
                    "devices": [
                        { "cores": 6, "id": "0", "name": "Genuine Intel(R) CPU @ 2.00GHz", "threads": 6 },
                        { "cores": 6, "id": "1", "name": "Genuine Intel(R) CPU @ 2.00GHz", "threads": 6 }
                    ],
                    "sockets": 2
                }
        hardware.storagecontrollers:
            description:
                dict with total number (count)
                and list of storage controllers (devices)
                with relevant data (drives, firmware, id, name, volume).
                note that storage controllers are only returned if server is 'On'.
            returned: always
            type: dict
            sample:
                {
                    "count": 1,
                    "devices": [
                        { "drives": 4, "firmware": "4.270.00-4869", "id": "1000", "name": "PRAID EP400i", "volumes": 1 }
                    ]
                }
        irmc:
            description:
                dict with relevant iRMC data
                (fw_builddate, fw_running, fw_version, hostname, macaddress, sdrr_version).
            returned: always
            type: dict
            sample:
                {
                    "fw_builddate": "2018-03-05T14:02:48",
                    "fw_running": "LowFWImage",
                    "fw_version": "9.08F",
                    "hostname": "iRMC01CA5C-iRMC",
                    "macaddress": "90:1B:0E:01:CA:5C",
                    "sdrr_version": "3.73"
                }
        mainboard:
            description:
                dict with relevant mainboard data
                (dnumber, manufacturer, part_number, serial_number, version).
            returned: always
            type: dict
            sample:
                {
                    "dnumber": "D3289",
                    "manufacturer": "FUJITSU",
                    "part_number": "S26361-D3289-D13",
                    "serial_number": "44617895",
                    "version": "WGS04 GS50"
                }
        system:
            description:
                dict with relevant system data
                (asset_tag, bios_version, description, health, helpdesk_message, host_name,
                idled_state, ip, location, manufacturer, memory_size, model, part_number,
                power_state, serial_number, uuid).
            returned: always
            type: dict
            sample:
                {
                    "asset_tag": "New AssetTag",
                    "bios_version": "V5.0.0.9 R1.36.0 for D3289-A1x",
                    "contact": "Admin (admin@server.room)",
                    "description": "server description",
                    "health": "OK",
                    "helpdesk_message": "New helpdesk message",
                    "host_name": "STK-SLES11SP4x64",
                    "idled_state": "Off",
                    "ip": 101.102.103.104,
                    "location": "Server Room",
                    "manufacturer": "FUJITSU",
                    "memory_size": "24 GB",
                    "model": "PRIMERGY RX2540 M1",
                    "part_number": "ABN:K1495-VXXX-XX",
                    "power_state": "On",
                    "serial_number": "YLVT000098",
                    "uuid": "11223344-5566-cafe-babe-deadbeef1234"
                }
'''


from typing import TYPE_CHECKING, Optional

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.fujitsu.primergy.plugins.module_utils.irmc_client import iRMC
from ansible_collections.fujitsu.primergy.plugins.module_utils.logger import AnsibleLogger
from ansible_collections.fujitsu.primergy.plugins.module_utils.errors import (
    IrmcModuleError,
    HttpError,
    ValidationError,
)
from ansible_collections.fujitsu.primergy.plugins.module_utils.helpers import dig

if TYPE_CHECKING:
    from ansible_collections.fujitsu.primergy.plugins.module_utils.logger import Logger


class FactsHandler:
    """iRMC facts取得・設定ハンドラー

    このクラスは、iRMCからのfacts取得とfacts設定を担当します。
    M8世代（Fsas）とM7以前（ts_fujitsu）の両方に対応しています。

    引数:
        irmc - iRMCクライアントインスタンス
        logger - ログ出力用のLoggerインスタンス（オプション）
    """

    def __init__(self, irmc: iRMC, logger: Optional['Logger'] = None):
        """FactsHandlerを初期化します。

        引数:
            irmc - iRMCクライアントインスタンス
            logger - ログ出力用のLoggerインスタンス（オプション）

        例外:
            ValidationError - vendor属性が取得できない場合
        """
        self.irmc = irmc
        self.logger = logger

        # M8対応: vendorを自動判定（ts_fujitsu or Fsas）
        # vendor属性が取得できない場合はエラー
        if irmc.vendor is None:
            raise ValidationError(
                'Failed to detect iRMC vendor. Vendor attribute not found in /redfish/v1'
            )
        self._debug(f'Detected iRMC vendor: {irmc.vendor}')

    def _warn(self, message: str):
        """警告メッセージを出力します。

        loggerが設定されている場合にのみログを出力します。

        引数:
            message - ログメッセージ
        """
        if self.logger:
            self.logger.warn(message)

    def _log(self, message: str):
        """ログメッセージを出力します。

        loggerが設定されている場合にのみログを出力します。

        引数:
            message - ログメッセージ
        """
        if self.logger:
            self.logger.log(message)

    def _debug(self, message: str):
        """デバッグメッセージを出力します。

        loggerが設定されている場合にのみログを出力します。

        引数:
            message - ログメッセージ
        """
        if self.logger:
            self.logger.debug(message)

    def get(self) -> dict:
        """facts取得（getコマンド）を実行します。

        戻り値:
            dict - Ansible module.exit_json()用の結果辞書
        """
        self._log('Starting facts retrieval')

        # システムデータ取得
        self._debug('Retrieving system data')
        system_data = self._get_system_data()

        self._debug('Retrieving OEM data')
        oem_data = self._get_oem_data()

        self._debug('Retrieving firmware data')
        fw_data = self._get_firmware_data()

        # 電源状態を取得
        power_state = dig(system_data, 'PowerState', default='Unknown')
        self._debug(f'Power state: {power_state}')

        # iRMCネットワーク情報取得
        self._debug('Retrieving iRMC network info')
        irmc_net = self._get_irmc_network_info()

        # 結果構築
        result = {
            'changed': False,
            'status': 0,
            'facts': {
                'system': self._build_system_facts(system_data, oem_data),
                'mainboard': self._build_mainboard_facts(system_data),
                'irmc': self._build_irmc_facts(fw_data, irmc_net),
                'hardware': self._get_hardware_info(power_state),
            }
        }

        self._log('Facts retrieval completed successfully')
        return result

    def set(self, params: dict) -> dict:
        """facts設定（setコマンド）を実行します。

        引数:
            params - モジュールパラメータ辞書

        戻り値:
            dict - Ansible module.exit_json()用の結果辞書
        """
        self._log('Starting facts update')

        # 更新ボディ構築（パラメータ検証含む）
        body = self._build_update_body(params)

        # OEMデータ取得（etag取得のため）
        self._debug('Retrieving OEM data for etag')
        oem_data = self._get_oem_data()
        etag = dig(oem_data, '@odata.etag')

        # OEMデータ更新
        self._debug(f'Updating OEM data with {etag=} and {body=}')
        self._patch_oem_data(body, etag)

        self._log('Facts update completed successfully')
        return {'changed': True, 'status': 0}

    def _get_system_data(self) -> dict:
        """システムデータを取得します。

        戻り値:
            dict - システムデータ

        例外:
            HttpError - 取得に失敗した場合
        """
        response = self.irmc.get('redfish/v1/Systems/0/')
        if response.status != 200:
            raise HttpError(
                'Failed to get system data',
                status=response.status,
                details=response.body
            )
        return response.body

    def _get_oem_data(self) -> dict:
        """OEMデータを取得します（M8対応）。

        戻り値:
            dict - OEMデータ

        例外:
            HttpError - 取得に失敗した場合
        """
        path = f'redfish/v1/Systems/0/Oem/{self.irmc.vendor}/System'
        response = self.irmc.get(path)
        if response.status != 200:
            raise HttpError(
                f'Failed to get OEM data from {path}',
                status=response.status,
                details=response.body
            )
        return response.body

    def _get_firmware_data(self) -> dict:
        """ファームウェアデータを取得します（M8対応）。

        戻り値:
            dict - ファームウェアデータ

        例外:
            HttpError - 取得に失敗した場合
        """
        path = f'redfish/v1/Systems/0/Oem/{self.irmc.vendor}/FirmwareInventory'
        response = self.irmc.get(path)
        if response.status != 200:
            raise HttpError(
                f'Failed to get firmware data from {path}',
                status=response.status,
                details=response.body
            )
        return response.body

    def _get_irmc_network_info(self) -> dict:
        """iRMCネットワーク情報を取得します。

        戻り値:
            dict - {'macaddress': str, 'hostname': str}
        """
        response = self.irmc.get('redfish/v1/Managers/iRMC/EthernetInterfaces?$expand=Members')
        if response.status != 200:
            return {'macaddress': None, 'hostname': None}

        members = dig(response.body, 'Members', default=[])
        if members:
            return {
                'macaddress': dig(members[0], 'MACAddress'),
                'hostname': dig(members[0], 'HostName'),
            }
        return {'macaddress': None, 'hostname': None}

    def _build_system_facts(self, system_data: dict, oem_data: dict) -> dict:
        """システムfactsを構築します。

        引数:
            system_data - システムデータ
            oem_data - OEMデータ

        戻り値:
            dict - システムfacts辞書
        """
        return {
            'bios_version': dig(system_data, 'BiosVersion'),
            'idled_state': dig(system_data, 'IndicatorLED'),
            'asset_tag': dig(oem_data, 'AssetTag'),
            'host_name': dig(system_data, 'HostName'),
            'manufacturer': dig(system_data, 'Manufacturer'),
            'model': dig(system_data, 'Model'),
            'part_number': dig(system_data, 'PartNumber'),
            'serial_number': dig(system_data, 'SerialNumber'),
            'uuid': dig(system_data, 'UUID'),
            'ip': dig(oem_data, 'SystemIP'),
            'location': dig(oem_data, 'Location'),
            'description': dig(oem_data, 'Description'),
            'contact': dig(oem_data, 'Contact'),
            'helpdesk_message': dig(oem_data, 'HelpdeskMessage'),
            'power_state': dig(system_data, 'PowerState'),
            'memory_size': f"{dig(system_data, 'MemorySummary', 'TotalSystemMemoryGiB', default=0)} GB",
            'health': dig(system_data, 'Status', 'HealthRollup'),
        }

    def _build_mainboard_facts(self, system_data: dict) -> dict:
        """メインボードfactsを構築します（M8対応）。

        引数:
            system_data - システムデータ

        戻り値:
            dict - メインボードfacts辞書
        """
        return {
            'manufacturer': dig(system_data, 'Oem', self.irmc.vendor, 'MainBoard', 'Manufacturer'),
            'dnumber': dig(system_data, 'Oem', self.irmc.vendor, 'MainBoard', 'Model'),
            'part_number': dig(system_data, 'Oem', self.irmc.vendor, 'MainBoard', 'PartNumber'),
            'serial_number': dig(system_data, 'Oem', self.irmc.vendor, 'MainBoard', 'SerialNumber'),
            'version': dig(system_data, 'Oem', self.irmc.vendor, 'MainBoard', 'Version'),
        }

    def _build_irmc_facts(self, fw_data: dict, irmc_net: dict) -> dict:
        """iRMC factsを構築します。

        引数:
            fw_data - ファームウェアデータ
            irmc_net - iRMCネットワーク情報

        戻り値:
            dict - iRMC facts辞書
        """
        return {
            'fw_version': dig(fw_data, 'BMCFirmware'),
            'fw_builddate': dig(fw_data, 'BMCFirmwareBuildDate'),
            'fw_running': dig(fw_data, 'BMCFirmwareRunning'),
            'sdrr_version': dig(fw_data, 'SDRRVersion'),
            'macaddress': irmc_net.get('macaddress'),
            'hostname': irmc_net.get('hostname'),
        }

    def _get_hardware_info(self, power_state: str) -> dict:
        """ハードウェア情報を取得します。

        引数:
            power_state - 電源状態

        戻り値:
            dict - ハードウェア情報辞書
        """
        hw_info = {}

        # システムハードウェア
        self._debug('Retrieving system hardware (Memory, Processors, EthernetInterfaces, and Storage)')
        hw_info.update(self._get_system_hardware(power_state))

        # シャーシハードウェア
        self._debug('Retrieving chassis hardware (Fans, PowerSupplies)')
        hw_info.update(self._get_chassis_hardware())

        return hw_info

    def _get_system_hardware(self, power_state: str) -> dict:
        """システムハードウェア情報を取得します（Memory, Processors等）。

        引数:
            power_state - 電源状態

        戻り値:
            dict - システムハードウェア情報辞書

        例外:
            HttpError - 取得に失敗した場合
        """
        hw_info = {}

        for hw_type in ('Memory', 'Processors', 'EthernetInterfaces', 'Storage'):
            path = f'redfish/v1/Systems/0/{hw_type}?$expand=Members'
            response = self.irmc.get(path)

            if response.status != 200:
                raise HttpError(
                    f'Failed to get {hw_type}',
                    status=response.status,
                    details=response.body
                )

            members = dig(response.body, 'Members', default=[])
            devices = []

            for member in members:
                if dig(member, 'Status', 'State') == 'Enabled':
                    device = self._extract_device_info(hw_type, member, power_state)
                    if device:
                        devices.append(device)

            hw_dict = {
                'count': len(devices),
                'devices': devices
            }

            if hw_type in ('Memory', 'Processors'):
                hw_dict['sockets'] = dig(response.body, 'Members@odata.count', default=0)

            key = 'storagecontrollers' if hw_type == 'Storage' else hw_type.lower()
            hw_info[key] = hw_dict

        return hw_info

    def _extract_device_info(self, hw_type: str, member: dict, power_state: str) -> dict:
        """デバイス情報を抽出します。

        引数:
            hw_type - ハードウェアタイプ
            member - メンバー辞書
            power_state - 電源状態

        戻り値:
            dict - デバイス情報辞書、またはNone
        """
        if hw_type == 'Memory':
            return {
                'id': dig(member, 'Id'),
                'name': dig(member, 'DeviceLocator'),
                'manufacturer': dig(member, 'Manufacturer'),
                'size': dig(member, 'CapacityMiB'),
            }
        elif hw_type == 'Processors':
            return {
                'id': dig(member, 'Id'),
                'name': dig(member, 'Model'),
                'cores': dig(member, 'TotalCores'),
                'threads': dig(member, 'TotalThreads'),
            }
        elif hw_type == 'EthernetInterfaces':
            name = dig(member, 'Description', default='')
            if not name:
                name = f"{dig(member, 'Name')} {dig(member, 'Id')}"
            return {
                'id': dig(member, 'Id'),
                'name': name,
                'macaddress': dig(member, 'MACAddress'),
            }
        elif hw_type == 'Storage' and power_state == 'On':
            controllers = dig(member, 'StorageControllers', default=[])
            if controllers:
                ctrl = controllers[0]
                return {
                    'id': dig(member, 'Id'),
                    'name': dig(ctrl, 'Model'),
                    'firmware': dig(ctrl, 'FirmwareVersion'),
                    'drives': dig(ctrl, 'Oem', self.irmc.vendor, 'DriveCount'),
                    'volumes': dig(ctrl, 'Oem', self.irmc.vendor, 'VolumeCount'),
                }
        return None

    def _get_chassis_hardware(self) -> dict:
        """シャーシハードウェア情報を取得します（Fans, PowerSupplies）。

        戻り値:
            dict - シャーシハードウェア情報辞書

        例外:
            HttpError - 取得に失敗した場合
        """
        hw_info = {}

        hw_sources = {
            'redfish/v1/Chassis/0/Thermal#/Fans': ['Fans'],
            'redfish/v1/Chassis/0/Power#/PowerSupplies': ['PowerSupplies'],
        }

        for path, hw_list in hw_sources.items():
            response = self.irmc.get(path)
            if response.status != 200:
                raise HttpError(
                    f'Failed to get chassis hardware from {path}',
                    status=response.status,
                    details=response.body
                )

            for hw in hw_list:
                items = dig(response.body, hw, default=[])
                devices = []

                for member in items:
                    if dig(member, 'Status', 'State') == 'Enabled':
                        device = self._extract_chassis_device(hw, member)
                        if device:
                            devices.append(device)

                hw_dict = {
                    'count': len(devices),
                    'devices': devices,
                    'sockets': dig(response.body, f'{hw}@odata.count', default=0)
                }
                hw_info[hw.lower()] = hw_dict

        return hw_info

    def _extract_chassis_device(self, hw_type: str, member: dict) -> dict:
        """シャーシデバイス情報を抽出します。

        引数:
            hw_type - ハードウェアタイプ
            member - メンバー辞書

        戻り値:
            dict - デバイス情報辞書
        """
        if hw_type == 'PowerSupplies':
            return {
                'id': dig(member, 'MemberId'),
                'name': dig(member, 'Name'),
                'manufacturer': dig(member, 'Manufacturer'),
                'model': dig(member, 'Model'),
            }
        else:  # Fans
            return {
                'id': dig(member, 'MemberId'),
                'name': dig(member, 'Name'),
                'location': dig(member, 'PhysicalContext'),
            }

    def _build_update_body(self, params: dict) -> dict:
        """更新ボディを構築します（パラメータ検証含む）。

        引数:
            params - モジュールパラメータ辞書

        戻り値:
            dict - 更新ボディ辞書

        例外:
            ValidationError - 更新パラメータが1つも指定されていない場合
        """
        body = {}
        if params.get('asset_tag') is not None:
            body['AssetTag'] = params['asset_tag']
        if params.get('location') is not None:
            body['Location'] = params['location']
        if params.get('description') is not None:
            body['Description'] = params['description']
        if params.get('contact') is not None:
            body['Contact'] = params['contact']
        if params.get('helpdesk_message') is not None:
            body['HelpdeskMessage'] = params['helpdesk_message']

        # 検証: 最低1つのパラメータが必要
        if not body:
            raise ValidationError(
                "Command 'set' requires at least one parameter to be set!"
            )

        return body

    def _patch_oem_data(self, body: dict, etag: str):
        """OEMデータをPATCHします。

        引数:
            body - 更新ボディ辞書
            etag - etagヘッダー値

        例外:
            ValidationError - etagが無効な場合
            HttpError - PATCH操作に失敗した場合
        """
        if not etag or not str(etag).isdigit():
            raise ValidationError(f'Invalid etag: {etag}')

        path = f'redfish/v1/Systems/0/Oem/{self.irmc.vendor}/System/'
        headers = {'If-Match': str(etag)}

        response = self.irmc.patch(path, body, headers=headers)
        if response.status != 200:
            raise HttpError(
                f'Failed to update OEM data at {path}',
                status=response.status,
                details=response.body
            )


def main():
    """メイン関数"""
    module_args = dict(
        irmc_url=dict(required=True, type='str'),
        irmc_username=dict(required=True, type='str'),
        irmc_password=dict(required=True, type='str', no_log=True),
        validate_certs=dict(required=False, type='bool', default=True),
        command=dict(required=False, type='str', default='get', choices=['get', 'set']),
        asset_tag=dict(required=False, type='str'),
        location=dict(required=False, type='str'),
        description=dict(required=False, type='str'),
        contact=dict(required=False, type='str'),
        helpdesk_message=dict(required=False, type='str'),
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=False,
    )

    if module.check_mode:
        module.exit_json(changed=False, msg='module was not run')

    try:
        # Loggerを作成
        logger = AnsibleLogger(module)

        # iRMCクライアント作成
        irmc = iRMC(
            ipaddress=module.params['irmc_url'],
            username=module.params['irmc_username'],
            password=module.params['irmc_password'],
            validate_certs=module.params['validate_certs'],
            logger=logger
        )

        # Handlerで処理
        handler = FactsHandler(irmc, logger=logger)

        if module.params['command'] == 'get':
            result = handler.get()
        elif module.params['command'] == 'set':
            result = handler.set(module.params)

        if (logs := logger.logs()) is not None:
            result['_logs'] = logs
        module.exit_json(**result)

    except IrmcModuleError as e:
        # iRMCモジュールエラー（汎用ハンドリング）
        params = e.to_fail_json_params()
        if (logs := logger.logs()) is not None:
            params['_logs'] = logs
        module.fail_json(**params)

    except Exception as e:
        # 予期しないエラー
        error_params = {'msg': f'Unexpected error: {str(e)}', 'status': 99}
        if (logs := logger.logs()) is not None:
            error_params['_logs'] = logs
        module.fail_json(**error_params)


if __name__ == '__main__':
    main()

