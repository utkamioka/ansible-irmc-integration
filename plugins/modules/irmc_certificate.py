#!/usr/bin/python

# Copyright 2018-2026 Fsas Technologies Inc.
# GNU General Public License v3.0+ (see LICENSE.md or https://www.gnu.org/licenses/gpl-3.0.txt)


DOCUMENTATION = r'''
---
module: irmc_certificate

short_description: manage iRMC certificates

description:
    - Ansible module to get or set the iRMC SSL/TLS server certificate and the CA certificate
      via iRMC Redfish interface.
    - Module Version V2.0.0.

requirements:
    - The module needs to run locally.
    - Python >= 3.14
    - Python modules 'requests', 'urllib3', 'requests_toolbelt'

version_added: "2.4"

author:
    - Yutaka Kamioka (<yutaka.kamioka@fujitsu.com>)

options:
    irmc_url:
        type:        str
        description: IP address of the iRMC to be requested for data.
        required:    true
    irmc_username:
        type:        str
        description: iRMC user for basic authentication.
        required:    true
    irmc_password:
        type:        str
        description: Password for iRMC user for basic authentication.
        required:    true
    validate_certs:
        type:        bool
        description: Evaluate SSL certificate (set to false for self-signed certificate).
        required:    false
        default:     true
    command:
        type:        str
        description:
            - Get or set iRMC certificate(s).
            - A new SSL certificate is used after iRMC is rebooted.
        required:    false
        default:     get
        choices:     ['get', 'set']
    private_key_path:
        type:        str
        description:
            - Path to file containing SSL private key.
            - This option also requires the SSL certificate.
        required:    false
    ssl_cert_path:
        type:        str
        description:
            - Path to file containing SSL certificate.
            - This option also requires the SSL private key.
        required:    false
    ssl_ca_cert_path:
        type:        str
        description: Path to file containing SSL CA certificate.
        required:    false

notes:
    - Command 'set' compares the SHA1 fingerprint of each given certificate with the one registered
      in the iRMC, and registers only the certificates which differ. If nothing differs, or no certificate
      is given, nothing is changed. The private key is not compared (it cannot be read from the iRMC),
      and is sent only together with a new SSL certificate.
    - A new SSL certificate is used after iRMC is rebooted. The role 'irmc_set_certificate' registers the certificates
      and reboots iRMC. Before the reboot, 'certificates' already shows the registered certificate.
    - After a CA certificate is registered, the iRMC web server restarts.
      The module waits until the iRMC responds again.
    - The certificate files (PEM) themselves cannot be read from the iRMC. Command 'get' returns
      the certificate information provided by the iRMC Redfish interface
      (fingerprint, subject, issuer, validity, ...).
'''

EXAMPLES = r'''
- name: Get and show SSL certificates
  tags:
    - get
  block:
    - name: Get SSL certificates
      fsas.primergy.irmc_certificate:
        irmc_url: "{{ inventory_hostname }}"
        irmc_username: "{{ irmc_user }}"
        irmc_password: "{{ irmc_password }}"
        validate_certs: "{{ validate_certificate }}"
        command: "get"
      register: certificates
      delegate_to: localhost
    - name: Show SSL certificates
      ansible.legacy.debug:
        var: certificates.certificates

# The SSL server certificate is used after iRMC is rebooted
- name: Set SSL server certificate
  fsas.primergy.irmc_certificate:
    irmc_url: "{{ inventory_hostname }}"
    irmc_username: "{{ irmc_user }}"
    irmc_password: "{{ irmc_password }}"
    validate_certs: "{{ validate_certificate }}"
    command: "set"
    ssl_cert_path: "{{ ssl_cert_path }}"
    private_key_path: "{{ private_key_path }}"
  delegate_to: localhost
  tags:
    - set_server_cert

- name: Set CA certificate
  fsas.primergy.irmc_certificate:
    irmc_url: "{{ inventory_hostname }}"
    irmc_username: "{{ irmc_user }}"
    irmc_password: "{{ irmc_password }}"
    validate_certs: "{{ validate_certificate }}"
    command: "set"
    ssl_ca_cert_path: "{{ ssl_ca_cert_path }}"
  delegate_to: localhost
  tags:
    - set_ca_cert
'''

