# モジュール移行ガイド

非推奨（deprecated）になったモジュールから、それに代わるモジュールへの移行方法を説明します。

このコレクションのモジュールの一部は、非推奨になり、新しいモジュールに置き換わります
（たとえば、使っている iRMC のインターフェースが削除される予定のため）。
非推奨のモジュールも当面は動作し、まだ削除しませんが、新しく書くプレイブックでは新しいモジュールを使ってください。
以下の節では、非推奨のモジュールごとに、非推奨になった理由、変わること、タスクの書き換え方を説明します。

- [irmc_user から irmc_account へ](#irmc_user-から-irmc_account-へ)

## irmc_user から irmc_account へ

`irmc_user` は、iRMC のリモートスクリプティングインターフェース（SCCI）で、iRMC のローカルユーザーアカウントを管理するモジュールです。
SCCI は iRMC から削除される予定です。代わりに、iRMC の Redfish インターフェースを使う `irmc_account` を使ってください。

### 主な違い

- **コマンド**：`create` と `change` は `set` にまとめました。
  `set` は、ユーザーがいなければ作成し、いれば違う設定だけを変更します。
  `get` と `delete` は同じです。`delete` は、ユーザーがいなければ変更なし（changed=false）になります。
- **設定**：設定は、オプション `account` に入れ子の辞書で指定します。
  キーと値は iRMC の Redfish インターフェースのものです（たとえば `OEM` ではなく `Oem`）。
- **戻り値**：`get` は、`user` の代わりに `account` と `account_info` を返します。
  `account` は変更できる設定だけを、オプション `account` と同じ構造で含みます。
  そのため、別のユーザーの `set` にそのまま渡せます。たとえば、ユーザーの複製や、設定のファイルへの書き出しと読み込みに使えます。
  `account_info` は、変更できない情報（`UserName`、`Id` など）を含みます。
- **パスワード**：パスワードは iRMC から読み出せないため、指定すると毎回送ります。
  現在と同じパスワードなら、`set` は変更なしになります。
  これはそのユーザーでログインして確かめるため、そのユーザーが Redfish を使えること（`account.Enabled: true`）が必要です。
- **SSH 公開鍵と S/MIME 証明書**：文字列ではなく、ファイルのパスで指定します。
  登録済みのものとフィンガープリントが違うときだけ登録します。
  鍵や証明書そのものは iRMC から読み出せません。`get` が返すのは、その情報
  （`account_info.SSHv2KeyFingerprint`、`account_info.SMIMECertificate`）だけです。

### パラメータの対応

| irmc_user | irmc_account | 備考 |
| --- | --- | --- |
| `command: get` / `create` / `change` / `delete` | `command: get` / `set` / `delete` | `create` と `change` は `set` にまとめた |
| `name` | `name` | |
| `password` | `password` | |
| `description` | `account.Description` | |
| `enabled` | `account.BaseValues.Enabled` | Web UI の「ユーザを有効にする」 |
| `redfish_enabled` | `account.Enabled` | Web UI の「Redfish/Web UI ユーザを有効にする」 |
| `redfish_role` | `account.RoleId` | `NoAccess` は使えない |
| `lan_privilege` | `account.Permissions.Standard.Lan` | `OEM` は `Oem`。`Reserved` は使えない |
| `serial_privilege` | `account.Permissions.Standard.Serial` | `lan_privilege` と同じ |
| `config_user_enabled` | `account.Permissions.Extended.ConfigureUsers` | |
| `config_bmc_enabled` | `account.Permissions.Extended.ConfigureIrmc` | |
| `avr_enabled` | `account.Permissions.Extended.UseVideoRedirection` | |
| `storage_enabled` | `account.Permissions.Extended.UseRemoteStorage` | |
| `shell` | `account.BaseValues.Shell` | `Remote Manager` は `RemoteManager`。`None` は同じ。`SMASH CLP`、`CLI`、`IPMI basic mode`、`IPMI terminal mode` は使えない |
| `snmpv3_enabled` | `account.SnmpV3.ServiceEnabled` | |
| `snmpv3_auth` と `snmpv3_privacy` | `account.SnmpV3.AuthPrivType` | 1つの値にまとめた（`SHA256_AES`、`SHA384_AES`、`SHA512_AES`、`SHA256_DES`、`SHA384_DES`、`SHA512_DES`）。旧の値（`SHA`、`MD5`、`Undefined`、`None`）は使えない |
| `snmpv3_access` | （なし） | Redfish では変更できない。現在の値は `account_info.SnmpV3.AccessType` で返る |
| `ssh_public_key` | `ssh_public_key_path` | 鍵の文字列ではなく、公開鍵のファイルのパス |
| `ssh_certificate` | `smime_certificate_path` | 証明書の文字列ではなく、S/MIME 証明書のファイルのパス |
| `email_enabled` | `account.Email.AlertChassisEventsUser` | Web UI の「Eメール警告を有効にする」。下の注意を参照 |
| `email_encrypted` | `account.Email.SendEncryptedAlerts` | |
| `email_type` | `account.Email.Layout` | `ITS-Format` は `ITS`、`Fixed Subject` は `FixedSubject`、`SMS` は `REMCS`。旧の `REMCS` は使えない |
| `email_server` | `account.Email.PreferredMailServer` | `Automatic` は `Auto` |
| `email_address` | `account.Email.Address` | |
| `alert_fans` | `account.Email.AlertFilter.Fans` | 値（`None`、`Critical`、`Warning`、`All`）は、すべての `alert_*` で同じ |
| `alert_temperatures` | `account.Email.AlertFilter.Temperature` | |
| `alert_hwerrors` | `account.Email.AlertFilter.Hardware` | |
| `alert_syshang` | `account.Email.AlertFilter.SystemHang` | |
| `alert_posterrors` | `account.Email.AlertFilter.Post` | |
| `alert_security` | `account.Email.AlertFilter.Security` | |
| `alert_sysstatus` | `account.Email.AlertFilter.SystemStatus` | |
| `alert_hderrors` | `account.Email.AlertFilter.Harddisk` | |
| `alert_network` | `account.Email.AlertFilter.NetworkError` | |
| `alert_remote` | `account.Email.AlertFilter.RemoteManagement` | |
| `alert_power` | `account.Email.AlertFilter.PowerSupply` | |
| `alert_memory` | `account.Email.AlertFilter.Memory` | |
| `alert_others` | `account.Email.AlertFilter.Others` | |

共通のオプション（`irmc_url`、`irmc_username`、`irmc_password`、`validate_certs`）は同じです。

`email_enabled` についての注意：iRMC の Redfish インターフェースでは、`AlertChassisEventsUser` と `PagingEnabled` の値が
入れ替わっています。Web UI の「Eメール警告を有効にする」は `AlertChassisEventsUser` です。
`irmc_account` は、Redfish インターフェースの名前をそのまま使っています。

### irmc_user に無かった設定

- `account.PasswordChangeRequired`：次のログインでパスワードの変更を求めるか
- `account.TwoFactorAuth.Enabled`：二要素認証
- `account.Email.ExtraSubjectEnabled` / `account.Email.ExtraSubject`：メールの件名に付け足す文字列
- `account.Email.AttachSystemReport`：メールにシステムレポートを添付するか
- `account.Email.AlertFilter.Spare` と `account.Email.PagingEnabled`：Web UI には表示されない項目

### 書き換えの例

書き換え前（`irmc_user`）：

```yaml
- name: Change user account
  fsas.primergy.irmc_user:
    irmc_url: "{{ inventory_hostname }}"
    irmc_username: "{{ irmc_user }}"
    irmc_password: "{{ irmc_password }}"
    validate_certs: "{{ validate_certificate }}"
    command: "change"
    name: "<username>"
    description: "operator account"
    redfish_enabled: true
    redfish_role: "Operator"
    lan_privilege: "OEM"
    email_enabled: true
    email_type: "Fixed Subject"
    email_server: "Automatic"
    email_address: "<user>@example.com"
    alert_fans: "Critical"
  delegate_to: localhost
```

書き換え後（`irmc_account`）：

```yaml
- name: Change user account
  fsas.primergy.irmc_account:
    irmc_url: "{{ inventory_hostname }}"
    irmc_username: "{{ irmc_user }}"
    irmc_password: "{{ irmc_password }}"
    validate_certs: "{{ validate_certificate }}"
    command: "set"
    name: "<username>"
    account:
      Description: "operator account"
      Enabled: true
      RoleId: "Operator"
      Permissions:
        Standard:
          Lan: "Oem"
      Email:
        AlertChassisEventsUser: true
        Layout: "FixedSubject"
        PreferredMailServer: "Auto"
        Address: "<user>@example.com"
        AlertFilter:
          Fans: "Critical"
  delegate_to: localhost
```

ユーザーを作成するときは、`password` も指定してください。`set` は、ユーザーがいなければ作成します。
