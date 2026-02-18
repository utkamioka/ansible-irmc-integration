#!/usr/bin/python

# Copyright 2018-2026 Fsas Technologies Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""irmc_setnextbootモジュールのユニットテストです。"""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from unittest.mock import Mock

import pytest

from ansible_collections.fsas_temp_ns.primergy.plugins.module_utils.errors import HttpError, ValidationError
from ansible_collections.fsas_temp_ns.primergy.plugins.module_utils.irmc_client import Request, Response
from ansible_collections.fsas_temp_ns.primergy.plugins.modules.irmc_setnextboot import SetNextBootController


class TestSetNextBootController:
    """SetNextBootControllerクラスのテストです。"""

    @pytest.fixture
    def mock_irmc(self):
        return Mock()

    @pytest.fixture
    def mock_logger(self):
        return Mock()

    @pytest.fixture
    def controller(self, mock_irmc, mock_logger):
        return SetNextBootController(mock_irmc, mock_logger)

    @pytest.fixture
    def system_response(self):
        return Response(
            body={
                'Boot': {
                    'BootSourceOverrideTarget': 'BiosSetup',
                    'BootSourceOverrideEnabled': 'Once',
                    'BootSourceOverrideMode': 'UEFI',
                    'BootSourceOverrideTarget@Redfish.AllowableValues': ['None', 'Pxe', 'Cd', 'Hdd', 'BiosSetup'],
                    'BootSourceOverrideEnabled@Redfish.AllowableValues': ['Once', 'Continuous']
                },
                '@odata.etag': 'W/"12345"',
            },
            headers={},
            status=200,
            request=Request('GET', '/redfish/v1/Systems/0'),
        )

    def test_execute_no_change(self, controller, mock_irmc, system_response):
        """変更なしのケース"""
        mock_irmc.get.return_value = system_response

        params = {
            'bootsource': 'BiosSetup',
            'bootoverride': 'Once',
            'bootmode': 'UEFI'
        }

        result = controller.execute(params)

        assert result.changed is False
        mock_irmc.patch.assert_not_called()
        # AllowableValues(2回) + CurrentSettings(1回) = 3回
        assert mock_irmc.get.call_count == 3

    def test_execute_change_source(self, controller, mock_irmc, system_response):
        """BootSource変更のケース"""
        mock_irmc.get.return_value = system_response
        mock_irmc.patch.return_value = Response(body={}, headers={}, status=200)

        params = {
            'bootsource': 'Pxe',
            'bootoverride': 'Once',
            'bootmode': 'UEFI'
        }

        result = controller.execute(params)

        assert result.changed is True
        mock_irmc.patch.assert_called_once()
        args = mock_irmc.patch.call_args
        assert args[0][1]['Boot']['BootSourceOverrideTarget'] == 'Pxe'
        # AllowableValues(2回) + CurrentSettings(1回) + ETag(1回) = 4回
        assert mock_irmc.get.call_count == 4

    def test_execute_none_source(self, controller, mock_irmc, system_response):
        """BootSource=Noneのケース"""
        mock_irmc.get.return_value = system_response
        mock_irmc.patch.return_value = Response(body={}, headers={}, status=200)

        params = {
            'bootsource': 'None',
            'bootoverride': 'Once',  # 無視されるべき
            'bootmode': 'UEFI'       # 無視されるべき
        }

        result = controller.execute(params)

        assert result.changed is True
        mock_irmc.patch.assert_called_once()
        body = mock_irmc.patch.call_args[0][1]
        assert body['Boot']['BootSourceOverrideTarget'] == 'None'
        assert 'BootSourceOverrideEnabled' not in body['Boot']

    def test_validation_error_source(self, controller, mock_irmc, system_response):
        """不正なBootSourceのケース"""
        mock_irmc.get.return_value = system_response

        params = {
            'bootsource': 'InvalidSource',
            'bootoverride': 'Once'
        }

        with pytest.raises(ValidationError) as exc:
            controller.execute(params)

        assert "Invalid parameter 'InvalidSource'" in exc.value.message

    def test_validation_error_override(self, controller, mock_irmc, system_response):
        """不正なBootOverrideのケース"""
        mock_irmc.get.return_value = system_response

        params = {
            'bootsource': 'BiosSetup',
            'bootoverride': 'InvalidOverride'
        }

        with pytest.raises(ValidationError) as exc:
            controller.execute(params)

        assert "Invalid parameter 'InvalidOverride'" in exc.value.message

    def test_http_error_get(self, controller, mock_irmc):
        """GET失敗のケース"""
        mock_irmc.get.return_value = Response(body='', headers={}, status=500)

        with pytest.raises(HttpError) as exc:
            controller.execute({'bootsource': 'BiosSetup'})

        assert exc.value.status == 500

    def test_http_error_patch(self, controller, mock_irmc, system_response):
        """PATCH失敗のケース"""
        mock_irmc.get.return_value = system_response
        mock_irmc.patch.return_value = Response(body='', headers={}, status=500)

        params = {
            'bootsource': 'Pxe',
            'bootoverride': 'Once'
        }

        with pytest.raises(HttpError) as exc:
            controller.execute(params)

        assert exc.value.status == 500
