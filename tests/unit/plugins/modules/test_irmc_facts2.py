#!/usr/bin/python

# Copyright 2018-2025 Fsas Technologies Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""irmc_facts2モジュールのユニットテスト"""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import pytest
from unittest.mock import Mock, PropertyMock
from requests.structures import CaseInsensitiveDict

from ansible_collections.fujitsu.primergy.plugins.modules.irmc_facts2 import FactsHandler
from ansible_collections.fujitsu.primergy.plugins.module_utils.irmc_client import Response
from ansible_collections.fujitsu.primergy.plugins.module_utils.logger import MockLogger
from ansible_collections.fujitsu.primergy.plugins.module_utils.errors import (
    ValidationError,
    HttpError,
)


# ==================== Fixtures ====================

@pytest.fixture
def mock_system_data_m7():
    """M7世代のシステムデータ（簡略版）"""
    return {
        'BiosVersion': 'V5.0.0.9 R1.36.0',
        'HostName': 'test-server',
        'Manufacturer': 'FUJITSU',
        'Model': 'PRIMERGY RX1330 M6S',
        'PartNumber': 'TEST-PART-M7',
        'SerialNumber': 'TEST-SN-M7-0001',
        'UUID': 'test0001-1111-2222-3333-444444444444',
        'PowerState': 'On',
        'IndicatorLED': 'Off',
        'MemorySummary': {
            'TotalSystemMemoryGiB': 32
        },
        'Status': {
            'HealthRollup': 'OK'
        },
        'Oem': {
            'ts_fujitsu': {
                'MainBoard': {
                    'Manufacturer': 'FUJITSU',
                    'Model': 'D3289',
                    'PartNumber': 'TEST-MB-PART-M7',
                    'SerialNumber': 'TEST-MB-SN-M7',
                    'Version': 'WGS04 GS50'
                }
            }
        }
    }


@pytest.fixture
def mock_system_data_m8():
    """M8世代のシステムデータ（簡略版）"""
    return {
        'BiosVersion': 'V6.0.0.1 R1.50.0',
        'HostName': 'test-server-m8',
        'Manufacturer': 'Fsas Technologies',
        'Model': 'PRIMERGY RX2530 M8',
        'PartNumber': 'TEST-PART-M8',
        'SerialNumber': 'TEST-SN-M8-0001',
        'UUID': 'test0002-2222-3333-4444-555555555555',
        'PowerState': 'On',
        'IndicatorLED': 'Off',
        'MemorySummary': {
            'TotalSystemMemoryGiB': 64
        },
        'Status': {
            'HealthRollup': 'OK'
        },
        'Oem': {
            'Fsas': {
                'MainBoard': {
                    'Manufacturer': 'Fsas Technologies',
                    'Model': 'D4134-A1',
                    'PartNumber': 'TEST-MB-PART-M8',
                    'SerialNumber': 'TEST-MB-SN-M8',
                    'Version': 'WGS01 GS52'
                }
            }
        }
    }


@pytest.fixture
def mock_oem_data_m7():
    """M7世代のOEMデータ（簡略版）"""
    return {
        '@odata.type': '#FTSSystem.v3_1_0.FTSSystem',
        '@odata.etag': '123456',
        'AssetTag': 'Test Asset Tag',
        'Location': 'Test Location',
        'Description': 'Test Description',
        'Contact': 'Admin <admin@test.local>',
        'HelpdeskMessage': 'Test Helpdesk',
        'SystemIP': '192.0.2.100'
    }


@pytest.fixture
def mock_oem_data_m8():
    """M8世代のOEMデータ（簡略版）"""
    return {
        '@odata.type': '#FsasSystem.v1_0_0.FsasSystem',
        '@odata.etag': '789012',
        'AssetTag': 'Test Asset Tag M8',
        'Location': 'Test Location M8',
        'Description': 'Test Description M8',
        'Contact': 'Admin <admin@test-m8.local>',
        'HelpdeskMessage': 'Test Helpdesk M8',
        'SystemIP': '192.0.2.200'
    }


@pytest.fixture
def mock_firmware_data():
    """ファームウェアデータ（M7/M8共通）"""
    return {
        'BMCFirmware': '3.03S',
        'BMCFirmwareBuildDate': '2025-09-11T02:57:25+09:00',
        'BMCFirmwareRunning': 'HighFWImage',
        'SDRRVersion': '3.24'
    }


