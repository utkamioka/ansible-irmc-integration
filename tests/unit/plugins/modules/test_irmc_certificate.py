#!/usr/bin/python

# Copyright 2018-2026 Fsas Technologies Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""irmc_certificateモジュールのユニットテストです。"""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import copy
from unittest.mock import Mock, patch

import pytest

from ansible_collections.fsas.primergy.plugins.module_utils.errors import HttpError, ModuleError, ValidationError
from ansible_collections.fsas.primergy.plugins.module_utils.helpers import pem_sha1_fingerprint
from ansible_collections.fsas.primergy.plugins.module_utils.irmc_client import Request, Response
from ansible_collections.fsas.primergy.plugins.modules.irmc_certificate import (
    CERTIFICATE0_PATH,
    CertificateController,
)

# vendorごとのテスト（ts_fujitsu: M7以前、Fsas: M8以降）
VENDORS = [
    pytest.param('ts_fujitsu', id='ts_fujitsu'),
    pytest.param('Fsas', id='Fsas'),
]

# テスト用の自己署名証明書（EC P-256）。フィンガープリントは openssl で計算した値を小文字にしたもの
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

CERT_C = """-----BEGIN CERTIFICATE-----
MIIBjzCCATWgAwIBAgIUGGze15zFT54kAzJV2VCfJhFqG04wCgYIKoZIzj0EAwIw
HTEbMBkGA1UEAwwSY2VydGlmaWNhdGUtdGVzdC1jMB4XDTI2MTAyNTA1MDYzMFoX
DTM2MTAyMjA1MDYzMFowHTEbMBkGA1UEAwwSY2VydGlmaWNhdGUtdGVzdC1jMFkw
EwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAE1BYhXICpOwaAQ1Uadgjo454SJluNwskV
nmI+0ksDkBA6K/FWTX6clNSyhE4+jrqFWIV/NjUlAAJGIJOaos2qvqNTMFEwHQYD
VR0OBBYEFAd5zhdijUjKFYoPLBXxRaL80g1AMB8GA1UdIwQYMBaAFAd5zhdijUjK
FYoPLBXxRaL80g1AMA8GA1UdEwEB/wQFMAMBAf8wCgYIKoZIzj0EAwIDSAAwRQIh
AOcjAbBnQnTSJ2bTCE1415NYcZ+4tfxnixwugHkU50sxAiACZJmYmSfwJksXRjkq
HEwVqXkdf64dELbrDuiFy3KfqA==
-----END CERTIFICATE-----
"""
CERT_C_SHA1 = '64:43:7c:10:3a:e9:bf:d0:8b:aa:e6:ce:88:de:8c:26:43:f7:3a:fe'

# 秘密鍵の中身はモジュールが解釈しないので、ダミーで良い
DUMMY_KEY = '-----BEGIN PRIVATE KEY-----\nDUMMY\n-----END PRIVATE KEY-----\n'


def oem_prefix_of(vendor):
    """ベンダーに対応するOEMアクション名の接頭辞を返します。"""
    return 'FTS' if vendor == 'ts_fujitsu' else 'Fsas'


def ca_path(vendor):
    """証明書設定リソースのパスを返します。"""
    return f'/redfish/v1/Managers/iRMC/Oem/{vendor}/iRMCConfiguration/Certificates'


def replace_path(vendor):
    """ReplaceCertificateアクションのパスを返します。"""
    return f'{CERTIFICATE0_PATH}/Actions/Oem/{oem_prefix_of(vendor)}Certificates.ReplaceCertificate'


def upload_ca_path(vendor):
    """UploadCACertificateアクションのパスを返します。"""
    return f'{ca_path(vendor)}/Actions/{oem_prefix_of(vendor)}Certificates.UploadCACertificate'


