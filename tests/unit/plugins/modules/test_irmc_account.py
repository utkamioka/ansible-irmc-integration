#!/usr/bin/python

# Copyright 2018-2026 Fsas Technologies Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""irmc_accountモジュールのユニットテストです。"""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import copy
from unittest.mock import Mock, patch

import pytest

from ansible_collections.fsas.primergy.plugins.module_utils.errors import HttpError, ModuleError, ValidationError
from ansible_collections.fsas.primergy.plugins.module_utils.helpers import pem_sha1_fingerprint
from ansible_collections.fsas.primergy.plugins.module_utils.irmc_client import Request, Response
from ansible_collections.fsas.primergy.plugins.modules.irmc_account import (
    AccountController,
    diff,
    project,
    ssh_public_key_irmc_fingerprints,
    ssh_public_key_md5_fingerprint,
)

# vendorごとのテスト（ts_fujitsu: M7以前、Fsas: M8以降）
VENDORS = [
    pytest.param('ts_fujitsu', id='ts_fujitsu'),
    pytest.param('Fsas', id='Fsas'),
]

ACCOUNTS_PATH = '/redfish/v1/AccountService/Accounts'

# テスト用のSSH公開鍵。フィンガープリントは 'ssh-keygen -l -E md5' で計算した値
SSH_KEY = 'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIO03As2+JIXuU87pUAGIEBEJpM/DLxnO65eFY0TTGgIA test-user\n'
SSH_KEY_MD5 = '96:eb:31:dd:44:e0:41:96:60:12:0e:28:ac:29:c6:0c'
# M8以降の世代が返すフィンガープリント（鍵のデータの SHA-256 の先頭16バイト）。'ssh-keygen -l -E sha256' は base64 表示なので、
# 鍵のデータを base64 デコードして SHA-256 を計算した値
SSH_KEY_SHA256_16 = '7e:9b:4a:c7:83:93:c7:d3:ce:75:c1:96:51:9c:9a:0b'