RETURN = r'''
certificates:
    description:
        - Certificates registered in the iRMC (after the change for command "set").
        - The values are the objects of the iRMC Redfish interface, without 'Oem' and '@odata.*' properties.
    returned: always
    type: dict
    contains:
        HttpsCertificate:
            description: SSL/TLS server certificate ('HttpsCertificate' of Certificate0)
            returned: always
            type: dict
            sample:
                FingerPrint: "ba:ea:4a:17:77:60:40:e3:95:5f:6f:d1:4c:6c:a2:9b:06:1b:6e:0a"
                FingerPrintHashAlgorithm: TPM_ALG_SHA1
                SerialNumber: "53:63:5c:34:b4:a4:52:92:79:e3:8c:c1:3a:46:5e:cc:f6:43:78:d5"
                SignatureAlgorithm: sha256WithRSAEncryption
                ValidNotBefore: "2026-10-18T07:57:11+00:00"
                ValidNotAfter: "2027-10-18T07:57:11+00:00"
                Issuer: {CommonName: Test Root CA, Country: JP}
                Subject: {CommonName: 192.0.2.1, Country: US}
        CACertificate:
            description: CA certificate ('CACertificate' of the iRMC certificate configuration)
            returned: always
            type: dict
            sample:
                SHA1FingerPrint: "1e:5d:c3:bd:dc:85:10:05:7e:1c:ac:e9:3f:a8:55:e5:71:e5:5b:71"
                MD5FingerPrint: "83:bb:b6:44:99:94:b5:8b:7c:26:41:06:e0:98:bb:74"
                SerialNumber: "3e:be:0c:1b:28:06:11:e6:71:3e:de:a7:05:57:2b:e4:41:00:79:a3"
                ValidFrom: "2026-10-18T07:57:11+00:00"
                ValidTo: "2036-10-15T07:57:11+00:00"
                IssuedFrom: {CommonName: Test Root CA}
                IssuedTo: {CommonName: Test Root CA}
'''


import ntpath
import traceback
from typing import Any, Mapping

from ansible.module_utils.basic import AnsibleModule, missing_required_lib
from ansible_collections.fsas.primergy.plugins.module_utils.controller_result import ControllerResult
from ansible_collections.fsas.primergy.plugins.module_utils.errors import HttpError, ModuleError, ValidationError
from ansible_collections.fsas.primergy.plugins.module_utils.helpers import dig, pem_sha1_fingerprint, remove_odata_keys
from ansible_collections.fsas.primergy.plugins.module_utils.irmc_client import iRMC
from ansible_collections.fsas.primergy.plugins.module_utils.logger import AnsibleLogger, Logger

try:
    from requests_toolbelt import MultipartEncoder
    HAS_REQUESTS_TOOLBELT = True
except ImportError:
    HAS_REQUESTS_TOOLBELT = False

# TLSサーバー証明書のリソース
# Managers/iRMC からのリンクでは辿れない（ManagerNetwork は廃止予定で NetworkProtocol への参照が無い）。
# パスは「Redfish_API_Specification_3_11S.pdf」に記載されている。vendorによらず同じ
CERTIFICATE0_PATH = '/redfish/v1/Managers/iRMC/NetworkProtocol/HTTPS/Certificates/Certificate0'

PEM_CONTENT_TYPE = 'application/x-pem-file'

# CA証明書を登録した後、iRMCのWebサーバーが再起動して応答するまでの待ち方（秒）
# 実機（RX1330 M6S）では登録の数秒後に接続できなくなり、10秒後には復帰していた
CA_UPLOAD_INITIAL_DELAY = 10
CA_UPLOAD_RETRY_INTERVAL = 5
CA_UPLOAD_TIMEOUT = 60