def initial_state(vendor):
    """iRMCの初期状態（実機ログを元にしたもの）を返します。TLS証明書はCERT_A、CA証明書はCERT_B。"""
    if vendor == 'Fsas':
        https_oem = {'Fsas': {'@odata.type': '#FsasCertificates.v1_0_0.FsasCertificates',
                              'Version': 3, 'PublicKey': '2048 bit RSA', 'SelfSigned': False}}
    else:
        https_oem = {'@odata.type': '#FTSCertificates.v2_1_0.FTSCertificates',
                     'Version': 3, 'PublicKey': '2048 bit RSA'}
    return {
        CERTIFICATE0_PATH: {
            '@odata.id': CERTIFICATE0_PATH,
            '@odata.type': '#Certificate.v1_6_0.Certificate',
            'Name': 'HTTPS Certificate',
            'HttpsCertificate': {
                'SerialNumber': '53:63:5c:34',
                'SignatureAlgorithm': 'sha256WithRSAEncryption',
                'ValidNotBefore': '2026-10-18T07:57:11+00:00',
                'ValidNotAfter': '2027-10-18T07:57:11+00:00',
                'FingerPrint': CERT_A_SHA1,
                'FingerPrintHashAlgorithm': 'TPM_ALG_SHA1',
                'Issuer': {'CommonName': 'Test Root CA'},
                'Subject': {'CommonName': '192.0.2.1'},
                'Oem': https_oem,
            },
            '@odata.etag': '1792495536',
        },
        ca_path(vendor): {
            '@odata.id': ca_path(vendor),
            '@odata.type': f'#{oem_prefix_of(vendor)}Certificates.v1_0_0.{oem_prefix_of(vendor)}Certificates',
            'Name': 'Certificate Configuration',
            'CACertificate': {
                'Version': 3,
                'SerialNumber': '3e:be:0c:1b',
                'ValidFrom': '2026-10-18T07:57:11+00:00',
                'ValidTo': '2036-10-15T07:57:11+00:00',
                'SHA1FingerPrint': CERT_B_SHA1,
                'MD5FingerPrint': '83:bb:b6:44',
                'IssuedFrom': {'CommonName': 'Test Root CA'},
                'IssuedTo': {'CommonName': 'Test Root CA'},
                'EmailAddress': ['ca@example.com'],
            },
            'SSHSSLCertificate': {'SHA1FingerPrint': 'f8:5c:54:80'},
            '@odata.etag': '1792510899',
        },
    }


class FakeIrmc:
    """証明書の状態を保持し、アクションへのPOSTで状態が変わるモックiRMCクライアントです。

    get / post / wait_until_available はMockなので、呼び出し内容をアサートできます。
    """

    def __init__(self, vendor, post_status=None, available=True):
        """FakeIrmcを初期化します。

        引数:
            vendor - ベンダー名（"ts_fujitsu" または "Fsas"）
            post_status - アクションのパスごとのPOSTのステータス（省略時は204）
            available - wait_until_available() の戻り値
        """
        self.vendor = vendor
        self.oem_prefix = oem_prefix_of(vendor)
        self.state = initial_state(vendor)
        self.post_status = post_status or {}
        self.get = Mock(side_effect=self._get)
        self.post = Mock(side_effect=self._post)
        self.wait_until_available = Mock(return_value=available)

    def _get(self, path, use_cache=True):
        if path not in self.state:
            return Response(body={}, headers={}, status=404, request=Request('GET', path))
        return Response(body=copy.deepcopy(self.state[path]), headers={}, status=200, request=Request('GET', path))

    def _post(self, path, body, headers=None):
        status = self.post_status.get(path, 204)
        if status not in (200, 202, 204):
            return Response(
                body={'error': {'code': 'Fsas.1.0.ActionDataValidationFailure',
                                'message': 'TLS private key validation error'}},
                headers={},
                status=status,
                request=Request('POST', path),
            )
        fields = body.fields
        if path == replace_path(self.vendor):
            cert = fields['certificate'][1].decode()
            self.state[CERTIFICATE0_PATH]['HttpsCertificate']['FingerPrint'] = pem_sha1_fingerprint(cert)
        elif path == upload_ca_path(self.vendor):
            cert = fields['data'][1].decode()
            self.state[ca_path(self.vendor)]['CACertificate']['SHA1FingerPrint'] = pem_sha1_fingerprint(cert)
        return Response(body=None, headers={}, status=204, request=Request('POST', path))

    def posted_paths(self):
        """POSTされたパスを順番に返します。"""
        return [c.args[0] for c in self.post.call_args_list]

    def posted_fields(self, index):
        """index番目のPOSTのフォームのフィールドを返します。"""
        return self.post.call_args_list[index].args[1].fields