@pytest.fixture
def mock_irmc_network_info():
    """iRMCネットワーク情報（M7/M8共通）"""
    return {
        'MACAddress': '00:11:22:33:44:55',
        'HostName': 'iRMC-test'
    }


@pytest.fixture
def create_mock_irmc():
    """モックiRMCインスタンスを作成するファクトリ関数"""
    def _create(vendor='ts_fujitsu', responses=None):
        """
        引数:
            vendor - vendor属性の値（'ts_fujitsu', 'Fsas', None）
            responses - {path: Response} の辞書
        """
        mock_irmc = Mock()
        type(mock_irmc).vendor = PropertyMock(return_value=vendor)

        if responses:
            # get()メソッドのモック設定
            def mock_get(path):
                return responses.get(path, Response({}, CaseInsensitiveDict(), 404))
            mock_irmc.get = Mock(side_effect=mock_get)

            # patch()メソッドのモック設定
            mock_irmc.patch = Mock(return_value=Response({}, CaseInsensitiveDict(), 200))

        return mock_irmc
    return _create


# ==================== TestFactsHandlerInit ====================

class TestFactsHandlerInit:
    """FactsHandler初期化のテスト"""

    def test_init_with_vendor_m7(self, create_mock_irmc):
        """vendor検出成功（M7: ts_fujitsu）"""
        mock_irmc = create_mock_irmc(vendor='ts_fujitsu')
        logger = MockLogger()

        handler = FactsHandler(mock_irmc, logger=logger)

        assert handler.irmc == mock_irmc
        assert handler.logger == logger

        # debugログが出力されることを確認
        debug_logs = [msg for msg in logger.messages['debug'] if 'Detected iRMC vendor' in msg]
        assert len(debug_logs) == 1
        assert 'ts_fujitsu' in debug_logs[0]

    def test_init_with_vendor_m8(self, create_mock_irmc):
        """vendor検出成功（M8: Fsas）"""
        mock_irmc = create_mock_irmc(vendor='Fsas')
        logger = MockLogger()

        handler = FactsHandler(mock_irmc, logger=logger)

        assert handler.irmc == mock_irmc
        assert handler.logger == logger

        # debugログが出力されることを確認
        debug_logs = [msg for msg in logger.messages['debug'] if 'Detected iRMC vendor' in msg]
        assert len(debug_logs) == 1
        assert 'Fsas' in debug_logs[0]

    def test_init_without_vendor_raises_error(self, create_mock_irmc):
        """vendor検出失敗 → ValidationError"""
        mock_irmc = create_mock_irmc(vendor=None)

        with pytest.raises(ValidationError) as exc_info:
            FactsHandler(mock_irmc)

        assert 'Failed to detect iRMC vendor' in str(exc_info.value)
        assert 'Vendor attribute not found in /redfish/v1' in str(exc_info.value)

    def test_init_without_logger(self, create_mock_irmc):
        """loggerなしでの初期化"""
        mock_irmc = create_mock_irmc(vendor='ts_fujitsu')

        handler = FactsHandler(mock_irmc, logger=None)

        assert handler.irmc == mock_irmc
        assert handler.logger is None
        # エラーが発生しないことを確認


# ==================== TestFactsHandlerGet ====================