# テスト用の自己署名証明書（test_irmc_certificate.py の CERT_A と同じ）
CERT = """-----BEGIN CERTIFICATE-----
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
CERT_SHA1 = 'd4:55:7c:dc:e0:f7:43:b4:c2:8a:f1:2b:8a:a5:67:4c:9d:b1:5a:05'


def oem_prefix_of(vendor):
    """ベンダーに対応するOEMアクション名の接頭辞を返します。"""
    return 'FTS' if vendor == 'ts_fujitsu' else 'Fsas'


def account_body(vendor, account_id, user_name):
    """Accountリソース（実機ログを元にしたもの）を返します。"""
    path = f'{ACCOUNTS_PATH}/{account_id}'
    prefix = oem_prefix_of(vendor)
    return {
        '@odata.id': path,
        '@odata.type': '#ManagerAccount.v1_9_0.ManagerAccount',
        'Id': account_id,
        'Name': 'User Account',
        'Description': 'my description',
        'Enabled': True,
        'Password': None,
        'PasswordChangeRequired': False,
        'UserName': user_name,
        'RoleId': 'Administrator',
        'Locked': False,
        'HostBootstrapAccount': False,
        'Links': {'Oem': {}, 'Role': {'@odata.id': '/redfish/v1/AccountService/Roles/Administrator'}},
        'Actions': {'Oem': {
            f'#{prefix}User.{action}': {'target': f'{path}/Actions/Oem/{prefix}User.{action}'}
            for action in ('AddUserSSHKey', 'AddUserMIMECert', 'RemoveUserSSHKey', 'RemoveUserMIMECert')
        }},
        'Oem': {vendor: {
            '@odata.type': f'#{prefix}User.v1_0_0.{prefix}User',
            'BaseValues': {'Enabled': True, 'Shell': 'RemoteManager'},
            'Permissions': {
                'Standard': {'Lan': 'Oem', 'Serial': 'Administrator'},
                'Extended': {'ConfigureUsers': True, 'ConfigureIrmc': True,
                             'UseVideoRedirection': True, 'UseRemoteStorage': True},
            },
            '2FAuth': {'Enabled': False, 'Configured': False},
            'Email': {
                'AlertFilter': {'Fans': 'Warning', 'Temperature': 'Warning', 'Hardware': 'All',
                                'SystemHang': 'Critical', 'Post': 'All', 'Security': 'Warning',
                                'SystemStatus': 'None', 'Harddisk': 'Critical', 'NetworkError': 'Warning',
                                'RemoteManagement': 'Critical', 'PowerSupply': 'Warning', 'Spare': 'None',
                                'Memory': 'Critical', 'Others': 'None'},
                'AlertChassisEventsUser': False,
                'PagingEnabled': True,
                'Layout': 'Standard',
                'Address': 'User02@domain.com',
                'PreferredMailServer': 'Auto',
                'SendEncryptedAlerts': False,
                'ExtraSubjectEnabled': False,
                'ExtraSubject': '""',
                'AttachSystemReport': False,
            },
            'SnmpV3': {
                'ServiceEnabled': True,
                'AuthPrivType': 'SHA256_AES',
                'AuthPrivType@Redfish.AllowableValues': ['SHA256_AES', 'SHA384_AES', 'SHA512_AES',
                                                         'SHA256_DES', 'SHA384_DES', 'SHA512_DES'],
                'AccessType': 'ReadOnly',
            },
            'SMIMECertificate': None,
            'SSHv2KeyFingerprint': None,
            'SNMPPasswordRequirement': True,
        }},
        '@Redfish.Copyright': 'Copyright 2014-2020 DMTF.',
        '@odata.etag': '1789984464',
    }


def merge(target, source):
    """sourceをtargetに再帰的にマージします（PATCHの再現）。"""
    for key, value in source.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            merge(target[key], value)
        else:
            target[key] = value


def error_response(method, path, status, message):
    """iRMCのエラーレスポンスを返します。"""
    body = {'error': {'@Message.ExtendedInfo': [{'Message': message}], 'code': 'Fsas.1.0.Error', 'message': message}}
    return Response(body=body, headers={}, status=status, request=Request(method, path))


class FakeIrmc:
    """アカウントの状態を保持し、POST / PATCH / DELETE で状態が変わるモックiRMCクライアントです。

    実機で確認したiRMCの動きを再現します。
    - 現在と同じパスワードを送ると500になり、一緒に送った項目も反映されない
    - SNMPv3が無効なユーザーのAuthPrivTypeを変えようとすると409になる
    - SNMPv3を無効にするとAuthPrivTypeはSHA256_AESに戻る
    get / post / patch / delete はMockなので、呼び出し内容をアサートできます。
    """

    def __init__(self, vendor, status=None):
        """FakeIrmcを初期化します。

        引数:
            vendor - ベンダー名（"ts_fujitsu" または "Fsas"）
            status - (メソッド, パス) ごとに返すステータス（省略時は成功）
        """
        self.vendor = vendor
        # 現在と同じパスワードを送ったときの応答（M7以前の世代は500、M8以降の世代は400）
        self.same_password_error = (500, 'Accessing property Password failed because of backend error.')
        self.oem_prefix = oem_prefix_of(vendor)
        self.status = status or {}
        self.accounts = {
            f'{ACCOUNTS_PATH}/2': account_body(vendor, '2', 'admin'),
            f'{ACCOUNTS_PATH}/3': account_body(vendor, '3', 'ansibleuser'),
        }
        self.passwords = {'admin': 'admin-password', 'ansibleuser': 'old-password'}
        # 送ったリクエストの順番（メソッド, パス）
        self.requests = []
        self.get = Mock(side_effect=self._get)
        self.post = Mock(side_effect=self._post)
        self.patch = Mock(side_effect=self._patch)
        self.delete = Mock(side_effect=self._delete)

    def _get(self, path, use_cache=True):
        self.requests.append(('GET', path))
        if path == '/redfish/v1':
            body = {'AccountService': {'@odata.id': '/redfish/v1/AccountService'}}
        elif path == '/redfish/v1/AccountService':
            body = {'Accounts': {'@odata.id': ACCOUNTS_PATH}}
        elif path == ACCOUNTS_PATH:
            body = {'Members': [{'@odata.id': p} for p in self.accounts]}
        elif path in self.accounts:
            body = copy.deepcopy(self.accounts[path])
        else:
            return Response(body={}, headers={}, status=404, request=Request('GET', path))
        return Response(body=body, headers={}, status=200, request=Request('GET', path))

    def _post(self, path, body, headers=None):
        self.requests.append(('POST', path))
        status = self.status.get(('POST', path))
        if status:
            return error_response('POST', path, *self._error_of(status, 'POST failed'))
        if path == ACCOUNTS_PATH:
            account_id = str(max(int(p.rsplit('/', 1)[1]) for p in self.accounts) + 1)
            new_path = f'{ACCOUNTS_PATH}/{account_id}'
            account = account_body(self.vendor, account_id, body['UserName'])
            # 実機で作成したユーザーの初期値
            account.update({'Description': '', 'RoleId': 'ReadOnly', 'Enabled': False})
            account['Oem'][self.vendor]['Email'].update({'PagingEnabled': True, 'AlertChassisEventsUser': False})
            account.update({key: body[key] for key in ('RoleId', 'Description', 'Enabled') if key in body})
            self.accounts[new_path] = account
            self.passwords[body['UserName']] = body['Password']
            return Response(body=copy.deepcopy(account), headers={'Location': new_path}, status=201,
                            request=Request('POST', path))

        oem = None
        for account in self.accounts.values():
            if path.startswith(account['@odata.id'] + '/Actions/'):
                oem = account['Oem'][self.vendor]
        content = body.fields['data'][1].decode()
        if path.endswith('User.AddUserSSHKey'):
            oem['SSHv2KeyFingerprint'] = f'RSA 256 {ssh_public_key_md5_fingerprint(content)}:'
        elif path.endswith('User.AddUserMIMECert'):
            oem['SMIMECertificate'] = {'SHA1FingerPrint': pem_sha1_fingerprint(content), '@odata.id': 'x'}
        return Response(body=None, headers={}, status=204, request=Request('POST', path))

    def _patch(self, path, body, headers=None):
        self.requests.append(('PATCH', path))
        status = self.status.get(('PATCH', path))
        if status:
            return error_response('PATCH', path, *self._error_of(status, 'PATCH failed'))
        account = self.accounts[path]
        user_name = account['UserName']
        if 'Password' in body and body['Password'] == self.passwords[user_name]:
            return error_response('PATCH', path, *self.same_password_error)

        snmpv3 = account['Oem'][self.vendor]['SnmpV3']
        requested = (body.get('Oem') or {}).get(self.vendor, {}).get('SnmpV3', {})
        enabled = requested.get('ServiceEnabled', snmpv3['ServiceEnabled'])
        if 'AuthPrivType' in requested and not enabled:
            return error_response('PATCH', path, 409,
                                  'The requirements related to the AuthPrivType are not fulfilled at the moment.')

        changes = copy.deepcopy(body)
        if 'Password' in changes:
            self.passwords[user_name] = changes.pop('Password')
        merge(account, changes)
        if not snmpv3['ServiceEnabled']:
            snmpv3['AuthPrivType'] = 'SHA256_AES'
        return Response(body=copy.deepcopy(account), headers={}, status=200, request=Request('PATCH', path))

    @staticmethod
    def _error_of(status, default_message):
        """statusの指定（ステータス、または (ステータス, メッセージ)）から (ステータス, メッセージ) を返します。"""
        return status if isinstance(status, tuple) else (status, default_message)

    def _delete(self, path, headers=None):
        status = self.status.get(('DELETE', path))
        if status:
            return error_response('DELETE', path, status, 'DELETE failed')
        del self.accounts[path]
        return Response(body=None, headers={}, status=204, request=Request('DELETE', path))

    def login(self, username, password):
        """そのユーザー名とパスワードでログインするモックiRMCクライアントを返します。"""
        client = Mock()
        ok = self.passwords.get(username) == password
        client.get.return_value = Response(body={}, headers={}, status=200 if ok else 401,
                                           request=Request('GET', 'x'))
        return client

    def oem(self, path):
        """アカウントの Oem.{vendor} を返します。"""
        return self.accounts[path]['Oem'][self.vendor]

    def patched_bodies(self):
        """PATCHのボディを順番に返します。"""
        return [c.args[1] for c in self.patch.call_args_list]


@pytest.fixture
def files(tmp_path):
    """公開鍵・証明書のファイルを作り、パスを返すfixtureです。"""
    paths = {}
    for name, content in {'id.pub': SSH_KEY, 'smime.pem': CERT, 'broken.pub': 'not-a-key\n',
                          'broken.pem': 'not a certificate\n'}.items():
        path = tmp_path / name
        path.write_text(content)
        paths[name] = str(path)
    paths['missing'] = str(tmp_path / 'missing')
    return paths


class TestFunctions:
    """モジュールの関数のテストです。"""

    def test_ssh_public_key_md5_fingerprint(self):
        """ssh-keygen -l -E md5 と同じ値になることのテストです。"""
        assert ssh_public_key_md5_fingerprint(SSH_KEY) == SSH_KEY_MD5

    def test_ssh_public_key_irmc_fingerprints(self):
        """M7以前の世代（MD5）と M8以降の世代（SHA-256の先頭16バイト）の両方を返すことのテストです。"""
        assert ssh_public_key_irmc_fingerprints(SSH_KEY) == (SSH_KEY_MD5, SSH_KEY_SHA256_16)

    @pytest.mark.parametrize('key', ['', 'ssh-rsa', 'ssh-rsa not*base64'])
    def test_ssh_public_key_md5_fingerprint_invalid(self, key):
        """公開鍵の形式が正しくない場合はValueErrorになることのテストです。"""
        with pytest.raises(ValueError):
            ssh_public_key_md5_fingerprint(key)

    def test_project(self):
        """argument_specにある項目だけを取り出すことのテストです。"""
        options = {'A': {'type': 'str'}, 'B': {'type': 'dict', 'options': {'C': {'type': 'bool'}}}}
        data = {'A': 'a', 'X': 'x', 'B': {'C': True, 'Y': 'y'}}
        assert project(data, options) == {'A': 'a', 'B': {'C': True}}
        assert project({'A': 'a'}, options) == {'A': 'a'}
        assert project(None, options) == {}

    def test_diff(self):
        """指定された値のうち、異なるものだけを返すことのテストです。Noneは未指定として扱います。"""
        desired = {'A': 'a', 'B': None, 'C': {'D': 1, 'E': 2}, 'F': {'G': None}}
        current = {'A': 'a', 'B': 'b', 'C': {'D': 1, 'E': 3}}
        assert diff(desired, current) == {'C': {'E': 2}}
        assert diff({'A': {'B': 1}}, None) == {'A': {'B': 1}}


class TestAccountController:
    """AccountControllerクラスのテストです。"""

    @pytest.fixture(params=VENDORS)
    def vendor(self, request):
        """ベンダー名を返すfixtureです。"""
        return request.param

    @pytest.fixture
    def irmc(self, vendor):
        """初期状態のFakeIrmcを返すfixtureです。"""
        return FakeIrmc(vendor)

    @pytest.fixture
    def controller(self, irmc):
        """AccountControllerインスタンスを返すfixtureです。"""
        return AccountController(irmc, Mock(), irmc.login)

    @staticmethod
    def params(**kwargs):
        """set_stateに渡すパラメータを返します。"""
        params = {'name': 'ansibleuser', 'password': None, 'account': None,
                  'ssh_public_key_path': None, 'smime_certificate_path': None}
        params.update(kwargs)
        return params

    # ---- get ----

    def test_get_state(self, controller):
        """get_state: Oemの中身を1段上に出したaccountと、読み取り専用のaccount_infoを返すことのテストです。"""
        result = controller.get_state({'name': 'ansibleuser'})

        assert result.changed is False
        account = result.extra_fields['account']
        assert account['RoleId'] == 'Administrator'
        assert account['BaseValues'] == {'Enabled': True, 'Shell': 'RemoteManager'}
        assert account['SnmpV3'] == {'ServiceEnabled': True, 'AuthPrivType': 'SHA256_AES'}
        assert account['TwoFactorAuth'] == {'Enabled': False}
        assert account['Email']['AlertFilter']['Spare'] == 'None'
        for key in ('Oem', 'UserName', 'Id', 'Password', 'Links', 'Actions', '@odata.etag', '2FAuth'):
            assert key not in account
        assert result.extra_fields['account_info'] == {
            'Id': '3',
            'UserName': 'ansibleuser',
            'Locked': False,
            'SNMPPasswordRequirement': True,
            'SSHv2KeyFingerprint': None,
            'SMIMECertificate': None,
            'SnmpV3': {'AccessType': 'ReadOnly'},
            'TwoFactorAuth': {'Configured': False},
        }

    def test_get_state_not_found(self, controller):
        """get_state: ユーザーがいなければModuleErrorになることのテストです。"""
        with pytest.raises(ModuleError, match="User 'nobody' not found"):
            controller.get_state({'name': 'nobody'})

    def test_get_state_vendor_unknown(self, controller, irmc):
        """get_state: iRMCのベンダーを判別できない場合はModuleErrorになることのテストです。"""
        irmc.vendor = None
        with pytest.raises(ModuleError, match='Failed to detect iRMC vendor'):
            controller.get_state({'name': 'ansibleuser'})

    # ---- set ----

    def test_set_state_nothing_given(self, controller, irmc):
        """set_state: 何も指定しなければ、何も送らずに変更なしになることのテストです。"""
        result = controller.set_state(self.params())

        assert result.changed is False
        irmc.patch.assert_not_called()
        irmc.post.assert_not_called()

    def test_set_state_already_same(self, controller, irmc):
        """set_state: 指定された値が現在と同じなら変更なしになることのテストです。"""
        result = controller.set_state(self.params(account={
            'RoleId': 'Administrator', 'Description': None,
            'Permissions': {'Standard': {'Lan': 'Oem', 'Serial': None}, 'Extended': None},
        }))

        assert result.changed is False
        irmc.patch.assert_not_called()

    def test_set_state_change(self, controller, irmc, vendor):
        """set_state: 異なる項目だけを1回のPATCHで送ることのテストです（OemはOem.{vendor}の中に入れる）。"""
        result = controller.set_state(self.params(account={
            'Description': 'new', 'RoleId': 'Administrator',
            'Email': {'AlertChassisEventsUser': True, 'Layout': 'Standard', 'AlertFilter': {'Spare': 'All'}},
            'TwoFactorAuth': {'Enabled': True},
        }))

        assert result.changed is True
        assert irmc.patched_bodies() == [{
            'Description': 'new',
            'Oem': {vendor: {
                'Email': {'AlertChassisEventsUser': True, 'AlertFilter': {'Spare': 'All'}},
                '2FAuth': {'Enabled': True},
            }},
        }]
        # ETagをIf-Matchに付ける
        assert irmc.patch.call_args.kwargs['headers'] == {'If-Match': '1789984464'}
        assert result.extra_fields['account']['Description'] == 'new'
        assert result.extra_fields['account']['TwoFactorAuth'] == {'Enabled': True}

    def test_set_state_copy(self, controller, irmc):
        """set_state: getのaccountをそのまま別のユーザーに渡すと、同じ設定になることのテストです。"""
        irmc.oem(f'{ACCOUNTS_PATH}/2')['Email']['Address'] = 'admin@example.com'
        source = controller.get_state({'name': 'admin'}).extra_fields['account']

        result = controller.set_state(self.params(name='copied', password='new-password', account=source))

        assert result.changed is True
        assert result.extra_fields['account'] == source
        assert result.extra_fields['account_info']['UserName'] == 'copied'

        # 2回目は変更なし（同じパスワードはログインで確かめる）
        again = controller.set_state(self.params(name='copied', password='new-password', account=source))
        assert again.changed is False

    def test_set_state_create(self, controller, irmc, vendor):
        """set_state: ユーザーがいなければ、POSTで作成してから残りをPATCHすることのテストです。"""
        result = controller.set_state(self.params(name='newuser', password='secret', account={
            'RoleId': 'Operator', 'Enabled': True, 'Description': 'desc', 'BaseValues': {'Shell': 'None'},
        }))

        assert result.changed is True
        irmc.post.assert_called_once_with(ACCOUNTS_PATH, {
            'UserName': 'newuser', 'Password': 'secret', 'RoleId': 'Operator', 'Description': 'desc',
            'Enabled': True,
        })
        # パスワードはPOSTで送ったので、PATCHでは送らない
        assert irmc.patched_bodies() == [{'Oem': {vendor: {'BaseValues': {'Shell': 'None'}}}}]
        assert result.extra_fields['account_info']['UserName'] == 'newuser'
        assert 'user created' in result.msg

    def test_set_state_create_without_password(self, controller, irmc):
        """set_state: パスワード無しではユーザーを作成できないことのテストです。"""
        with pytest.raises(ValidationError, match="'password' is required"):
            controller.set_state(self.params(name='newuser', account={'RoleId': 'Operator'}))
        irmc.post.assert_not_called()

    def test_set_state_error_hides_password(self, controller, irmc):
        """set_state: iRMCのエラーメッセージにパスワードが含まれていても、伏せてから使うことのテストです。

        警告（module.warn）はAnsibleのno_logで伏せられないため、モジュールで伏せる必要があります。
        """
        password = 'Too-Long-Test-Value-0123456789'
        irmc.status[('POST', ACCOUNTS_PATH)] = (
            400, f'The value {password} for the property Password exceeds allowed range or size')

        with pytest.raises(HttpError) as e:
            controller.set_state(self.params(name='newuser', password=password))

        assert password not in e.value.message
        assert 'The value ******** for the property Password' in e.value.message
        warned = ' '.join(str(c.args[0]) for c in controller.logger.warn.call_args_list)
        assert password not in warned

    def test_set_state_create_failure(self, controller, irmc):
        """set_state: 作成に失敗した場合はHttpErrorになることのテストです。"""
        irmc.status[('POST', ACCOUNTS_PATH)] = 400
        with pytest.raises(HttpError) as e:
            controller.set_state(self.params(name='newuser', password='secret'))
        assert e.value.status == 400

    def test_set_state_password_changed(self, controller, irmc):
        """set_state: パスワードは他の項目の後に単独で送ることのテストです。"""
        result = controller.set_state(self.params(password='new-password', account={'Description': 'new'}))

        assert result.changed is True
        assert irmc.patched_bodies() == [{'Description': 'new'}, {'Password': 'new-password'}]
        assert irmc.passwords['ansibleuser'] == 'new-password'
        # パスワードを変えた後はiRMCにアクセスしない（自分自身のパスワードを変えた場合に備える）
        assert irmc.requests[-1] == ('PATCH', f'{ACCOUNTS_PATH}/3')
        assert 'password' in result.msg

    @pytest.mark.parametrize('error', [
        pytest.param((500, 'Accessing property Password failed because of backend error.'), id='M7_or_earlier'),
        pytest.param((400, 'The same password is already in use.'), id='M8_or_later'),
    ])
    def test_set_state_password_same(self, controller, irmc, error):
        """set_state: 同じパスワード（M7以前は500、M8以降は400）でも、ログインできれば変更なしになることのテストです。"""
        irmc.same_password_error = error
        result = controller.set_state(self.params(password='old-password'))

        assert result.changed is False
        assert irmc.patched_bodies() == [{'Password': 'old-password'}]

    def test_set_state_password_same_login_failed(self, controller, irmc):
        """set_state: 500の後にログインもできなければ、元のエラーになることのテストです。"""
        irmc.status[('PATCH', f'{ACCOUNTS_PATH}/3')] = 500
        with pytest.raises(HttpError) as e:
            controller.set_state(self.params(password='another-password'))
        assert e.value.status == 500
        assert "login as 'ansibleuser' returned status 401" in e.value.message

    def test_set_state_password_rejected(self, controller, irmc):
        """set_state: 400でもログインできなければ、iRMCのエラーをそのまま返すことのテストです（規則違反など）。"""
        irmc.status[('PATCH', f'{ACCOUNTS_PATH}/3')] = (400, 'The password does not meet the requirements.')
        with pytest.raises(HttpError, match='does not meet the requirements') as e:
            controller.set_state(self.params(password='another-password'))
        assert e.value.status == 400
        assert "login as 'ansibleuser' returned status 401" in e.value.message

    def test_set_state_password_other_error(self, controller, irmc):
        """set_state: 400と500以外のエラーは、ログインを試さずにそのままエラーになることのテストです。"""
        irmc.status[('PATCH', f'{ACCOUNTS_PATH}/3')] = 403
        login = Mock(side_effect=irmc.login)
        controller.irmc_factory = login
        with pytest.raises(HttpError) as e:
            controller.set_state(self.params(password='another-password'))
        assert e.value.status == 403
        login.assert_not_called()

    def test_set_state_partial_failure(self, controller, irmc, files):
        """set_state: 途中で失敗した場合は、変更済みの内容をメッセージに含めることのテストです。"""
        irmc.status[('POST', f'{ACCOUNTS_PATH}/3/Actions/Oem/{irmc.oem_prefix}User.AddUserSSHKey')] = 400
        with pytest.raises(HttpError, match=r'already changed: settings \(Description\)'):
            controller.set_state(self.params(account={'Description': 'new'}, ssh_public_key_path=files['id.pub']))

    # ---- SNMPv3 ----

    def test_set_state_snmpv3_enable_with_type(self, controller, irmc, vendor):
        """set_state: 有効化とAuthPrivTypeの変更は1回で送ることのテストです。"""
        irmc.oem(f'{ACCOUNTS_PATH}/3')['SnmpV3']['ServiceEnabled'] = False

        result = controller.set_state(self.params(account={
            'SnmpV3': {'ServiceEnabled': True, 'AuthPrivType': 'SHA512_AES'}}))

        assert result.changed is True
        assert irmc.patched_bodies() == [
            {'Oem': {vendor: {'SnmpV3': {'ServiceEnabled': True, 'AuthPrivType': 'SHA512_AES'}}}}]

    def test_set_state_snmpv3_disable_drops_type(self, controller, irmc, vendor):
        """set_state: 無効化するときはAuthPrivTypeを送らないことのテストです（iRMCがSHA256_AESに戻す）。"""
        irmc.oem(f'{ACCOUNTS_PATH}/3')['SnmpV3']['AuthPrivType'] = 'SHA512_DES'

        result = controller.set_state(self.params(account={
            'SnmpV3': {'ServiceEnabled': False, 'AuthPrivType': 'SHA256_AES'}}))

        assert result.changed is True
        assert irmc.patched_bodies() == [{'Oem': {vendor: {'SnmpV3': {'ServiceEnabled': False}}}}]
        assert result.extra_fields['account']['SnmpV3'] == {'ServiceEnabled': False, 'AuthPrivType': 'SHA256_AES'}

    @pytest.mark.parametrize('snmpv3', [
        pytest.param({'ServiceEnabled': False, 'AuthPrivType': 'SHA384_AES'}, id='disable'),
        pytest.param({'AuthPrivType': 'SHA384_AES'}, id='already_disabled'),
    ])
    def test_set_state_snmpv3_type_while_disabled(self, controller, irmc, snmpv3):
        """set_state: 無効なのにSHA256_AES以外を指定すると、送る前にValidationErrorになることのテストです。"""
        if 'ServiceEnabled' not in snmpv3:
            irmc.oem(f'{ACCOUNTS_PATH}/3')['SnmpV3']['ServiceEnabled'] = False
        with pytest.raises(ValidationError, match="'SnmpV3.AuthPrivType' can be 'SHA384_AES' only while"):
            controller.set_state(self.params(account={'SnmpV3': snmpv3}))
        irmc.patch.assert_not_called()

    def test_set_state_snmpv3_copy_disabled(self, controller, irmc):
        """set_state: 無効のユーザーの設定（SHA256_AES）を無効のユーザーに渡しても何も送らないことのテストです。"""
        irmc.oem(f'{ACCOUNTS_PATH}/3')['SnmpV3']['ServiceEnabled'] = False
        result = controller.set_state(self.params(account={
            'SnmpV3': {'ServiceEnabled': False, 'AuthPrivType': 'SHA256_AES'}}))

        assert result.changed is False
        irmc.patch.assert_not_called()

    def test_set_state_patch_failure(self, controller, irmc):
        """set_state: PATCHの失敗はExtendedInfoのメッセージを含むHttpErrorになることのテストです。"""
        irmc.status[('PATCH', f'{ACCOUNTS_PATH}/3')] = 409
        with pytest.raises(HttpError, match='PATCH failed') as e:
            controller.set_state(self.params(account={'Description': 'new'}))
        assert e.value.status == 409

    # ---- SSH公開鍵 / S/MIME証明書 ----

    def test_set_state_ssh_key(self, controller, irmc, files):
        """set_state: SSH公開鍵は、フィンガープリントが違うときだけ登録することのテストです。"""
        result = controller.set_state(self.params(ssh_public_key_path=files['id.pub']))

        assert result.changed is True
        assert irmc.post.call_args.args[0].endswith(f'/{irmc.oem_prefix}User.AddUserSSHKey')
        assert SSH_KEY_MD5 in result.extra_fields['account_info']['SSHv2KeyFingerprint']

        irmc.post.reset_mock()
        again = controller.set_state(self.params(ssh_public_key_path=files['id.pub']))
        assert again.changed is False
        irmc.post.assert_not_called()

    def test_set_state_ssh_key_m8_fingerprint(self, controller, irmc, files):
        """set_state: M8以降の世代のフィンガープリント（SHA-256の先頭16バイト）でも登録済みと判断することのテストです。"""
        irmc.oem(f'{ACCOUNTS_PATH}/3')['SSHv2KeyFingerprint'] = f'rsa 256 {SSH_KEY_SHA256_16}:'
        result = controller.set_state(self.params(ssh_public_key_path=files['id.pub']))

        assert result.changed is False
        irmc.post.assert_not_called()

    def test_set_state_ssh_key_case_insensitive(self, controller, irmc, files):
        """set_state: 鍵の種類の大文字小文字と末尾の':'の違いは無視することのテストです。"""
        irmc.oem(f'{ACCOUNTS_PATH}/3')['SSHv2KeyFingerprint'] = f'ed25519 256 {SSH_KEY_MD5.upper()}'
        result = controller.set_state(self.params(ssh_public_key_path=files['id.pub']))

        assert result.changed is False
        irmc.post.assert_not_called()

    def test_set_state_smime_certificate(self, controller, irmc, files):
        """set_state: S/MIME証明書は、SHA1フィンガープリントが違うときだけ登録することのテストです。"""
        result = controller.set_state(self.params(smime_certificate_path=files['smime.pem']))

        assert result.changed is True
        assert irmc.post.call_args.args[0].endswith(f'/{irmc.oem_prefix}User.AddUserMIMECert')
        assert result.extra_fields['account_info']['SMIMECertificate'] == {'SHA1FingerPrint': CERT_SHA1}

        irmc.post.reset_mock()
        again = controller.set_state(self.params(smime_certificate_path=files['smime.pem']))
        assert again.changed is False
        irmc.post.assert_not_called()

    @pytest.mark.parametrize(('param', 'name', 'message'), [
        ('ssh_public_key_path', 'broken.pub', 'is not an OpenSSH public key'),
        ('smime_certificate_path', 'broken.pem', 'is not a PEM certificate'),
    ])
    def test_set_state_invalid_file(self, controller, irmc, files, param, name, message):
        """set_state: 形式が正しくないファイルはValidationErrorになることのテストです。"""
        with pytest.raises(ValidationError, match=message):
            controller.set_state(self.params(**{param: files[name]}))
        irmc.post.assert_not_called()

    def test_set_state_missing_file(self, controller, irmc, files):
        """set_state: ファイルが無ければ、iRMCに何も送らずにModuleErrorになることのテストです。"""
        with pytest.raises(ModuleError, match='Could not read file'):
            controller.set_state(self.params(name='newuser', password='x', ssh_public_key_path=files['missing']))
        irmc.post.assert_not_called()

    # ---- delete ----

    def test_delete_state(self, controller, irmc):
        """delete_state: ユーザーを削除し、2回目は変更なしになることのテストです。"""
        result = controller.delete_state({'name': 'ansibleuser'})
        assert result.changed is True
        irmc.delete.assert_called_once_with(f'{ACCOUNTS_PATH}/3')

        again = controller.delete_state({'name': 'ansibleuser'})
        assert again.changed is False
        assert irmc.delete.call_count == 1

    def test_delete_state_failure(self, controller, irmc):
        """delete_state: 削除に失敗した場合はHttpErrorになることのテストです。"""
        irmc.status[('DELETE', f'{ACCOUNTS_PATH}/3')] = 403
        with pytest.raises(HttpError) as e:
            controller.delete_state({'name': 'ansibleuser'})
        assert e.value.status == 403


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
            'name': 'ansibleuser',
            'password': None,
            'account': None,
            'ssh_public_key_path': None,
            'smime_certificate_path': None,
        }
        module._verbosity = 0
        return module

    @pytest.fixture
    def mock_logger(self):
        """to_logs_dict()が空辞書を返すモックLoggerを返すfixtureです。"""
        logger = Mock()
        logger.to_logs_dict.return_value = {}
        return logger

    @patch('ansible_collections.fsas.primergy.plugins.modules.irmc_account.iRMC')
    @patch('ansible_collections.fsas.primergy.plugins.modules.irmc_account.AnsibleLogger')
    def test_get_command_success(self, mock_logger_class, mock_irmc_class, mock_module, mock_logger):
        """get command: 正常系の統合テストです。"""
        from ansible_collections.fsas.primergy.plugins.modules.irmc_account import irmc_account

        mock_logger_class.return_value = mock_logger
        mock_irmc_class.return_value = FakeIrmc('Fsas')

        irmc_account(mock_module)

        mock_module.exit_json.assert_called_once()
        call_kwargs = mock_module.exit_json.call_args[1]
        assert call_kwargs['changed'] is False
        assert call_kwargs['account_info']['UserName'] == 'ansibleuser'
        mock_module.fail_json.assert_not_called()

    @patch('ansible_collections.fsas.primergy.plugins.modules.irmc_account.iRMC')
    @patch('ansible_collections.fsas.primergy.plugins.modules.irmc_account.AnsibleLogger')
    def test_set_command_password_login(self, mock_logger_class, mock_irmc_class, mock_module, mock_logger):
        """set command: 同じパスワードの確認に、対象ユーザーの認証情報でiRMCクライアントを作ることのテストです。"""
        from ansible_collections.fsas.primergy.plugins.modules.irmc_account import irmc_account

        mock_module.params.update({'command': 'set', 'password': 'old-password'})
        mock_logger_class.return_value = mock_logger
        irmc = FakeIrmc('Fsas')
        login_client = irmc.login('ansibleuser', 'old-password')
        mock_irmc_class.side_effect = [irmc, login_client]

        irmc_account(mock_module)

        mock_module.exit_json.assert_called_once()
        assert mock_module.exit_json.call_args[1]['changed'] is False
        assert mock_irmc_class.call_args_list[1].kwargs['username'] == 'ansibleuser'
        assert mock_irmc_class.call_args_list[1].kwargs['password'] == 'old-password'

    @patch('ansible_collections.fsas.primergy.plugins.modules.irmc_account.iRMC')
    @patch('ansible_collections.fsas.primergy.plugins.modules.irmc_account.AnsibleLogger')
    def test_delete_command_success(self, mock_logger_class, mock_irmc_class, mock_module, mock_logger):
        """delete command: 正常系の統合テストです。"""
        from ansible_collections.fsas.primergy.plugins.modules.irmc_account import irmc_account

        mock_module.params.update({'command': 'delete'})
        mock_logger_class.return_value = mock_logger
        mock_irmc_class.return_value = FakeIrmc('Fsas')

        irmc_account(mock_module)

        mock_module.exit_json.assert_called_once()
        assert mock_module.exit_json.call_args[1]['changed'] is True

    @patch('ansible_collections.fsas.primergy.plugins.modules.irmc_account.iRMC')
    @patch('ansible_collections.fsas.primergy.plugins.modules.irmc_account.AnsibleLogger')
    def test_module_error_handling(self, mock_logger_class, mock_irmc_class, mock_module, mock_logger):
        """ModuleErrorがfail_jsonになることのテストです。"""
        from ansible_collections.fsas.primergy.plugins.modules.irmc_account import irmc_account

        mock_module.params.update({'name': 'nobody'})
        mock_logger_class.return_value = mock_logger
        mock_irmc_class.return_value = FakeIrmc('Fsas')

        irmc_account(mock_module)

        mock_module.fail_json.assert_called_once()
        assert "User 'nobody' not found" in mock_module.fail_json.call_args[1]['msg']
        mock_module.exit_json.assert_not_called()

    @patch('ansible_collections.fsas.primergy.plugins.modules.irmc_account.iRMC')
    @patch('ansible_collections.fsas.primergy.plugins.modules.irmc_account.AnsibleLogger')
    def test_http_error_handling(self, mock_logger_class, mock_irmc_class, mock_module, mock_logger):
        """HTTPエラーがstatus付きのfail_jsonになることのテストです。"""
        from ansible_collections.fsas.primergy.plugins.modules.irmc_account import irmc_account

        mock_module.params.update({'command': 'set', 'account': {'Description': 'new'}})
        mock_logger_class.return_value = mock_logger
        mock_irmc_class.return_value = FakeIrmc('Fsas', status={('PATCH', f'{ACCOUNTS_PATH}/3'): 409})

        irmc_account(mock_module)

        mock_module.fail_json.assert_called_once()
        assert mock_module.fail_json.call_args[1]['status'] == 409

    @patch('ansible_collections.fsas.primergy.plugins.modules.irmc_account.iRMC')
    @patch('ansible_collections.fsas.primergy.plugins.modules.irmc_account.AnsibleLogger')
    def test_unexpected_error_handling(self, mock_logger_class, mock_irmc_class, mock_module, mock_logger):
        """予期しない例外（接続エラー等）のハンドリングのテストです。"""
        from ansible_collections.fsas.primergy.plugins.modules.irmc_account import irmc_account

        mock_logger_class.return_value = mock_logger
        irmc = FakeIrmc('Fsas')
        irmc.get.side_effect = ConnectionError('connection refused')
        mock_irmc_class.return_value = irmc

        irmc_account(mock_module)

        mock_module.fail_json.assert_called_once()
        call_kwargs = mock_module.fail_json.call_args[1]
        assert 'Unexpected error: connection refused' in call_kwargs['msg']
        assert 'exception' in call_kwargs

    @patch('ansible_collections.fsas.primergy.plugins.modules.irmc_account.iRMC')
    @patch('ansible_collections.fsas.primergy.plugins.modules.irmc_account.AnsibleLogger')
    def test_check_mode(self, mock_logger_class, mock_irmc_class, mock_module):
        """check_mode時はiRMCにアクセスせずに終了することのテストです。"""
        from ansible_collections.fsas.primergy.plugins.modules.irmc_account import irmc_account

        mock_module.check_mode = True
        # 実際のexit_json()と同様に処理を終了させる
        mock_module.exit_json.side_effect = SystemExit

        with pytest.raises(SystemExit):
            irmc_account(mock_module)

        mock_module.exit_json.assert_called_once_with(changed=False, msg='module was not run')
        mock_irmc_class.assert_not_called()
