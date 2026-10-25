# Copyright 2018-2025 Fsas Technologies Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Ansible Collection共通ヘルパー関数

このモジュールは、JSON処理等の汎用的なユーティリティ関数を提供します。
"""

from __future__ import absolute_import, division, print_function, annotations

__metaclass__ = type

import base64
import binascii
import hashlib
import re
from typing import Any


def dig(data: Any, *keys, default=None) -> Any:
    """ネストされた辞書から値を安全に取得します（Ruby's Hash#dig inspired）。

    この関数名はRubyの Hash#dig メソッドから命名されています。

    キーが存在しない場合はdefaultを返しますが、
    キーが存在して値がNoneの場合はNoneを返します。

    引数:
        data - 検索対象の辞書
        *keys - 取得するキーのパス（可変長引数）
        default - キーが存在しない場合のデフォルト値

    戻り値:
        取得した値、キーが存在しない場合はdefault

    使用例:
        >>> data = {'Status': {'State': 'Enabled'}}
        >>> dig(data, 'Status', 'State')
        'Enabled'

        >>> dig(data, 'Status', 'Missing', default='Unknown')
        'Unknown'

        >>> data2 = {'Status': {'State': None}}
        >>> dig(data2, 'Status', 'State', default='Unknown')
        None  # キーは存在するのでNoneを返す

        >>> data3 = {'count': 0, 'flag': False}
        >>> dig(data3, 'count', default=-1)
        0  # Falsy値もそのまま返す

        >>> dig(data3, 'flag', default=True)
        False  # Falsy値もそのまま返す
    """
    result = data
    for key in keys:
        if isinstance(result, dict):
            # キーの存在を明示的にチェック
            if key in result:
                result = result[key]
            else:
                # キーが存在しない場合のみdefaultを返す
                return default
        else:
            # 辞書でない場合は探索不可
            return default

    # ここまで到達した場合、すべてのキーが存在した
    # 値がNoneや0、False等のFalsy値でもそのまま返す
    return result


def remove_odata_keys(data: Any) -> Any:
    """Redfishのレスポンスから '@odata' で始まるキーを取り除きます。

    dictとlistを再帰的にたどり、'@odata.id' や '@odata.type' などのメタ情報を除いた
    新しいオブジェクトを返します。元のオブジェクトは変更しません。
    '@Redfish.AllowableValues' など '@odata' 以外のキーは残します。

    引数:
        data - Redfishのレスポンス（dict / list / それ以外の値）

    戻り値:
        '@odata' で始まるキーを取り除いたオブジェクト（dict / list 以外はそのまま）

    使用例:
        >>> remove_odata_keys({'@odata.id': '/redfish/v1', 'Name': 'x', 'Items': [{'@odata.type': 't', 'A': 1}]})
        {'Name': 'x', 'Items': [{'A': 1}]}
    """
    if isinstance(data, dict):
        return {
            key: remove_odata_keys(value)
            for key, value in data.items()
            if not (isinstance(key, str) and key.startswith('@odata'))
        }
    if isinstance(data, list):
        return [remove_odata_keys(item) for item in data]
    return data


def pem_sha1_fingerprint(pem: str) -> str:
    """PEM形式の証明書からSHA1フィンガープリントを計算します。

    最初の '-----BEGIN CERTIFICATE-----' ブロックをbase64デコードしたDERのSHA1を、
    iRMCのRedfishが返す形式（小文字16進数を ':' で区切ったもの）で返します。
    'openssl x509 -noout -fingerprint -sha1' の値を小文字にしたものと同じです。

    引数:
        pem - PEM形式の証明書の文字列（証明書チェーンの場合は最初の証明書を使う）

    戻り値:
        SHA1フィンガープリント（例: 'ba:ea:4a:...:6e:0a'）

    例外:
        ValueError - 証明書のブロックが無い、またはbase64としてデコードできない場合
    """
    match = re.search(
        r'-----BEGIN CERTIFICATE-----(.+?)-----END CERTIFICATE-----',
        pem,
        re.DOTALL,
    )
    if match is None:
        raise ValueError('No PEM certificate block (-----BEGIN CERTIFICATE-----) found')

    try:
        der = base64.b64decode(''.join(match.group(1).split()), validate=True)
    except (binascii.Error, ValueError) as e:
        raise ValueError(f'PEM certificate block is not valid base64: {e}') from e

    # 証明書の識別に使うもので、セキュリティ目的のハッシュではない
    digest = hashlib.sha1(der, usedforsecurity=False).hexdigest()
    return ':'.join(digest[i:i + 2] for i in range(0, len(digest), 2))