SET_PARAMETERS = ('private_key_path', 'ssl_cert_path', 'ssl_ca_cert_path')


class CertificateController:
    """iRMCの証明書（TLSサーバー証明書・CA証明書）を管理するControllerクラスです。
    """

    def __init__(self, irmc: iRMC, logger: Logger):
        """CertificateControllerを初期化します。

        引数:
            irmc - iRMCクライアントインスタンス
            logger - ログ出力用のLoggerインスタンス
        """
        self.irmc = irmc
        self.logger = logger

    def _vendor(self) -> str:
        """iRMCのベンダーを返します。

        戻り値:
            ベンダー（M7以前は"ts_fujitsu"、M8以降は"Fsas"）

        例外:
            ModuleError - iRMCのベンダーを判別できない場合
        """
        vendor = self.irmc.vendor
        if vendor is None:
            raise ModuleError("Failed to detect iRMC vendor")
        return vendor

    def _oem_prefix(self) -> str:
        """OEMアクション名の接頭辞を返します。

        戻り値:
            接頭辞（M7以前は"FTS"、M8以降は"Fsas"）

        例外:
            ModuleError - iRMCのベンダーを判別できない場合
        """
        oem_prefix = self.irmc.oem_prefix
        if oem_prefix is None:
            raise ModuleError("Failed to detect iRMC vendor")
        return oem_prefix

    def _ca_path(self) -> str:
        """CA証明書を含む証明書設定リソースのパスを返します。

        戻り値:
            証明書設定リソースのパス

        例外:
            ModuleError - iRMCのベンダーを判別できない場合
        """
        # 以下のリンクを辿って得られるパスを組み立てる
        #   GET /redfish/v1/Managers/iRMC
        #     -> .Oem.{vendor}.iRMCConfiguration."@odata.id"
        #        (/redfish/v1/Managers/iRMC/Oem/{vendor}/iRMCConfiguration)
        #   GET /redfish/v1/Managers/iRMC/Oem/{vendor}/iRMCConfiguration
        #     -> .Certificates."@odata.id"
        #        (/redfish/v1/Managers/iRMC/Oem/{vendor}/iRMCConfiguration/Certificates)
        return f'/redfish/v1/Managers/iRMC/Oem/{self._vendor()}/iRMCConfiguration/Certificates'

    def _replace_certificate_path(self) -> str:
        """TLSサーバー証明書の差し替えアクションのパスを返します。

        戻り値:
            ReplaceCertificateアクションのパス

        例外:
            ModuleError - iRMCのベンダーを判別できない場合
        """
        # 以下のリンクを辿って得られるパスを組み立てる
        #   GET /redfish/v1/Managers/iRMC/NetworkProtocol/HTTPS/Certificates/Certificate0
        #     -> .Actions.Oem."#{oem_prefix}Certificates.ReplaceCertificate".target
        return f'{CERTIFICATE0_PATH}/Actions/Oem/{self._oem_prefix()}Certificates.ReplaceCertificate'

    def _upload_ca_certificate_path(self) -> str:
        """CA証明書の登録アクションのパスを返します。

        戻り値:
            UploadCACertificateアクションのパス

        例外:
            ModuleError - iRMCのベンダーを判別できない場合
        """
        # 以下のリンクを辿って得られるパスを組み立てる
        #   GET /redfish/v1/Managers/iRMC/Oem/{vendor}/iRMCConfiguration/Certificates
        #     -> .Actions."#{oem_prefix}Certificates.UploadCACertificate".target
        return f'{self._ca_path()}/Actions/{self._oem_prefix()}Certificates.UploadCACertificate'

    def _fetch(self, path: str) -> dict:
        """リソースを取得します。

        書き込みの後はiRMCクライアントがキャッシュを捨てるので、常に最新の値が得られます。

        引数:
            path - 取得するリソースのパス

        戻り値:
            レスポンスボディ

        例外:
            HttpError - HTTPリクエストが失敗した場合
        """
        response = self.irmc.get(path)
        if response.status != 200:
            msg = f"Failed to {response.request.method} {response.request.path}"
            self.logger.warn(msg)
            raise HttpError(msg, status=response.status)
        return response.body

    def _certificate_info(self, body: Any, field: str, path: str) -> dict:
        """リソースから証明書の情報を取り出し、Oemと@odataのキーを取り除きます。

        引数:
            body - リソースのレスポンスボディ
            field - 証明書の情報を持つプロパティ名
            path - 警告メッセージに使うパス

        戻り値:
            証明書の情報

        例外:
            ModuleError - プロパティが存在しない場合
        """
        info = dig(body, field)
        if not isinstance(info, dict):
            msg = f"{field!r} field not found in response of {path}"
            self.logger.warn(msg)
            raise ModuleError(msg)
        # Oemはvendorによって構造が違うため返さない
        info = {key: value for key, value in info.items() if key != 'Oem'}
        return remove_odata_keys(info)

    def _collect(self) -> dict:
        """登録済みの証明書の情報を取得し、戻り値の形式にまとめます。

        戻り値:
            証明書の情報（HttpsCertificate / CACertificate）

        例外:
            HttpError - HTTPリクエストが失敗した場合
            ModuleError - iRMCのベンダーを判別できない場合、またはレスポンスに証明書の情報が無い場合
        """
        ca_path = self._ca_path()
        return {
            'HttpsCertificate': self._certificate_info(self._fetch(CERTIFICATE0_PATH), 'HttpsCertificate',
                                                       CERTIFICATE0_PATH),
            'CACertificate': self._certificate_info(self._fetch(ca_path), 'CACertificate', ca_path),
        }

    def _read_file(self, path: str) -> bytes:
        """証明書・秘密鍵のファイルを読み込みます。

        引数:
            path - ファイルのパス

        戻り値:
            ファイルの内容

        例外:
            ModuleError - ファイルを読み込めない場合
        """
        try:
            with open(path, 'rb') as f:
                return f.read()
        except OSError as e:
            raise ModuleError(f"Could not read key/certificate file at '{path}': {e}") from e

    def _fingerprint(self, pem: bytes, path: str) -> str:
        """証明書ファイルの内容からSHA1フィンガープリントを計算します。

        引数:
            pem - 証明書ファイルの内容
            path - エラーメッセージに使うファイルのパス

        戻り値:
            SHA1フィンガープリント（小文字16進数の':'区切り）

        例外:
            ValidationError - PEM形式の証明書ではない場合
        """
        try:
            return pem_sha1_fingerprint(pem.decode('ascii', errors='replace'))
        except ValueError as e:
            raise ValidationError(f"'{path}' is not a PEM certificate: {e}") from e

    def _post_multipart(self, path: str, fields: dict, changed_paths: list[str]) -> None:
        """multipart/form-dataでアクションを実行します。

        引数:
            path - アクションのパス
            fields - フォームのフィールド（フィールド名 -> (ファイル名, 内容, Content-Type)）
            changed_paths - これまでに変更済みのアクションのパス（失敗時のメッセージに使用）

        例外:
            HttpError - HTTPリクエストが失敗した場合
        """
        self.logger.debug(f"Posting {', '.join(fields)} to {path}")
        response = self.irmc.post(path, MultipartEncoder(fields=fields))
        if response.status not in (200, 202, 204):
            error_message = dig(response.body, 'error', 'message') if isinstance(response.body, dict) else None
            msg = (
                f"Failed to {response.request.method} {response.request.path}: "
                f"{error_message or response.body}"
            )
            # TLS証明書とCA証明書は別々に登録するため、途中で失敗すると一部だけ変更された状態になる
            if changed_paths:
                msg += f" (already changed: {', '.join(changed_paths)})"
            self.logger.warn(msg)
            raise HttpError(msg, status=response.status)

    def _plan_tls_upload(self, cert_path: str | None, key_path: str | None) -> tuple | None:
        """TLSサーバー証明書の差し替えが必要か判定し、必要なら送信内容を返します。

        引数:
            cert_path - 証明書ファイルのパス（未指定ならNone）
            key_path - 秘密鍵ファイルのパス（cert_pathと一緒に指定される）

        戻り値:
            (アクションのパス, フォームのフィールド, 登録後にiRMCの応答を待つか)。不要ならNone

        例外:
            ValidationError - 証明書がPEM形式でない場合
            HttpError - HTTPリクエストが失敗した場合
            ModuleError - ファイルを読み込めない場合、またはiRMCのベンダーを判別できない場合
        """
        if cert_path is None:
            return None
        cert = self._read_file(cert_path)
        key = self._read_file(key_path)
        current = dig(self._fetch(CERTIFICATE0_PATH), 'HttpsCertificate', 'FingerPrint')
        if self._fingerprint(cert, cert_path) == str(current).lower():
            return None
        return (self._replace_certificate_path(), {
            'certificate': (ntpath.basename(cert_path), cert, PEM_CONTENT_TYPE),
            'private_key': (ntpath.basename(key_path), key, PEM_CONTENT_TYPE),
        }, False)

    def _plan_ca_upload(self, ca_path: str | None) -> tuple | None:
        """CA証明書の登録が必要か判定し、必要なら送信内容を返します。

        引数:
            ca_path - CA証明書ファイルのパス（未指定ならNone）

        戻り値:
            (アクションのパス, フォームのフィールド, 登録後にiRMCの応答を待つか)。不要ならNone

        例外:
            ValidationError - 証明書がPEM形式でない場合
            HttpError - HTTPリクエストが失敗した場合
            ModuleError - ファイルを読み込めない場合、またはiRMCのベンダーを判別できない場合
        """
        if ca_path is None:
            return None
        ca_cert = self._read_file(ca_path)
        current = dig(self._fetch(self._ca_path()), 'CACertificate', 'SHA1FingerPrint')
        if self._fingerprint(ca_cert, ca_path) == str(current).lower():
            return None
        # CA証明書を登録するとiRMCのWebサーバーが再起動するので、登録後に応答を待つ
        return (self._upload_ca_certificate_path(), {
            'data': (ntpath.basename(ca_path), ca_cert, PEM_CONTENT_TYPE),
        }, True)

    def get_state(self) -> ControllerResult:
        """登録済みの証明書の情報を取得します。

        戻り値:
            ControllerResult（changed=False, certificates属性を含む）

        例外:
            HttpError - HTTPリクエストが失敗した場合
            ModuleError - iRMCのベンダーを判別できない場合、またはレスポンスに証明書の情報が無い場合
        """
        self.logger.debug("Getting certificates from iRMC")
        return ControllerResult.unchanged(certificates=self._collect())

    def set_state(self, params: Mapping[str, Any]) -> ControllerResult:
        """証明書を登録します。

        指定された証明書のうち、iRMCに登録済みのものとSHA1フィンガープリントが異なるものだけを登録します。
        TLSサーバー証明書の差し替え、CA証明書の登録の順に行います
        （CA証明書を登録するとiRMCのWebサーバーが再起動するため、最後にする）。

        引数:
            params - パラメータ辞書（任意: private_key_path, ssl_cert_path, ssl_ca_cert_path。
                     private_key_pathとssl_cert_pathは両方そろって指定する。空文字は未指定として扱う）

        戻り値:
            ControllerResult（changed=TrueまたはFalse, certificates属性を含む）

        例外:
            ValidationError - 秘密鍵と証明書の片方だけが指定された場合、または証明書がPEM形式でない場合
            HttpError - HTTPリクエストが失敗した場合
            ModuleError - ファイルを読み込めない場合、iRMCのベンダーを判別できない場合、
                          またはCA証明書の登録後にiRMCが応答しない場合
        """
        # 空文字は未指定として扱う（旧版と同じ）
        key_path, cert_path, ca_path = (params.get(name) or None for name in SET_PARAMETERS)

        if (key_path is None) != (cert_path is None):
            raise ValidationError(
                "Both 'private_key_path' and 'ssl_cert_path' are required to successfully import SSL key pair!"
            )

        # 変更対象のパラメータが1つも無い場合は、何もせず変更なしとして終える
        # (roleの変数を指定せずに呼ばれてもエラーにしないため。irmc_ntpと同じ方針)
        if cert_path is None and ca_path is None:
            return ControllerResult.unchanged(
                msg=f"No certificate to set was specified ({', '.join(SET_PARAMETERS)})",
                certificates=self._collect(),
            )

        # 登録が必要なものを順番に並べる(TLSサーバー証明書 -> CA証明書)
        uploads = [
            upload
            for upload in (self._plan_tls_upload(cert_path, key_path), self._plan_ca_upload(ca_path))
            if upload is not None
        ]

        if not uploads:
            return ControllerResult.unchanged(
                msg="Certificates are already registered",
                certificates=self._collect(),
            )

        changed_paths = []
        for path, fields, wait_after in uploads:
            self._post_multipart(path, fields, changed_paths)
            changed_paths.append(path)

            if wait_after:
                available = self.irmc.wait_until_available(
                    initial_delay=CA_UPLOAD_INITIAL_DELAY,
                    interval=CA_UPLOAD_RETRY_INTERVAL,
                    timeout=CA_UPLOAD_TIMEOUT,
                )
                if not available:
                    raise ModuleError(
                        f"iRMC did not respond within {CA_UPLOAD_INITIAL_DELAY + CA_UPLOAD_TIMEOUT} seconds "
                        f"after the CA certificate was registered (already changed: {', '.join(changed_paths)})"
                    )

        self.logger.log(f"Certificates changed: {', '.join(changed_paths)}")
        return ControllerResult.changed_success(certificates=self._collect())