class TestFactsHandlerGet:
    """FactsHandler.get()メソッドのテスト"""

    def test_get_success_m7(
        self,
        create_mock_irmc,
        mock_system_data_m7,
        mock_oem_data_m7,
        mock_firmware_data,
        mock_irmc_network_info
    ):
        """正常系（M7データ）"""
        # レスポンスの準備
        responses = {
            'redfish/v1/Systems/0/': Response(mock_system_data_m7, CaseInsensitiveDict(), 200),
            'redfish/v1/Systems/0/Oem/ts_fujitsu/System': Response(mock_oem_data_m7, CaseInsensitiveDict(), 200),
            'redfish/v1/Systems/0/Oem/ts_fujitsu/FirmwareInventory': Response(mock_firmware_data, CaseInsensitiveDict(), 200),
            'redfish/v1/Managers/iRMC/EthernetInterfaces?$expand=Members': Response(
                {'Members': [mock_irmc_network_info]},
                CaseInsensitiveDict(),
                200
            ),
            # ハードウェア情報（簡略版）
            'redfish/v1/Systems/0/Memory?$expand=Members': Response({'Members': [], 'Members@odata.count': 0}, CaseInsensitiveDict(), 200),
            'redfish/v1/Systems/0/Processors?$expand=Members': Response({'Members': [], 'Members@odata.count': 0}, CaseInsensitiveDict(), 200),
            'redfish/v1/Systems/0/EthernetInterfaces?$expand=Members': Response({'Members': []}, CaseInsensitiveDict(), 200),
            'redfish/v1/Systems/0/Storage?$expand=Members': Response({'Members': []}, CaseInsensitiveDict(), 200),
            'redfish/v1/Chassis/0/Thermal#/Fans': Response({'Fans': [], 'Fans@odata.count': 0}, CaseInsensitiveDict(), 200),
            'redfish/v1/Chassis/0/Power#/PowerSupplies': Response({'PowerSupplies': [], 'PowerSupplies@odata.count': 0}, CaseInsensitiveDict(), 200),
        }

        mock_irmc = create_mock_irmc(vendor='ts_fujitsu', responses=responses)
        handler = FactsHandler(mock_irmc)

        # 実行
        result = handler.get()

        # 検証
        assert result['changed'] is False
        assert result['status'] == 0
        assert 'facts' in result
        assert 'system' in result['facts']
        assert 'mainboard' in result['facts']
        assert 'irmc' in result['facts']
        assert 'hardware' in result['facts']

        # システム情報
        assert result['facts']['system']['model'] == 'PRIMERGY RX1330 M6S'
        assert result['facts']['system']['serial_number'] == 'TEST-SN-M7-0001'
        assert result['facts']['system']['asset_tag'] == 'Test Asset Tag'

        # メインボード情報
        assert result['facts']['mainboard']['manufacturer'] == 'FUJITSU'
        assert result['facts']['mainboard']['dnumber'] == 'D3289'

        # iRMC情報
        assert result['facts']['irmc']['fw_version'] == '3.03S'
        assert result['facts']['irmc']['macaddress'] == '00:11:22:33:44:55'

    def test_get_success_m8(
        self,
        create_mock_irmc,
        mock_system_data_m8,
        mock_oem_data_m8,
        mock_firmware_data,
        mock_irmc_network_info
    ):
        """正常系（M8データ）"""
        # レスポンスの準備
        responses = {
            'redfish/v1/Systems/0/': Response(mock_system_data_m8, CaseInsensitiveDict(), 200),
            'redfish/v1/Systems/0/Oem/Fsas/System': Response(mock_oem_data_m8, CaseInsensitiveDict(), 200),
            'redfish/v1/Systems/0/Oem/Fsas/FirmwareInventory': Response(mock_firmware_data, CaseInsensitiveDict(), 200),
            'redfish/v1/Managers/iRMC/EthernetInterfaces?$expand=Members': Response(
                {'Members': [mock_irmc_network_info]},
                CaseInsensitiveDict(),
                200
            ),
            # ハードウェア情報（簡略版）
            'redfish/v1/Systems/0/Memory?$expand=Members': Response({'Members': [], 'Members@odata.count': 0}, CaseInsensitiveDict(), 200),
            'redfish/v1/Systems/0/Processors?$expand=Members': Response({'Members': [], 'Members@odata.count': 0}, CaseInsensitiveDict(), 200),
            'redfish/v1/Systems/0/EthernetInterfaces?$expand=Members': Response({'Members': []}, CaseInsensitiveDict(), 200),
            'redfish/v1/Systems/0/Storage?$expand=Members': Response({'Members': []}, CaseInsensitiveDict(), 200),
            'redfish/v1/Chassis/0/Thermal#/Fans': Response({'Fans': [], 'Fans@odata.count': 0}, CaseInsensitiveDict(), 200),
            'redfish/v1/Chassis/0/Power#/PowerSupplies': Response({'PowerSupplies': [], 'PowerSupplies@odata.count': 0}, CaseInsensitiveDict(), 200),
        }

        mock_irmc = create_mock_irmc(vendor='Fsas', responses=responses)
        handler = FactsHandler(mock_irmc)

        # 実行
        result = handler.get()

        # 検証
        assert result['changed'] is False
        assert result['status'] == 0

        # システム情報（M8の値を確認）
        assert result['facts']['system']['model'] == 'PRIMERGY RX2530 M8'
        assert result['facts']['system']['serial_number'] == 'TEST-SN-M8-0001'
        assert result['facts']['system']['asset_tag'] == 'Test Asset Tag M8'

        # メインボード情報（M8の値を確認）
        assert result['facts']['mainboard']['manufacturer'] == 'Fsas Technologies'
        assert result['facts']['mainboard']['dnumber'] == 'D4134-A1'

    def test_get_system_data_error(self, create_mock_irmc):
        """システムデータ取得失敗 → HttpError"""
        responses = {
            'redfish/v1/Systems/0/': Response({'error': 'Not Found'}, CaseInsensitiveDict(), 404),
        }

        mock_irmc = create_mock_irmc(vendor='ts_fujitsu', responses=responses)
        handler = FactsHandler(mock_irmc)

        with pytest.raises(HttpError) as exc_info:
            handler.get()

        assert 'Failed to get system data' in str(exc_info.value)

    def test_get_oem_data_error(
        self,
        create_mock_irmc,
        mock_system_data_m7
    ):
        """OEMデータ取得失敗 → HttpError"""
        responses = {
            'redfish/v1/Systems/0/': Response(mock_system_data_m7, CaseInsensitiveDict(), 200),
            'redfish/v1/Systems/0/Oem/ts_fujitsu/System': Response({'error': 'Not Found'}, CaseInsensitiveDict(), 404),
        }

        mock_irmc = create_mock_irmc(vendor='ts_fujitsu', responses=responses)
        handler = FactsHandler(mock_irmc)

        with pytest.raises(HttpError) as exc_info:
            handler.get()

        assert 'Failed to get OEM data' in str(exc_info.value)

    def test_get_firmware_data_error(
        self,
        create_mock_irmc,
        mock_system_data_m7,
        mock_oem_data_m7
    ):
        """ファームウェアデータ取得失敗 → HttpError"""
        responses = {
            'redfish/v1/Systems/0/': Response(mock_system_data_m7, CaseInsensitiveDict(), 200),
            'redfish/v1/Systems/0/Oem/ts_fujitsu/System': Response(mock_oem_data_m7, CaseInsensitiveDict(), 200),
            'redfish/v1/Systems/0/Oem/ts_fujitsu/FirmwareInventory': Response({'error': 'Not Found'}, CaseInsensitiveDict(), 404),
        }

        mock_irmc = create_mock_irmc(vendor='ts_fujitsu', responses=responses)
        handler = FactsHandler(mock_irmc)

        with pytest.raises(HttpError) as exc_info:
            handler.get()

        assert 'Failed to get firmware data' in str(exc_info.value)

    def test_get_network_info_failure_returns_none(
        self,
        create_mock_irmc,
        mock_system_data_m7,
        mock_oem_data_m7,
        mock_firmware_data
    ):
        """ネットワーク情報取得失敗時はNoneを返す"""
        responses = {
            'redfish/v1/Systems/0/': Response(mock_system_data_m7, CaseInsensitiveDict(), 200),
            'redfish/v1/Systems/0/Oem/ts_fujitsu/System': Response(mock_oem_data_m7, CaseInsensitiveDict(), 200),
            'redfish/v1/Systems/0/Oem/ts_fujitsu/FirmwareInventory': Response(mock_firmware_data, CaseInsensitiveDict(), 200),
            'redfish/v1/Managers/iRMC/EthernetInterfaces?$expand=Members': Response({'error': 'Not Found'}, CaseInsensitiveDict(), 404),
            # ハードウェア情報
            'redfish/v1/Systems/0/Memory?$expand=Members': Response({'Members': [], 'Members@odata.count': 0}, CaseInsensitiveDict(), 200),
            'redfish/v1/Systems/0/Processors?$expand=Members': Response({'Members': [], 'Members@odata.count': 0}, CaseInsensitiveDict(), 200),
            'redfish/v1/Systems/0/EthernetInterfaces?$expand=Members': Response({'Members': []}, CaseInsensitiveDict(), 200),
            'redfish/v1/Systems/0/Storage?$expand=Members': Response({'Members': []}, CaseInsensitiveDict(), 200),
            'redfish/v1/Chassis/0/Thermal#/Fans': Response({'Fans': [], 'Fans@odata.count': 0}, CaseInsensitiveDict(), 200),
            'redfish/v1/Chassis/0/Power#/PowerSupplies': Response({'PowerSupplies': [], 'PowerSupplies@odata.count': 0}, CaseInsensitiveDict(), 200),
        }

        mock_irmc = create_mock_irmc(vendor='ts_fujitsu', responses=responses)
        handler = FactsHandler(mock_irmc)

        result = handler.get()

        # ネットワーク情報がNoneであることを確認
        assert result['facts']['irmc']['macaddress'] is None
        assert result['facts']['irmc']['hostname'] is None


