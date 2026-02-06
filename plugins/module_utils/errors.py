#!/usr/bin/python

# Copyright 2018-2026 Fsas Technologies Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Ansibleモジュール実行時の例外クラス定義モジュールです。"""


class ModuleError(Exception):
    """Ansibleモジュール実行エラーの基底クラスです。

    引数:
        message - エラーメッセージ
    """

    def __init__(self, message: str):
        """ModuleErrorを初期化します。

        引数:
            message - エラーメッセージ
        """
        self.message = message
        super().__init__(self.message)

    def to_fail_dict(self) -> dict:
        """fail_json用の辞書を返します。

        戻り値:
            fail_json用の辞書（msg属性を含む）
        """
        return {'msg': self.message}


class ValidationError(ModuleError):
    """パラメータ検証エラーです。

    モジュールのパラメータが不正な場合に使用します。

    引数:
        message - エラーメッセージ
    """



class HttpError(ModuleError):
    """HTTPリクエストエラーです。

    iRMC APIへのHTTPリクエストが失敗した場合に使用します。

    引数:
        message - エラーメッセージ
        status - HTTPステータスコード
    """

    def __init__(self, message: str, status: int):
        """HttpErrorを初期化します。

        引数:
            message - エラーメッセージ
            status - HTTPステータスコード
        """
        super().__init__(message)
        self.status = status

    def to_fail_dict(self) -> dict:
        """fail_json用の辞書を返します。

        戻り値:
            fail_json用の辞書（msg, status属性を含む）
        """
        return {'msg': self.message, 'status': self.status}