def irmc_certificate(module: AnsibleModule) -> None:
    """irmc_certificateモジュールのメイン処理です。

    引数:
        module - AnsibleModuleインスタンス
    """
    if module.check_mode:
        module.exit_json(changed=False, msg='module was not run')

    if not HAS_REQUESTS_TOOLBELT:
        module.fail_json(msg=missing_required_lib('requests_toolbelt'))

    # ロガー初期化
    logger = AnsibleLogger(module)

    # iRMCクライアント初期化
    irmc = iRMC(
        ipaddress=module.params['irmc_url'],
        username=module.params['irmc_username'],
        password=module.params['irmc_password'],
        validate_certs=module.params['validate_certs'],
        logger=logger,
        raise_on_error=True,
    )

    # Controller初期化
    controller = CertificateController(irmc, logger)

    # ビジネスロジック実行
    try:
        if module.params['command'] == 'get':
            controller_result = controller.get_state()
        elif module.params['command'] == 'set':
            controller_result = controller.set_state(module.params)
        else:
            raise ValidationError(f"Unknown command: {module.params['command']}")

        result = controller_result.to_exit_dict() | logger.to_logs_dict()
        module.exit_json(**result)

    except ModuleError as e:
        result = e.to_fail_dict() | logger.to_logs_dict()
        module.fail_json(**result)

    except Exception as e:
        # 予期しないエラー（接続エラーを含む）
        result = {'msg': f"Unexpected error: {e}", 'exception': traceback.format_exc()} | logger.to_logs_dict()
        module.fail_json(**result)


def main() -> None:
    module_args = dict(
        irmc_url=dict(required=True, type='str'),
        irmc_username=dict(required=True, type='str'),
        irmc_password=dict(required=True, type='str', no_log=True),
        validate_certs=dict(required=False, type='bool', default=True),
        command=dict(required=False, type='str', default='get', choices=['get', 'set']),
        private_key_path=dict(required=False, type='str', no_log=False),
        ssl_cert_path=dict(required=False, type='str'),
        ssl_ca_cert_path=dict(required=False, type='str'),
    )
    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=False,
    )

    irmc_certificate(module)


if __name__ == '__main__':
    main()
