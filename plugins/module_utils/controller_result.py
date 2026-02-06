#!/usr/bin/python

# Copyright 2018-2026 Fsas Technologies Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Controllerメソッドの実行結果を表すクラス定義モジュールです。"""


class ControllerResult:
    """Controllerメソッドの実行結果を表すクラスです。

    Ansibleモジュールのexit_json()に渡す戻り値を標準化します。

    引数:
        changed - 変更があったかどうか
        skipped - スキップされたかどうか
        msg - メッセージ
        **kwargs - 追加のフィールド（例: power_state='On'）
    """

    def __init__(
        self,
        changed: bool,
        skipped: bool = False,
        msg: str | None = None,
        **kwargs,
    ):
        """ControllerResultを初期化します。

        引数:
            changed - 変更があったかどうか
            skipped - スキップされたかどうか（デフォルト: False）
            msg - メッセージ（オプション）
            **kwargs - 追加のフィールド
        """
        self.changed = changed
        self.skipped = skipped
        self.msg = msg
        self.extra_fields = kwargs

    def to_exit_dict(self) -> dict:
        """exit_json()用の辞書を返します。

        戻り値:
            exit_json用の辞書（changed, skipped, msg, 追加フィールドを含む）
        """
        result = {'changed': self.changed}
        if self.skipped:
            result['skipped'] = True
        if self.msg is not None:
            result['msg'] = self.msg
        result.update(self.extra_fields)
        return result

    @classmethod
    def unchanged(cls, **kwargs) -> 'ControllerResult':
        """変更なしの結果を返します。

        引数:
            **kwargs - 任意のフィールド

        戻り値:
            changed=Falseのインスタンス
        """
        return cls(changed=False, **kwargs)

    @classmethod
    def changed_success(cls, **kwargs) -> 'ControllerResult':
        """変更成功の結果を返します。

        引数:
            **kwargs - 任意のフィールド

        戻り値:
            changed=Trueのインスタンス
        """
        return cls(changed=True, **kwargs)

    @classmethod
    def skipped(cls, msg: str, **kwargs) -> 'ControllerResult':
        """スキップの結果を返します。

        引数:
            msg - skippedの原因を説明するメッセージ
            **kwargs - 任意のフィールド

        戻り値:
            changed=False, skipped=Trueのインスタンス
        """
        return cls(changed=False, skipped=True, msg=msg, **kwargs)