# ==================== TestFactsHandlerSet ====================

class TestFactsHandlerSet:
    """FactsHandler.set()メソッドのテスト"""

    def test_set_success_m7(self, create_mock_irmc, mock_oem_data_m7):
        """正常系（M7データ）- asset_tagを更新"""
        # レスポンスの準備
        responses = {
            'redfish/v1/Systems/0/Oem/ts_fujitsu/System': Response(
                mock_oem_data_m7,
                CaseInsensitiveDict(),
                200
            ),
        }

        mock_irmc = create_mock_irmc(vendor='ts_fujitsu', responses=responses)
        handler = FactsHandler(mock_irmc)

        # パラメータ
        params = {'asset_tag': 'New Asset Tag'}

        # 実行
        result = handler.set(params)

        # 検証
        assert result['changed'] is True

        # patch()が呼ばれたことを確認
        mock_irmc.patch.assert_called_once()
        call_args = mock_irmc.patch.call_args

        # パス確認
        assert call_args[0][0] == 'redfish/v1/Systems/0/Oem/ts_fujitsu/System/'

        # ボディ確認
        assert call_args[0][1] == {'AssetTag': 'New Asset Tag'}

        # ヘッダー確認
        assert call_args[1]['headers'] == {'If-Match': '123456'}

    def test_set_success_m8_multiple_params(self, create_mock_irmc, mock_oem_data_m8):
        """正常系（M8データ）- 複数パラメータを更新"""
        # レスポンスの準備
        responses = {
            'redfish/v1/Systems/0/Oem/Fsas/System': Response(
                mock_oem_data_m8,
                CaseInsensitiveDict(),
                200
            ),
        }

        mock_irmc = create_mock_irmc(vendor='Fsas', responses=responses)
        handler = FactsHandler(mock_irmc)

        # パラメータ（複数）
        params = {
            'asset_tag': 'New Asset M8',
            'location': 'New Location M8',
            'contact': 'new-admin@test.local',
        }

        # 実行
        result = handler.set(params)

        # 検証
        assert result['changed'] is True

        # patch()の呼び出し確認
        call_args = mock_irmc.patch.call_args

        # パス確認（M8はFsas）
        assert call_args[0][0] == 'redfish/v1/Systems/0/Oem/Fsas/System/'

        # ボディ確認
        assert call_args[0][1] == {
            'AssetTag': 'New Asset M8',
            'Location': 'New Location M8',
            'Contact': 'new-admin@test.local',
        }

    def test_set_validation_error_no_params(self, create_mock_irmc):
        """パラメータ検証エラー - 必須パラメータがない"""
        mock_irmc = create_mock_irmc(vendor='ts_fujitsu')
        handler = FactsHandler(mock_irmc)

        # 空のパラメータ
        params = {}

        # 実行 → ValidationError
        with pytest.raises(ValidationError) as exc_info:
            handler.set(params)

        assert "requires at least one parameter to be set" in str(exc_info.value)

    def test_set_invalid_etag(self, create_mock_irmc):
        """etagが不正 → ValidationError"""
        # etagが無効なレスポンス
        invalid_oem_data = {
            '@odata.etag': 'invalid_etag',  # 数値でない
            'AssetTag': 'Test',
        }
        responses = {
            'redfish/v1/Systems/0/Oem/ts_fujitsu/System': Response(
                invalid_oem_data,
                CaseInsensitiveDict(),
                200
            ),
        }

        mock_irmc = create_mock_irmc(vendor='ts_fujitsu', responses=responses)
        handler = FactsHandler(mock_irmc)

        params = {'asset_tag': 'New Tag'}

        # 実行 → ValidationError
        with pytest.raises(ValidationError) as exc_info:
            handler.set(params)

        assert 'Invalid etag' in str(exc_info.value)

    def test_set_patch_error(self, create_mock_irmc, mock_oem_data_m7):
        """PATCH失敗 → HttpError"""
        # OEM取得は成功
        responses = {
            'redfish/v1/Systems/0/Oem/ts_fujitsu/System': Response(
                mock_oem_data_m7,
                CaseInsensitiveDict(),
                200
            ),
        }

        mock_irmc = create_mock_irmc(vendor='ts_fujitsu', responses=responses)

        # patch()は失敗を返す
        mock_irmc.patch = Mock(return_value=Response(
            {'error': 'Forbidden'},
            CaseInsensitiveDict(),
            403
        ))

        handler = FactsHandler(mock_irmc)

        params = {'asset_tag': 'New Tag'}

        # 実行 → HttpError
        with pytest.raises(HttpError) as exc_info:
            handler.set(params)

        assert 'Failed to update OEM data' in str(exc_info.value)


