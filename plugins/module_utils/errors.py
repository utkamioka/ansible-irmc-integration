# Copyright 2018-2025 Fsas Technologies Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Ansible Collection共通エラークラス

このモジュールは、iRMCモジュール全体で使用できる汎用的なエラークラスを提供します。
"""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from typing import Any, Optional


class IrmcModuleError(Exception):
    """Ansibleモジュールの基底エラークラスです。

    全てのiRMCモジュールで使用できる汎用エラークラスです。
    fail_json()に必要な情報を保持します。

    引数:
        message - エラーメッセージ
        status - HTTPステータスコードまたは内部ステータスコード（20-100番台）
        details - 追加の詳細情報（例外オブジェクト、レスポンスボディ等）
    """

    def __init__(
        self,
        message: str,
        status: Optional[int] = None,
        details: Any = None
    ):
        """IrmcModuleErrorを初期化します。

        引数:
            message - エラーメッセージ
            status - HTTPステータスコードまたは内部ステータスコード
            details - 追加の詳細情報
        """
        super().__init__(message)
        self.message = message
        self.status = status
        self.details = details

    def to_fail_json_params(self) -> dict:
        """fail_json()用のパラメータ辞書を生成します。

        戻り値:
            dict - fail_json(**params)で使用できる辞書
        """
        params = {'msg': self.message}

        if self.status is not None:
            params['status'] = self.status

        if self.details is not None:
            # 詳細情報が例外の場合は文字列化
            if isinstance(self.details, Exception):
                params['exception'] = str(self.details)
            else:
                params['exception'] = self.details

        return params


class HttpError(IrmcModuleError):
    """HTTP通信エラーです。

    iRMCへのHTTPリクエストが失敗した場合のエラーです。
    """
    pass


class ValidationError(IrmcModuleError):
    """パラメータ検証エラーです。

    モジュールパラメータの検証に失敗した場合のエラーです。
    ステータスコード10（ビジネスロジックエラー）が自動設定されます。
    """

    def __init__(self, message: str):
        """ValidationErrorを初期化します。

        引数:
            message - エラーメッセージ
        """
        super().__init__(message, status=10)


class ResourceNotFoundError(HttpError):
    """リソースが見つからないエラー（404）です。"""

    def __init__(self, resource: str):
        """ResourceNotFoundErrorを初期化します。

        引数:
            resource - 見つからなかったリソースのパスまたは名前
        """
        super().__init__(f'Resource not found: {resource}', status=404)


class UnauthorizedError(HttpError):
    """認証エラー（401）です。

    iRMCへの認証が失敗した場合のエラーです。
    """

    def __init__(self):
        """UnauthorizedErrorを初期化します。"""
        super().__init__('Authentication failed', status=401)
