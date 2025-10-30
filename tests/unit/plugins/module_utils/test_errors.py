#!/usr/bin/python

# Copyright 2018-2025 Fsas Technologies Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""errorsモジュールのユニットテスト"""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import pytest

from ansible_collections.fujitsu.primergy.plugins.module_utils.errors import (
    IrmcModuleError,
    HttpError,
    ValidationError,
    ResourceNotFoundError,
    UnauthorizedError,
)


class TestIrmcModuleError:
    """IrmcModuleErrorクラスのテスト"""

    def test_init_with_message_only(self):
        """メッセージのみで初期化"""
        error = IrmcModuleError('Test error')
        assert error.message == 'Test error'
        assert error.status is None
        assert error.details is None

    def test_init_with_all_params(self):
        """全パラメータで初期化"""
        error = IrmcModuleError('Test error', status=500, details='Extra info')
        assert error.message == 'Test error'
        assert error.status == 500
        assert error.details == 'Extra info'

    def test_to_fail_json_params_message_only(self):
        """メッセージのみの場合のfail_json_params"""
        error = IrmcModuleError('Test error')
        params = error.to_fail_json_params()
        assert params == {'msg': 'Test error'}

    def test_to_fail_json_params_with_status(self):
        """ステータス付きの場合のfail_json_params"""
        error = IrmcModuleError('Test error', status=500)
        params = error.to_fail_json_params()
        assert params == {'msg': 'Test error', 'status': 500}

    def test_to_fail_json_params_with_details_string(self):
        """詳細情報（文字列）付きの場合のfail_json_params"""
        error = IrmcModuleError('Test error', status=500, details='Extra info')
        params = error.to_fail_json_params()
        assert params == {
            'msg': 'Test error',
            'status': 500,
            'exception': 'Extra info'
        }

    def test_to_fail_json_params_with_details_exception(self):
        """詳細情報（例外）付きの場合のfail_json_params"""
        exc = ValueError('Invalid value')
        error = IrmcModuleError('Test error', status=99, details=exc)
        params = error.to_fail_json_params()
        assert params['msg'] == 'Test error'
        assert params['status'] == 99
        assert 'Invalid value' in params['exception']

    def test_to_fail_json_params_with_details_dict(self):
        """詳細情報（辞書）付きの場合のfail_json_params"""
        details = {'error': {'message': 'Something went wrong'}}
        error = IrmcModuleError('Test error', status=500, details=details)
        params = error.to_fail_json_params()
        assert params == {
            'msg': 'Test error',
            'status': 500,
            'exception': details
        }

    def test_exception_message(self):
        """例外メッセージが正しく設定される"""
        error = IrmcModuleError('Test error')
        assert str(error) == 'Test error'


class TestHttpError:
    """HttpErrorクラスのテスト"""

    def test_http_error_inherits_from_irmc_module_error(self):
        """IrmcModuleErrorを継承している"""
        error = HttpError('HTTP error', status=500)
        assert isinstance(error, IrmcModuleError)
        assert error.message == 'HTTP error'
        assert error.status == 500

    def test_http_error_to_fail_json_params(self):
        """fail_json_paramsが正しく動作する"""
        error = HttpError('Connection failed', status=503, details='Timeout')
        params = error.to_fail_json_params()
        assert params == {
            'msg': 'Connection failed',
            'status': 503,
            'exception': 'Timeout'
        }


class TestValidationError:
    """ValidationErrorクラスのテスト"""

    def test_validation_error_auto_status(self):
        """ステータスが自動的に10に設定される"""
        error = ValidationError('Invalid parameter')
        assert error.message == 'Invalid parameter'
        assert error.status == 10
        assert error.details is None

    def test_validation_error_to_fail_json_params(self):
        """fail_json_paramsが正しく動作する"""
        error = ValidationError('Required parameter missing')
        params = error.to_fail_json_params()
        assert params == {
            'msg': 'Required parameter missing',
            'status': 10
        }

    def test_validation_error_inherits_from_irmc_module_error(self):
        """IrmcModuleErrorを継承している"""
        error = ValidationError('Validation failed')
        assert isinstance(error, IrmcModuleError)


class TestResourceNotFoundError:
    """ResourceNotFoundErrorクラスのテスト"""

    def test_resource_not_found_error_message_format(self):
        """メッセージが正しくフォーマットされる"""
        error = ResourceNotFoundError('/redfish/v1/Systems/0')
        assert error.message == 'Resource not found: /redfish/v1/Systems/0'
        assert error.status == 404

    def test_resource_not_found_error_inherits_from_http_error(self):
        """HttpErrorを継承している"""
        error = ResourceNotFoundError('/some/path')
        assert isinstance(error, HttpError)
        assert isinstance(error, IrmcModuleError)

    def test_resource_not_found_error_to_fail_json_params(self):
        """fail_json_paramsが正しく動作する"""
        error = ResourceNotFoundError('/api/resource')
        params = error.to_fail_json_params()
        assert params == {
            'msg': 'Resource not found: /api/resource',
            'status': 404
        }


class TestUnauthorizedError:
    """UnauthorizedErrorクラスのテスト"""

    def test_unauthorized_error_fixed_message(self):
        """固定メッセージが設定される"""
        error = UnauthorizedError()
        assert error.message == 'Authentication failed'
        assert error.status == 401

    def test_unauthorized_error_inherits_from_http_error(self):
        """HttpErrorを継承している"""
        error = UnauthorizedError()
        assert isinstance(error, HttpError)
        assert isinstance(error, IrmcModuleError)

    def test_unauthorized_error_to_fail_json_params(self):
        """fail_json_paramsが正しく動作する"""
        error = UnauthorizedError()
        params = error.to_fail_json_params()
        assert params == {
            'msg': 'Authentication failed',
            'status': 401
        }


class TestErrorHierarchy:
    """エラークラスの階層構造のテスト"""

    def test_error_hierarchy(self):
        """エラークラスの継承関係を確認"""
        # IrmcModuleErrorが基底
        assert issubclass(HttpError, IrmcModuleError)
        assert issubclass(ValidationError, IrmcModuleError)

        # HttpErrorの派生
        assert issubclass(ResourceNotFoundError, HttpError)
        assert issubclass(UnauthorizedError, HttpError)

        # 全て Exception を継承
        assert issubclass(IrmcModuleError, Exception)
        assert issubclass(HttpError, Exception)
        assert issubclass(ValidationError, Exception)
        assert issubclass(ResourceNotFoundError, Exception)
        assert issubclass(UnauthorizedError, Exception)