@pytest.fixture
def files(tmp_path):
    """証明書・秘密鍵のファイルを作り、パスを返すfixtureです。"""
    paths = {}
    for name, content in {'a.crt': CERT_A, 'b.crt': CERT_B, 'c.crt': CERT_C, 'server.key': DUMMY_KEY,
                          'not_pem.crt': 'not a certificate\n'}.items():
        path = tmp_path / name
        path.write_text(content)
        paths[name] = str(path)
    paths['missing.crt'] = str(tmp_path / 'missing.crt')
    return paths


class TestCertificateController:
    """CertificateControllerクラスのテストです。"""

    @pytest.fixture(params=VENDORS)
    def vendor(self, request):
        """ベンダー名を返すfixtureです。"""
        return request.param

    @pytest.fixture
    def irmc(self, vendor):
        """初期状態のFakeIrmcを返すfixtureです。"""
        return FakeIrmc(vendor)

    @pytest.fixture
    def mock_logger(self):
        """モックLoggerを返すfixtureです。"""
        return Mock()

    @pytest.fixture
    def controller(self, irmc, mock_logger):
        """CertificateControllerインスタンスを返すfixtureです。"""
        return CertificateController(irmc, mock_logger)

    # ---- get ----

    def test_get_state(self, controller, irmc):
        """get_state: Oemと@odataのキーを除いた証明書の情報を返すことのテストです。"""
        result = controller.get_state()

        assert result.changed is False
        certificates = result.extra_fields['certificates']
        assert set(certificates) == {'HttpsCertificate', 'CACertificate'}
        assert certificates['HttpsCertificate']['FingerPrint'] == CERT_A_SHA1
        assert 'Oem' not in certificates['HttpsCertificate']
        assert certificates['CACertificate']['SHA1FingerPrint'] == CERT_B_SHA1
        assert certificates['CACertificate']['EmailAddress'] == ['ca@example.com']
        assert not any(key.startswith('@odata') for value in certificates.values() for key in value)
        irmc.post.assert_not_called()

    def test_get_state_http_error(self, controller, irmc, vendor):
        """get_state: GETが失敗した場合のテストです。"""
        del irmc.state[ca_path(vendor)]

        with pytest.raises(HttpError) as exc_info:
            controller.get_state()

        assert exc_info.value.status == 404
        assert f'Failed to GET {ca_path(vendor)}' in exc_info.value.message

    def test_get_state_missing_field(self, controller, irmc):
        """get_state: HttpsCertificateが無い場合のテストです。"""
        del irmc.state[CERTIFICATE0_PATH]['HttpsCertificate']

        with pytest.raises(ModuleError) as exc_info:
            controller.get_state()

        assert "'HttpsCertificate' field not found" in exc_info.value.message

    def test_get_state_vendor_unknown(self, controller, irmc):
        """get_state: ベンダーを判別できない場合のテストです。"""
        irmc.vendor = None

        with pytest.raises(ModuleError) as exc_info:
            controller.get_state()

        assert 'vendor' in exc_info.value.message

    # ---- set: 変更なし ----

    def test_set_state_no_parameter(self, controller, irmc):
        """set_state: 証明書が1つも指定されていない場合は、何もせずchanged=Falseになることのテストです。"""
        result = controller.set_state({'private_key_path': None, 'ssl_cert_path': '', 'ssl_ca_cert_path': None})

        assert result.changed is False
        assert 'No certificate to set' in result.msg
        assert result.extra_fields['certificates']['HttpsCertificate']['FingerPrint'] == CERT_A_SHA1
        irmc.post.assert_not_called()

    def test_set_state_already_registered(self, controller, irmc, files):
        """set_state: フィンガープリントが同じなら登録しないことのテストです。"""
        result = controller.set_state({
            'private_key_path': files['server.key'],
            'ssl_cert_path': files['a.crt'],
            'ssl_ca_cert_path': files['b.crt'],
        })

        assert result.changed is False
        assert 'already registered' in result.msg
        irmc.post.assert_not_called()
        irmc.wait_until_available.assert_not_called()

    # ---- set: 変更あり ----

    def test_set_state_tls_only(self, controller, irmc, vendor, files):
        """set_state: TLS証明書だけ違う場合、ReplaceCertificateに証明書と秘密鍵を送ることのテストです。"""
        result = controller.set_state({
            'private_key_path': files['server.key'],
            'ssl_cert_path': files['c.crt'],
            'ssl_ca_cert_path': files['b.crt'],  # 登録済みと同じ
        })

        assert result.changed is True
        assert irmc.posted_paths() == [replace_path(vendor)]
        fields = irmc.posted_fields(0)
        assert set(fields) == {'certificate', 'private_key'}
        assert fields['certificate'] == ('c.crt', CERT_C.encode(), 'application/x-pem-file')
        assert fields['private_key'] == ('server.key', DUMMY_KEY.encode(), 'application/x-pem-file')
        irmc.wait_until_available.assert_not_called()
        assert result.extra_fields['certificates']['HttpsCertificate']['FingerPrint'] == CERT_C_SHA1

    def test_set_state_ca_only(self, controller, irmc, vendor, files):
        """set_state: CA証明書だけ指定した場合、UploadCACertificateに送り、iRMCの応答を待つことのテストです。"""
        result = controller.set_state({'ssl_ca_cert_path': files['c.crt']})

        assert result.changed is True
        assert irmc.posted_paths() == [upload_ca_path(vendor)]
        assert irmc.posted_fields(0) == {'data': ('c.crt', CERT_C.encode(), 'application/x-pem-file')}
        irmc.wait_until_available.assert_called_once_with(initial_delay=10, interval=5, timeout=60)
        assert result.extra_fields['certificates']['CACertificate']['SHA1FingerPrint'] == CERT_C_SHA1

    def test_set_state_both(self, controller, irmc, vendor, files):
        """set_state: 両方違う場合、TLS証明書 -> CA証明書の順に登録することのテストです。"""
        result = controller.set_state({
            'private_key_path': files['server.key'],
            'ssl_cert_path': files['c.crt'],
            'ssl_ca_cert_path': files['a.crt'],
        })

        assert result.changed is True
        assert irmc.posted_paths() == [replace_path(vendor), upload_ca_path(vendor)]
        certificates = result.extra_fields['certificates']
        assert certificates['HttpsCertificate']['FingerPrint'] == CERT_C_SHA1
        assert certificates['CACertificate']['SHA1FingerPrint'] == CERT_A_SHA1

    def test_set_state_fingerprint_case_insensitive(self, controller, irmc, vendor, files):
        """set_state: iRMCのフィンガープリントが大文字でも、同じ証明書なら登録しないことのテストです。"""
        irmc.state[CERTIFICATE0_PATH]['HttpsCertificate']['FingerPrint'] = CERT_A_SHA1.upper()

        result = controller.set_state({'private_key_path': files['server.key'], 'ssl_cert_path': files['a.crt']})

        assert result.changed is False
        irmc.post.assert_not_called()

    # ---- set: エラー ----

    @pytest.mark.parametrize('params', [
        {'private_key_path': 'server.key'},
        {'ssl_cert_path': 'a.crt'},
        {'ssl_cert_path': 'a.crt', 'private_key_path': ''},
    ], ids=['key_only', 'cert_only', 'empty_key'])
    def test_set_state_key_pair_required(self, controller, irmc, params):
        """set_state: 秘密鍵と証明書の片方だけの場合はValidationErrorになることのテストです。"""
        with pytest.raises(ValidationError) as exc_info:
            controller.set_state(params)

        assert "Both 'private_key_path' and 'ssl_cert_path' are required" in exc_info.value.message
        irmc.get.assert_not_called()

    def test_set_state_file_not_found(self, controller, irmc, files):
        """set_state: ファイルを読み込めない場合のテストです。"""
        with pytest.raises(ModuleError) as exc_info:
            controller.set_state({'ssl_ca_cert_path': files['missing.crt']})

        assert f"Could not read key/certificate file at '{files['missing.crt']}'" in exc_info.value.message
        irmc.post.assert_not_called()

    def test_set_state_not_pem(self, controller, irmc, files):
        """set_state: PEM形式の証明書でない場合はValidationErrorになることのテストです。"""
        with pytest.raises(ValidationError) as exc_info:
            controller.set_state({'ssl_ca_cert_path': files['not_pem.crt']})

        assert f"'{files['not_pem.crt']}' is not a PEM certificate" in exc_info.value.message
        irmc.post.assert_not_called()

    def test_set_state_post_failure(self, controller, irmc, vendor, files):
        """set_state: 鍵ペアの不一致などでPOSTが失敗した場合のテストです。"""
        irmc.post_status[replace_path(vendor)] = 400

        with pytest.raises(HttpError) as exc_info:
            controller.set_state({'private_key_path': files['server.key'], 'ssl_cert_path': files['c.crt']})

        assert exc_info.value.status == 400
        assert f'Failed to POST {replace_path(vendor)}' in exc_info.value.message
        assert 'TLS private key validation error' in exc_info.value.message
        assert 'already changed' not in exc_info.value.message

    def test_set_state_partial_failure(self, controller, irmc, vendor, files):
        """set_state: CA証明書の登録が失敗した場合、変更済みのTLS証明書がメッセージに含まれることのテストです。"""
        irmc.post_status[upload_ca_path(vendor)] = 400

        with pytest.raises(HttpError) as exc_info:
            controller.set_state({
                'private_key_path': files['server.key'],
                'ssl_cert_path': files['c.crt'],
                'ssl_ca_cert_path': files['a.crt'],
            })

        assert f'Failed to POST {upload_ca_path(vendor)}' in exc_info.value.message
        assert f'already changed: {replace_path(vendor)}' in exc_info.value.message

    def test_set_state_not_available_after_ca_upload(self, controller, irmc, vendor, files):
        """set_state: CA証明書の登録後にiRMCが応答しない場合のテストです。"""
        irmc.wait_until_available.return_value = False

        with pytest.raises(ModuleError) as exc_info:
            controller.set_state({'ssl_ca_cert_path': files['c.crt']})

        assert 'did not respond within 70 seconds' in exc_info.value.message
        assert f'already changed: {upload_ca_path(vendor)}' in exc_info.value.message

    def test_set_state_vendor_unknown(self, controller, irmc, files):
        """set_state: ベンダーを判別できない場合のテストです。"""
        irmc.vendor = None
        irmc.oem_prefix = None

        with pytest.raises(ModuleError) as exc_info:
            controller.set_state({'ssl_ca_cert_path': files['c.crt']})

        assert 'vendor' in exc_info.value.message
        irmc.post.assert_not_called()


