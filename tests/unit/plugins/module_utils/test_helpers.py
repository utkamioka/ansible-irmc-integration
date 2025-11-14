#!/usr/bin/python

# Copyright 2018-2025 Fsas Technologies Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""helpersモジュールのユニットテスト"""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import pytest

from ansible_collections.fujitsu.primergy.plugins.module_utils.helpers import (
    dig,
)


# ========================================
# Fixtures
# ========================================

@pytest.fixture
def simple_nested_data():
    """シンプルな2階層ネスト構造（浅い階層テスト用）"""
    return {'Status': {'State': 'Enabled'}}


@pytest.fixture
def simple_nested_none():
    """値がNoneの2階層ネスト構造（None値テスト用）"""
    return {'Status': {'State': None}}


@pytest.fixture
def deep_nested_data():
    """深い階層のネスト構造（4階層）"""
    return {
        'user': {
            'profile': {
                'address': {
                    'city': 'Tokyo'
                }
            }
        }
    }


# ========================================
# Tests
# ========================================

class TestDig:
    """dig()関数のテスト"""

    class TestDepth:
        """階層の深さによる取得"""

        def test_shallow(self, simple_nested_data):
            """浅い階層（1-2階層）の取得"""
            # 2階層
            assert dig(simple_nested_data, 'Status', 'State') == 'Enabled'
            # 1階層
            assert dig(simple_nested_data, 'Status') == {'State': 'Enabled'}

        def test_deep(self, deep_nested_data):
            """深い階層（3階層以上）の取得"""
            # 4階層
            result = dig(deep_nested_data, 'user', 'profile', 'address', 'city')
            assert result == 'Tokyo'

    class TestKeyExistence:
        """キーの存在パターン"""

        def test_key_exists(self, simple_nested_data):
            """キーが存在する場合は値を返す"""
            result = dig(simple_nested_data, 'Status', 'State')
            assert result == 'Enabled'

        def test_key_not_exists_with_default(self, simple_nested_data):
            """キーが存在しない場合、defaultを返す"""
            result = dig(simple_nested_data, 'Status', 'Missing', default='Unknown')
            assert result == 'Unknown'

        def test_key_not_exists_without_default(self, simple_nested_data):
            """キーが存在せず、defaultを指定しない場合はNoneを返す"""
            result = dig(simple_nested_data, 'Status', 'Missing')
            assert result is None

        def test_intermediate_key_missing(self):
            """途中のキーが存在しない（辞書でない）場合"""
            data = {'Status': 'Enabled'}  # Statusが辞書でない
            result = dig(data, 'Status', 'State', default='Unknown')
            assert result == 'Unknown'

    class TestNoneHandling:
        """None値の扱い"""

        def test_none_value_with_default(self, simple_nested_none):
            """値がNoneでdefaultを指定した場合、Noneを返す（重要）"""
            result = dig(simple_nested_none, 'Status', 'State', default='Unknown')
            assert result is None  # defaultではなくNone

        def test_none_value_without_default(self, simple_nested_none):
            """値がNoneでdefaultを指定しない場合、Noneを返す"""
            result = dig(simple_nested_none, 'Status', 'State')
            assert result is None

    class TestEdgeCases:
        """その他のエッジケース"""

        def test_empty_keys(self, simple_nested_data):
            """キーを指定しない場合は元のデータを返す"""
            result = dig(simple_nested_data)
            assert result == simple_nested_data
