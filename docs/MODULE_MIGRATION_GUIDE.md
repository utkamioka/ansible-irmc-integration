# Module Migration Guide

This guide explains how to move from deprecated modules to the modules that replace them.

Some modules of this collection are deprecated and replaced by new modules,
for example because an iRMC interface they use will be removed.
The deprecated modules still work and are not removed yet, but new playbooks should use the new modules.
Each section below describes one deprecated module: why it is deprecated, what changes, and how to rewrite tasks.

- [irmc_user to irmc_account](#irmc_user-to-irmc_account)

## irmc_user to irmc_account

`irmc_user` manages iRMC local user accounts via the iRMC remote scripting interface (SCCI),
which will be removed from the iRMC. Use `irmc_account` instead, which uses the iRMC Redfish interface.

### Main differences

- **Commands**: `create` and `change` are merged into `set`.
  `set` creates the user if it does not exist, and changes only the settings which differ.
  `get` and `delete` are the same. `delete` reports no change if the user does not exist.
- **Settings**: The settings are given in the option `account` as a nested dictionary.
  The keys and values are the ones of the iRMC Redfish interface (for example `Oem` instead of `OEM`).
- **Return values**: `get` returns `account` and `account_info` instead of `user`.
  `account` contains only the settings which can be changed, in the same structure as the option `account`.
  It can be passed as it is to `set` for another user, for example to copy a user,
  or to export the settings to a file and import them later.
  `account_info` contains the information which cannot be changed (for example `UserName` and `Id`).
- **Password**: The password cannot be read from the iRMC, so it is always sent.
  If it is the same as the current one, `set` reports no change.
  This is confirmed by logging in as the user, so the user has to be allowed to use Redfish (`account.Enabled: true`).
- **SSH public key and S/MIME certificate**: They are given as file paths instead of strings,
  and registered only when their fingerprint differs from the registered one.
  The key and the certificate themselves cannot be read from the iRMC. `get` returns only their information
  (`account_info.SSHv2KeyFingerprint` and `account_info.SMIMECertificate`).

### Parameters

| irmc_user | irmc_account | Notes |
| --- | --- | --- |
| `command: get` / `create` / `change` / `delete` | `command: get` / `set` / `delete` | `create` and `change` are merged into `set` |
| `name` | `name` | |
| `password` | `password` | |
| `description` | `account.Description` | |
| `enabled` | `account.BaseValues.Enabled` | 'Enable user' in the Web UI |
| `redfish_enabled` | `account.Enabled` | 'Redfish/Web UI user enabled' in the Web UI |
| `redfish_role` | `account.RoleId` | `NoAccess` is not available |
| `lan_privilege` | `account.Permissions.Standard.Lan` | `OEM` is `Oem`. `Reserved` is not available |
| `serial_privilege` | `account.Permissions.Standard.Serial` | Same as `lan_privilege` |
| `config_user_enabled` | `account.Permissions.Extended.ConfigureUsers` | |
| `config_bmc_enabled` | `account.Permissions.Extended.ConfigureIrmc` | |
| `avr_enabled` | `account.Permissions.Extended.UseVideoRedirection` | |
| `storage_enabled` | `account.Permissions.Extended.UseRemoteStorage` | |
| `shell` | `account.BaseValues.Shell` | `Remote Manager` is `RemoteManager`. `None` is the same. `SMASH CLP`, `CLI`, `IPMI basic mode` and `IPMI terminal mode` are not available |
| `snmpv3_enabled` | `account.SnmpV3.ServiceEnabled` | |
| `snmpv3_auth` and `snmpv3_privacy` | `account.SnmpV3.AuthPrivType` | Merged into one value: `SHA256_AES`, `SHA384_AES`, `SHA512_AES`, `SHA256_DES`, `SHA384_DES` or `SHA512_DES`. The old values (`SHA`, `MD5`, `Undefined`, `None`) are not available |
| `snmpv3_access` | (none) | Cannot be changed via Redfish. The current value is returned as `account_info.SnmpV3.AccessType` |
| `ssh_public_key` | `ssh_public_key_path` | Path to the public key file instead of the key string |
| `ssh_certificate` | `smime_certificate_path` | Path to the S/MIME certificate file instead of the certificate string |
| `email_enabled` | `account.Email.AlertChassisEventsUser` | 'Enable email alerting' in the Web UI. See the note below |
| `email_encrypted` | `account.Email.SendEncryptedAlerts` | |
| `email_type` | `account.Email.Layout` | `ITS-Format` is `ITS`, `Fixed Subject` is `FixedSubject`, `SMS` is `REMCS`. The old `REMCS` is not available |
| `email_server` | `account.Email.PreferredMailServer` | `Automatic` is `Auto` |
| `email_address` | `account.Email.Address` | |
| `alert_fans` | `account.Email.AlertFilter.Fans` | The values (`None`, `Critical`, `Warning`, `All`) are the same for all `alert_*` |
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

The common options (`irmc_url`, `irmc_username`, `irmc_password` and `validate_certs`) are the same.

Note on `email_enabled`: In the iRMC Redfish interface, the values of `AlertChassisEventsUser` and `PagingEnabled`
are swapped. 'Enable email alerting' in the Web UI is `AlertChassisEventsUser`. `irmc_account` uses the names
of the Redfish interface as they are.

### Settings which irmc_user did not support

- `account.PasswordChangeRequired`: whether the user has to change the password at the next login
- `account.TwoFactorAuth.Enabled`: two-factor authentication
- `account.Email.ExtraSubjectEnabled` / `account.Email.ExtraSubject`: text added to the subject of the email
- `account.Email.AttachSystemReport`: attach the system report to the email
- `account.Email.AlertFilter.Spare` and `account.Email.PagingEnabled`: not shown in the Web UI

### Example

Before (`irmc_user`):

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

After (`irmc_account`):

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

To create a user, give `password` too. `set` creates the user if it does not exist.