# ==================== TestFactsHandlerDataBuild ====================

class TestFactsHandlerDataBuild:
    """データ構築メソッドのテスト"""

    def test_build_system_facts_m7(self, create_mock_irmc, mock_system_data_m7, mock_oem_data_m7):
        """_build_system_facts() - M7データ"""
        mock_irmc = create_mock_irmc(vendor='ts_fujitsu')
        handler = FactsHandler(mock_irmc)

        result = handler._build_system_facts(mock_system_data_m7, mock_oem_data_m7)

        # 検証
        assert result['bios_version'] == 'V5.0.0.9 R1.36.0'
        assert result['host_name'] == 'test-server'
        assert result['manufacturer'] == 'FUJITSU'
        assert result['model'] == 'PRIMERGY RX1330 M6S'
        assert result['serial_number'] == 'TEST-SN-M7-0001'
        assert result['uuid'] == 'test0001-1111-2222-3333-444444444444'
        assert result['power_state'] == 'On'
        assert result['memory_size'] == '32 GB'
        assert result['health'] == 'OK'
        assert result['asset_tag'] == 'Test Asset Tag'
        assert result['location'] == 'Test Location'
        assert result['contact'] == 'Admin <admin@test.local>'

    def test_build_system_facts_m8(self, create_mock_irmc, mock_system_data_m8, mock_oem_data_m8):
        """_build_system_facts() - M8データ"""
        mock_irmc = create_mock_irmc(vendor='Fsas')
        handler = FactsHandler(mock_irmc)

        result = handler._build_system_facts(mock_system_data_m8, mock_oem_data_m8)

        # 検証（M8の値）
        assert result['bios_version'] == 'V6.0.0.1 R1.50.0'
        assert result['host_name'] == 'test-server-m8'
        assert result['manufacturer'] == 'Fsas Technologies'
        assert result['model'] == 'PRIMERGY RX2530 M8'
        assert result['memory_size'] == '64 GB'

    def test_build_mainboard_facts_m7(self, create_mock_irmc, mock_system_data_m7):
        """_build_mainboard_facts() - M7データ"""
        mock_irmc = create_mock_irmc(vendor='ts_fujitsu')
        handler = FactsHandler(mock_irmc)

        result = handler._build_mainboard_facts(mock_system_data_m7)

        # 検証
        assert result['manufacturer'] == 'FUJITSU'
        assert result['dnumber'] == 'D3289'
        assert result['part_number'] == 'TEST-MB-PART-M7'
        assert result['serial_number'] == 'TEST-MB-SN-M7'
        assert result['version'] == 'WGS04 GS50'

    def test_build_mainboard_facts_m8(self, create_mock_irmc, mock_system_data_m8):
        """_build_mainboard_facts() - M8データ"""
        mock_irmc = create_mock_irmc(vendor='Fsas')
        handler = FactsHandler(mock_irmc)

        result = handler._build_mainboard_facts(mock_system_data_m8)

        # 検証（M8の値）
        assert result['manufacturer'] == 'Fsas Technologies'
        assert result['dnumber'] == 'D4134-A1'
        assert result['part_number'] == 'TEST-MB-PART-M8'
        assert result['serial_number'] == 'TEST-MB-SN-M8'

    def test_build_irmc_facts(self, create_mock_irmc, mock_firmware_data):
        """_build_irmc_facts() - ファームウェアとネットワーク情報"""
        mock_irmc = create_mock_irmc(vendor='ts_fujitsu')
        handler = FactsHandler(mock_irmc)

        # _get_irmc_network_info()が返すフォーマット（小文字のキー）
        irmc_net = {
            'macaddress': '00:11:22:33:44:55',
            'hostname': 'iRMC-test'
        }

        result = handler._build_irmc_facts(mock_firmware_data, irmc_net)

        # 検証
        assert result['fw_version'] == '3.03S'
        assert result['fw_builddate'] == '2025-09-11T02:57:25+09:00'
        assert result['fw_running'] == 'HighFWImage'
        assert result['sdrr_version'] == '3.24'
        assert result['macaddress'] == '00:11:22:33:44:55'
        assert result['hostname'] == 'iRMC-test'