class TestModuleIntegration:
    """モジュール全体の統合テストです。"""

    @pytest.fixture
    def mock_module(self):
        """モックAnsibleModuleを返すfixtureです。"""
        module = Mock()
        module.check_mode = False
        module.params = {
            'irmc_url': '192.0.2.1',
            'irmc_username': 'admin',
            'irmc_password': 'password',
            'validate_certs': False,
            'command': 'get',
            'private_key_path': None,
            'ssl_cert_path': None,
            'ssl_ca_cert_path': None,
        }
        module._verbosity = 0
        return module

    @pytest.fixture
    def mock_logger(self):
        """to_logs_dict()が空辞書を返すモックLoggerを返すfixtureです。"""
        logger = Mock()
        logger.to_logs_dict.return_value = {}
        return logger

    @patch('ansible_collections.fsas.primergy.plugins.modules.irmc_certificate.iRMC')
    @patch('ansible_collections.fsas.primergy.plugins.modules.irmc_certificate.AnsibleLogger')
    def test_get_command_success(self, mock_logger_class, mock_irmc_class, mock_module, mock_logger):
        """get command: 正常系の統合テストです。"""
        from ansible_collections.fsas.primergy.plugins.modules.irmc_certificate import irmc_certificate

        mock_logger_class.return_value = mock_logger
        mock_irmc_class.return_value = FakeIrmc('Fsas')

        irmc_certificate(mock_module)

        mock_module.exit_json.assert_called_once()
        call_kwargs = mock_module.exit_json.call_args[1]
        assert call_kwargs['changed'] is False
        assert call_kwargs['certificates']['HttpsCertificate']['FingerPrint'] == CERT_A_SHA1
        mock_module.fail_json.assert_not_called()

    @patch('ansible_collections.fsas.primergy.plugins.modules.irmc_certificate.iRMC')
    @patch('ansible_collections.fsas.primergy.plugins.modules.irmc_certificate.AnsibleLogger')
    def test_set_command_success(self, mock_logger_class, mock_irmc_class, mock_module, mock_logger, files):
        """set command: 正常系の統合テストです。"""
        from ansible_collections.fsas.primergy.plugins.modules.irmc_certificate import irmc_certificate

        mock_module.params.update({
            'command': 'set',
            'private_key_path': files['server.key'],
            'ssl_cert_path': files['c.crt'],
        })
        mock_logger_class.return_value = mock_logger
        mock_irmc_class.return_value = FakeIrmc('Fsas')

        irmc_certificate(mock_module)

        mock_module.exit_json.assert_called_once()
        call_kwargs = mock_module.exit_json.call_args[1]
        assert call_kwargs['changed'] is True
        assert call_kwargs['certificates']['HttpsCertificate']['FingerPrint'] == CERT_C_SHA1
        mock_module.fail_json.assert_not_called()

    @patch('ansible_collections.fsas.primergy.plugins.modules.irmc_certificate.iRMC')
    @patch('ansible_collections.fsas.primergy.plugins.modules.irmc_certificate.AnsibleLogger')
    def test_validation_error_handling(self, mock_logger_class, mock_irmc_class, mock_module, mock_logger):
        """ValidationErrorがfail_jsonになることのテストです。"""
        from ansible_collections.fsas.primergy.plugins.modules.irmc_certificate import irmc_certificate

        mock_module.params.update({'command': 'set', 'ssl_cert_path': 'a.crt'})
        mock_logger_class.return_value = mock_logger
        mock_irmc_class.return_value = FakeIrmc('Fsas')

        irmc_certificate(mock_module)

        mock_module.fail_json.assert_called_once()
        assert "Both 'private_key_path' and 'ssl_cert_path'" in mock_module.fail_json.call_args[1]['msg']
        mock_module.exit_json.assert_not_called()

    @patch('ansible_collections.fsas.primergy.plugins.modules.irmc_certificate.iRMC')
    @patch('ansible_collections.fsas.primergy.plugins.modules.irmc_certificate.AnsibleLogger')
    def test_http_error_handling(self, mock_logger_class, mock_irmc_class, mock_module, mock_logger, files):
        """HTTPエラーハンドリングのテストです。"""
        from ansible_collections.fsas.primergy.plugins.modules.irmc_certificate import irmc_certificate

        mock_module.params.update({
            'command': 'set',
            'private_key_path': files['server.key'],
            'ssl_cert_path': files['c.crt'],
        })
        mock_logger_class.return_value = mock_logger
        mock_irmc_class.return_value = FakeIrmc('Fsas', post_status={replace_path('Fsas'): 400})

        irmc_certificate(mock_module)

        mock_module.fail_json.assert_called_once()
        call_kwargs = mock_module.fail_json.call_args[1]
        assert call_kwargs['status'] == 400
        assert 'TLS private key validation error' in call_kwargs['msg']
        mock_module.exit_json.assert_not_called()

    @patch('ansible_collections.fsas.primergy.plugins.modules.irmc_certificate.iRMC')
    @patch('ansible_collections.fsas.primergy.plugins.modules.irmc_certificate.AnsibleLogger')
    def test_unexpected_error_handling(self, mock_logger_class, mock_irmc_class, mock_module, mock_logger):
        """予期しない例外（接続エラー等）のハンドリングのテストです。"""
        from ansible_collections.fsas.primergy.plugins.modules.irmc_certificate import irmc_certificate

        mock_logger_class.return_value = mock_logger
        irmc = FakeIrmc('Fsas')
        irmc.get.side_effect = ConnectionError('connection refused')
        mock_irmc_class.return_value = irmc

        irmc_certificate(mock_module)

        mock_module.fail_json.assert_called_once()
        call_kwargs = mock_module.fail_json.call_args[1]
        assert 'Unexpected error: connection refused' in call_kwargs['msg']
        assert 'exception' in call_kwargs

    @patch('ansible_collections.fsas.primergy.plugins.modules.irmc_certificate.iRMC')
    @patch('ansible_collections.fsas.primergy.plugins.modules.irmc_certificate.AnsibleLogger')
    def test_check_mode(self, mock_logger_class, mock_irmc_class, mock_module):
        """check_mode時はiRMCにアクセスせずに終了することのテストです。"""
        from ansible_collections.fsas.primergy.plugins.modules.irmc_certificate import irmc_certificate

        mock_module.check_mode = True
        # 実際のexit_json()と同様に処理を終了させる
        mock_module.exit_json.side_effect = SystemExit

        with pytest.raises(SystemExit):
            irmc_certificate(mock_module)

        mock_module.exit_json.assert_called_once_with(changed=False, msg='module was not run')
        mock_irmc_class.assert_not_called()
