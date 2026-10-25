#!/usr/bin/python

# Copyright 2018-2026 Fsas Technologies Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""helpersモジュールのユニットテスト"""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import pytest

import copy

from ansible_collections.fsas.primergy.plugins.module_utils.helpers import (
    dig,
    pem_sha1_fingerprint,
    remove_odata_keys,
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


# ========================================
# remove_odata_keys
# ========================================

class TestRemoveOdataKeys:
    """remove_odata_keys() のテスト"""

    def test_nested_dict_and_list(self):
        """dict と list を再帰的にたどって '@odata' で始まるキーを取り除く"""
        data = {
            '@odata.id': '/redfish/v1/Managers/iRMC/NetworkProtocol/HTTPS/Certificates/Certificate0',
            '@odata.type': '#Certificate.v1_6_0.Certificate',
            'Name': 'HTTPS Certificate',
            'HttpsCertificate': {
                'FingerPrint': 'ba:ea:4a:17',
                'Oem': {'Fsas': {'@odata.type': '#FsasCertificates.v1_0_0.FsasCertificates', 'Version': 3}},
            },
            'Members': [{'@odata.id': '/a'}, {'@odata.id': '/b', 'Id': 'b'}],
        }

        assert remove_odata_keys(data) == {
            'Name': 'HTTPS Certificate',
            'HttpsCertificate': {
                'FingerPrint': 'ba:ea:4a:17',
                'Oem': {'Fsas': {'Version': 3}},
            },
            'Members': [{}, {'Id': 'b'}],
        }

    def test_other_at_keys_are_kept(self):
        """'@odata' 以外の '@' キー（'@Redfish.*' など）は残す"""
        data = {
            '@Redfish.Copyright': 'Copyright',
            'Command@Redfish.AllowableValues': ['A', 'B'],
            'Keys@odata.count': 3,
        }

        assert remove_odata_keys(data) == data

    def test_original_is_not_modified(self):
        """元のオブジェクトは変更しない"""
        data = {'@odata.id': '/redfish/v1', 'Items': [{'@odata.type': 't', 'A': 1}]}
        original = copy.deepcopy(data)

        remove_odata_keys(data)

        assert data == original

    @pytest.mark.parametrize('value', [None, 0, 'text', True])
    def test_scalar_values(self, value):
        """dict / list 以外はそのまま返す"""
        assert remove_odata_keys(value) == value


# ========================================
# pem_sha1_fingerprint
# ========================================

# テスト用の自己署名証明書（EC P-256、CN=helpers-test-a / helpers-test-b）
# フィンガープリントは `openssl x509 -noout -fingerprint -sha1` の値を小文字にしたもの
CERT_A = """-----BEGIN CERTIFICATE-----
MIIBhzCCAS2gAwIBAgIUNMqZAxhe2SrnAOTEuN5Jx2DGBB4wCgYIKoZIzj0EAwIw
GTEXMBUGA1UEAwwOaGVscGVycy10ZXN0LWEwHhcNMjYxMDI1MDUwNDE3WhcNMzYx
MDIyMDUwNDE3WjAZMRcwFQYDVQQDDA5oZWxwZXJzLXRlc3QtYTBZMBMGByqGSM49
AgEGCCqGSM49AwEHA0IABJVb2o4/L/GNqphWdqe6E0DQd3RA/NtqBUOovZW586IM
ssunreaqt+cqUozwYYI/vxdwZerNybBSxxExa9xKd1ijUzBRMB0GA1UdDgQWBBRU
ScUzOO/UZW5XX/kjvL4sl+SUtzAfBgNVHSMEGDAWgBRUScUzOO/UZW5XX/kjvL4s
l+SUtzAPBgNVHRMBAf8EBTADAQH/MAoGCCqGSM49BAMCA0gAMEUCIAjEk9fGbB0P
uHXtolcK9Af3GE0fx9IyiTF9cQouu/5YAiEAr7M/hB6/pSmlC8bAkSNJJnP/c9i2
+J6AGsciHkme6tI=
-----END CERTIFICATE-----
"""
CERT_A_SHA1 = 'd4:55:7c:dc:e0:f7:43:b4:c2:8a:f1:2b:8a:a5:67:4c:9d:b1:5a:05'

CERT_B = """-----BEGIN CERTIFICATE-----
MIIBhzCCAS2gAwIBAgIUJBd9MLSINnzuyg4gurZIJcU56AgwCgYIKoZIzj0EAwIw
GTEXMBUGA1UEAwwOaGVscGVycy10ZXN0LWIwHhcNMjYxMDI1MDUwNDE3WhcNMzYx
MDIyMDUwNDE3WjAZMRcwFQYDVQQDDA5oZWxwZXJzLXRlc3QtYjBZMBMGByqGSM49
AgEGCCqGSM49AwEHA0IABNNALQmCnTL/6KDfDLsWVoalBcOz6OaoJVc6uZ1jM4Ax
CBKoyaPS35yMZHQerxNyM0BqAqYp05pU/kvfFtqk646jUzBRMB0GA1UdDgQWBBTp
dae8ay4eTukaIEIFFZLGAv+LtDAfBgNVHSMEGDAWgBTpdae8ay4eTukaIEIFFZLG
Av+LtDAPBgNVHRMBAf8EBTADAQH/MAoGCCqGSM49BAMCA0gAMEUCIDbL8x+w00+S
jto2YFQdF7HdU33N0UrVTDflKfxa59CdAiEAwWiLygcwvYifI8q6PlwyVxXct4fH
ht4nkrqEPY1Lv7U=
-----END CERTIFICATE-----
"""
CERT_B_SHA1 = '5d:ad:70:6b:40:3e:34:2b:f7:c8:56:9e:55:70:25:6c:2a:00:22:99'


class TestPemSha1Fingerprint:
    """pem_sha1_fingerprint() のテスト"""

    @pytest.mark.parametrize(('pem', 'expected'), [
        (CERT_A, CERT_A_SHA1),
        (CERT_B, CERT_B_SHA1),
    ], ids=['cert_a', 'cert_b'])
    def test_fingerprint(self, pem, expected):
        """openssl と同じフィンガープリントを、小文字の ':' 区切りで返す"""
        assert pem_sha1_fingerprint(pem) == expected

    def test_first_certificate_in_chain(self):
        """証明書が複数ある場合は最初のものを使う"""
        assert pem_sha1_fingerprint(CERT_A + CERT_B) == CERT_A_SHA1
        assert pem_sha1_fingerprint(CERT_B + CERT_A) == CERT_B_SHA1

    def test_crlf_and_surrounding_text(self):
        """改行が CRLF でも、前後に別の文字列があっても同じ値になる"""
        pem = 'subject=CN=helpers-test-a\r\n' + CERT_A.replace('\n', '\r\n')
        assert pem_sha1_fingerprint(pem) == CERT_A_SHA1

    @pytest.mark.parametrize('pem', [
        '',
        '-----BEGIN RSA PRIVATE KEY-----\nMIIB\n-----END RSA PRIVATE KEY-----\n',
        'not a certificate',
    ], ids=['empty', 'private_key', 'text'])
    def test_no_certificate_block(self, pem):
        """証明書のブロックが無ければ ValueError"""
        with pytest.raises(ValueError, match='No PEM certificate block'):
            pem_sha1_fingerprint(pem)

    def test_invalid_base64(self):
        """base64 としてデコードできなければ ValueError"""
        pem = '-----BEGIN CERTIFICATE-----\n!!!not-base64!!!\n-----END CERTIFICATE-----\n'
        with pytest.raises(ValueError, match='not valid base64'):
            pem_sha1_fingerprint(pem)