# ==================== TestFactsHandlerHardware ====================

class TestFactsHandlerHardware:
    """ハードウェア情報抽出メソッドのテスト"""

    def test_extract_device_info_memory(self, create_mock_irmc):
        """_extract_device_info() - Memoryデバイス"""
        mock_irmc = create_mock_irmc(vendor='ts_fujitsu')
        handler = FactsHandler(mock_irmc)

        member = {
            'Id': 'DIMM_1A',
            'DeviceLocator': 'DIMM 1A',
            'Manufacturer': 'Samsung',
            'CapacityMiB': 16384,
        }

        result = handler._extract_device_info('Memory', member, 'On')

        assert result['id'] == 'DIMM_1A'
        assert result['name'] == 'DIMM 1A'
        assert result['manufacturer'] == 'Samsung'
        assert result['size'] == 16384

    def test_extract_device_info_processors(self, create_mock_irmc):
        """_extract_device_info() - Processorsデバイス"""
        mock_irmc = create_mock_irmc(vendor='ts_fujitsu')
        handler = FactsHandler(mock_irmc)

        member = {
            'Id': 'CPU1',
            'Model': 'Intel(R) Xeon(R) Gold 6326 CPU @ 2.90GHz',
            'TotalCores': 16,
            'TotalThreads': 32,
        }

        result = handler._extract_device_info('Processors', member, 'On')

        assert result['id'] == 'CPU1'
        assert result['name'] == 'Intel(R) Xeon(R) Gold 6326 CPU @ 2.90GHz'
        assert result['cores'] == 16
        assert result['threads'] == 32

    def test_extract_device_info_ethernetinterfaces(self, create_mock_irmc):
        """_extract_device_info() - EthernetInterfacesデバイス"""
        mock_irmc = create_mock_irmc(vendor='ts_fujitsu')
        handler = FactsHandler(mock_irmc)

        member = {
            'Id': 'NIC.Slot.1-1',
            'Description': 'Intel I350 Gigabit Network Connection',
            'Name': 'NIC',
            'MACAddress': 'AA:BB:CC:DD:EE:FF',
        }

        result = handler._extract_device_info('EthernetInterfaces', member, 'On')

        assert result['id'] == 'NIC.Slot.1-1'
        assert result['name'] == 'Intel I350 Gigabit Network Connection'
        assert result['macaddress'] == 'AA:BB:CC:DD:EE:FF'

    def test_extract_device_info_storage_power_on_m7(self, create_mock_irmc):
        """_extract_device_info() - Storageデバイス（power_state='On', M7）"""
        mock_irmc = create_mock_irmc(vendor='ts_fujitsu')
        handler = FactsHandler(mock_irmc)

        member = {
            'Id': 'RAIDAdapter0',
            'StorageControllers': [
                {
                    'Model': 'LSI MegaRAID SAS 9361-8i',
                    'FirmwareVersion': '4.680.00-8321',
                    'Oem': {
                        'ts_fujitsu': {
                            'DriveCount': 4,
                            'VolumeCount': 2,
                        }
                    }
                }
            ]
        }

        result = handler._extract_device_info('Storage', member, 'On')

        assert result['id'] == 'RAIDAdapter0'
        assert result['name'] == 'LSI MegaRAID SAS 9361-8i'
        assert result['firmware'] == '4.680.00-8321'
        assert result['drives'] == 4
        assert result['volumes'] == 2

    def test_extract_device_info_storage_power_off_returns_none(self, create_mock_irmc):
        """_extract_device_info() - Storageデバイス（power_state='Off' → None）"""
        mock_irmc = create_mock_irmc(vendor='ts_fujitsu')
        handler = FactsHandler(mock_irmc)

        member = {
            'Id': 'RAIDAdapter0',
            'StorageControllers': [
                {
                    'Model': 'LSI MegaRAID SAS 9361-8i',
                    'FirmwareVersion': '4.680.00-8321',
                }
            ]
        }

        result = handler._extract_device_info('Storage', member, 'Off')

        # power_state='Off'の場合はNoneを返す
        assert result is None
