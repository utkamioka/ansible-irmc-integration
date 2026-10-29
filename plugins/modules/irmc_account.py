#!/usr/bin/python

# Copyright 2018-2026 Fsas Technologies Inc.
# GNU General Public License v3.0+ (see LICENSE.md or https://www.gnu.org/licenses/gpl-3.0.txt)


DOCUMENTATION = r'''
---
module: irmc_account

short_description: manage iRMC local user accounts

description:
    - Ansible module to get, create, change or delete an iRMC local user account
      via iRMC Redfish interface.
    - This module replaces the deprecated module 'irmc_user'.
    - The settings are given and returned in the structure of the iRMC Redfish interface
      (C(/redfish/v1/AccountService/Accounts/{id})). The vendor specific settings
      (C(Oem.ts_fujitsu) / C(Oem.Fsas)) are moved up to the top level.
      The return value C(account) of command C(get) can be passed to C(account) of command C(set) as it is,
      for example to create a user with the same settings as another user.
    - Module Version V1.0.0.

requirements:
    - The module needs to run locally.
    - Python >= 3.14
    - Python modules 'requests', 'urllib3'
    - Python module 'requests_toolbelt' (only when 'ssh_public_key_path' or 'smime_certificate_path' is given)

version_added: "3.2.0"

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
            - C(get) returns the settings of the user.
            - C(set) creates the user if it does not exist, and changes only the settings which differ.
            - C(delete) deletes the user.
        required:    false
        default:     get
        choices:     ['get', 'set', 'delete']
    name:
        type:        str
        description: Name of the user (C(UserName)).
        required:    true
    password:
        type:        str
        description:
            - Password of the user. Required to create a user.
            - The current password cannot be read from the iRMC. Therefore the password is always sent,
              and the iRMC rejects the same password as the current one (status 500 or 400, depending on
              the iRMC generation). In that case the module logs in as the user with the password,
              and reports no change if it succeeds. Otherwise the error of the iRMC is returned.
              This requires that the user is allowed to use Redfish (C(account.Enabled=true)).
        required:    false
    account:
        type:        dict
        description:
            - Settings of the user. Only the given settings are compared and changed.
            - Same structure as the return value C(account). The return value C(account) of command C(get)
              can be passed as it is, for example to create a user with the same settings as another user.
            - The items of the return value C(account_info) (for example C(UserName), C(Id) and C(SnmpV3.AccessType))
              cannot be given. They are rejected as unsupported parameters.
        required:    false
        suboptions:
            Description:
                type:        str
                description: Description of the user.
            Enabled:
                type:        bool
                description:
                    - Whether the user may use Redfish and the Web UI
                      (Web UI 'Redfish/Web UI user enabled').
                    - This is not whether the user itself is enabled. See C(BaseValues.Enabled).
            RoleId:
                type:        str
                description: Redfish role of the user.
                choices:     ['Administrator', 'Operator', 'ReadOnly']
            PasswordChangeRequired:
                type:        bool
                description: Whether the user has to change the password at the next login.
            BaseValues:
                type:        dict
                description: Basic settings of the user.
                suboptions:
                    Enabled:
                        type:        bool
                        description: Whether the user is enabled (Web UI 'Enable user').
                    Shell:
                        type:        str
                        description: Shell of the user for text access.
                        choices:     ['RemoteManager', 'None']
            Permissions:
                type:        dict
                description: IPMI and other permissions of the user.
                suboptions:
                    Standard:
                        type:        dict
                        description: IPMI channel privileges.
                        suboptions:
                            Lan:
                                type:        str
                                description: Privilege for the LAN channel.
                                choices:     ['Administrator', 'Operator', 'User', 'Oem', 'Callback', 'NoAccess']
                            Serial:
                                type:        str
                                description: Privilege for the serial channel.
                                choices:     ['Administrator', 'Operator', 'User', 'Oem', 'Callback', 'NoAccess']
                    Extended:
                        type:        dict
                        description: Extended permissions.
                        suboptions:
                            ConfigureUsers:
                                type:        bool
                                description: Whether the user may configure user accounts.
                            ConfigureIrmc:
                                type:        bool
                                description: Whether the user may configure iRMC settings.
                            UseVideoRedirection:
                                type:        bool
                                description: Whether the user may use the video redirection (AVR).
                            UseRemoteStorage:
                                type:        bool
                                description: Whether the user may use the remote storage.
            SnmpV3:
                type:        dict
                description:
                    - SNMPv3 settings of the user.
                    - SNMP has to be enabled for the whole iRMC (Web UI 'Services > SNMP'),
                      otherwise the iRMC rejects the change.
                suboptions:
                    ServiceEnabled:
                        type:        bool
                        description: Whether SNMPv3 is enabled for the user.
                    AuthPrivType:
                        type:        str
                        description:
                            - Authentication and privacy protocols.
                            - Can be changed only while SNMPv3 is enabled for the user.
                              The iRMC resets it to C(SHA256_AES) when SNMPv3 is disabled.
                              Therefore only C(SHA256_AES) can be given together with C(ServiceEnabled=false).
                        choices:
                            - SHA256_AES
                            - SHA384_AES
                            - SHA512_AES
                            - SHA256_DES
                            - SHA384_DES
                            - SHA512_DES
            Email:
                type:        dict
                description: Email alerting settings of the user.
                suboptions:
                    AlertChassisEventsUser:
                        type:        bool
                        description:
                            - Whether email alerting is enabled for the user (Web UI 'Enable email alerting').
                            - In the iRMC Redfish interface, the values of C(AlertChassisEventsUser) and
                              C(PagingEnabled) are swapped.
                              This module uses the names of the Redfish interface as they are.
                    PagingEnabled:
                        type:        bool
                        description:
                            - Not shown in the Web UI. See C(AlertChassisEventsUser).
                    Address:
                        type:        str
                        description: Email address of the user.
                    Layout:
                        type:        str
                        description: Format of the email. C(REMCS) is the 'SMS format' in the Web UI.
                        choices:     ['Standard', 'ITS', 'REMCS', 'FixedSubject']
                    PreferredMailServer:
                        type:        str
                        description: Mail server to be used.
                        choices:     ['Auto', 'Primary', 'Secondary']
                    SendEncryptedAlerts:
                        type:        bool
                        description: Whether the email is encrypted with the S/MIME certificate of the user.
                    AttachSystemReport:
                        type:        bool
                        description: Whether the system report is attached to the email.
                    ExtraSubjectEnabled:
                        type:        bool
                        description: Whether C(ExtraSubject) is added to the subject of the email.
                    ExtraSubject:
                        type:        str
                        description: Text added to the subject of the email.
                    AlertFilter:
                        type:        dict
                        description:
                            - Severity of the events which are sent to the user, per component.
                            - C(Spare) is not shown in the Web UI.
                        suboptions:
                            Fans:
                                type:        str
                                description: Fan sensors.
                                choices:     ['None', 'Critical', 'Warning', 'All']
                            Temperature:
                                type:        str
                                description: Temperature sensors.
                                choices:     ['None', 'Critical', 'Warning', 'All']
                            Hardware:
                                type:        str
                                description: Critical hardware errors.
                                choices:     ['None', 'Critical', 'Warning', 'All']
                            SystemHang:
                                type:        str
                                description: System hang.
                                choices:     ['None', 'Critical', 'Warning', 'All']
                            Post:
                                type:        str
                                description: POST errors.
                                choices:     ['None', 'Critical', 'Warning', 'All']
                            Security:
                                type:        str
                                description: Security.
                                choices:     ['None', 'Critical', 'Warning', 'All']
                            SystemStatus:
                                type:        str
                                description: System status.
                                choices:     ['None', 'Critical', 'Warning', 'All']
                            Harddisk:
                                type:        str
                                description: Disk drivers and controllers.
                                choices:     ['None', 'Critical', 'Warning', 'All']
                            NetworkError:
                                type:        str
                                description: Network interface.
                                choices:     ['None', 'Critical', 'Warning', 'All']
                            RemoteManagement:
                                type:        str
                                description: Remote management.
                                choices:     ['None', 'Critical', 'Warning', 'All']
                            PowerSupply:
                                type:        str
                                description: System power.
                                choices:     ['None', 'Critical', 'Warning', 'All']
                            Spare:
                                type:        str
                                description: Spare (not shown in the Web UI).
                                choices:     ['None', 'Critical', 'Warning', 'All']
                            Memory:
                                type:        str
                                description: Memory.
                                choices:     ['None', 'Critical', 'Warning', 'All']
                            Others:
                                type:        str
                                description: Other events.
                                choices:     ['None', 'Critical', 'Warning', 'All']
            TwoFactorAuth:
                type:        dict
                description: Two-factor authentication settings of the user (C(2FAuth) in the Redfish interface).
                suboptions:
                    Enabled:
                        type:        bool
                        description: Whether two-factor authentication is enabled for the user.
    ssh_public_key_path:
        type:        str
        description:
            - Path to the file containing the SSHv2 public key of the user (OpenSSH format).
            - The key is registered only if its fingerprint differs from the registered one.
              The iRMC calculates the fingerprint by MD5 or, depending on the iRMC generation,
              by the first 16 bytes of SHA-256. Both are compared.
        required:    false
    smime_certificate_path:
        type:        str
        description:
            - Path to the file containing the S/MIME certificate of the user (PEM format).
            - The certificate is registered only if its SHA1 fingerprint differs from the registered one.
        required:    false

notes:
    - Command C(set) creates the user with C(name), C(password), C(account.RoleId), C(account.Description)
      and C(account.Enabled), and then changes the other given settings.
    - The password is changed after all the other settings. If the module logs in as the user whose password is changed
      (C(irmc_username) equals C(name)), the module sends no more requests after the password is changed.
    - Registered SSH public keys and S/MIME certificates cannot be removed with this module.
    - When a user is copied by passing the return value C(account) to another user (including export to a file and
      import from it), only the settings in C(account) are copied. The information in C(account_info),
      the SSH public key and the S/MIME certificate are not copied.
    - The values of the iRMC Redfish interface are used as they are. They differ from the deprecated module 'irmc_user'
      (for example C(Oem) instead of C(OEM), C(REMCS) instead of C(SMS)).
    - The parameters of the deprecated module 'irmc_user' correspond as follows.
      See docs/MODULE_MIGRATION_GUIDE.md of this collection for details.
    - C(command) C(create) / C(change) -> C(set). C(description) -> C(account.Description).
      C(enabled) -> C(account.BaseValues.Enabled). C(redfish_enabled) -> C(account.Enabled).
      C(redfish_role) -> C(account.RoleId).
    - C(lan_privilege) / C(serial_privilege) -> C(account.Permissions.Standard.Lan) / C(Serial) (C(OEM) is C(Oem)).
      C(config_user_enabled) / C(config_bmc_enabled) / C(avr_enabled) / C(storage_enabled)
      -> C(account.Permissions.Extended.ConfigureUsers) / C(ConfigureIrmc) / C(UseVideoRedirection)
      / C(UseRemoteStorage).
      C(shell) -> C(account.BaseValues.Shell) (C(Remote Manager) is C(RemoteManager)).
    - C(snmpv3_enabled) -> C(account.SnmpV3.ServiceEnabled).
      C(snmpv3_auth) and C(snmpv3_privacy) -> C(account.SnmpV3.AuthPrivType).
      C(snmpv3_access) cannot be changed (C(account_info.SnmpV3.AccessType)).
    - C(ssh_public_key) -> C(ssh_public_key_path). C(ssh_certificate) -> C(smime_certificate_path).
    - C(email_enabled) -> C(account.Email.AlertChassisEventsUser).
      C(email_encrypted) -> C(account.Email.SendEncryptedAlerts).
      C(email_type) -> C(account.Email.Layout) (C(ITS-Format) is C(ITS), C(Fixed Subject) is C(FixedSubject),
      C(SMS) is C(REMCS)). C(email_server) -> C(account.Email.PreferredMailServer) (C(Automatic) is C(Auto)).
      C(email_address) -> C(account.Email.Address).
    - C(alert_*) -> C(account.Email.AlertFilter.*). C(alert_fans) -> C(Fans), C(alert_temperatures) -> C(Temperature),
      C(alert_hwerrors) -> C(Hardware), C(alert_syshang) -> C(SystemHang), C(alert_posterrors) -> C(Post),
      C(alert_security) -> C(Security), C(alert_sysstatus) -> C(SystemStatus), C(alert_hderrors) -> C(Harddisk),
      C(alert_network) -> C(NetworkError), C(alert_remote) -> C(RemoteManagement), C(alert_power) -> C(PowerSupply),
      C(alert_memory) -> C(Memory), C(alert_others) -> C(Others).
'''

EXAMPLES = r'''
# Get user account data
- name: Get and show user account
  tags:
    - get
  block:
    - name: Get user account
      fsas.primergy.irmc_account:
        irmc_url: "{{ inventory_hostname }}"
        irmc_username: "{{ irmc_user }}"
        irmc_password: "{{ irmc_password }}"
        validate_certs: "{{ validate_certificate }}"
        command: "get"
        name: "{{ username | default('ansibleuser') }}"
      register: user
      delegate_to: localhost
    - name: Show user account
      ansible.builtin.debug:
        msg:
          account: "{{ user.account }}"
          account_info: "{{ user.account_info }}"

# Create the user account if it does not exist, and change only the settings which differ
#   'username' and 'password' have no default, so that a user is not created with a default password
- name: Create or change user account
  fsas.primergy.irmc_account:
    irmc_url: "{{ inventory_hostname }}"
    irmc_username: "{{ irmc_user }}"
    irmc_password: "{{ irmc_password }}"
    validate_certs: "{{ validate_certificate }}"
    command: "set"
    name: "{{ username }}"
    password: "{{ password }}"
    account:
      Description: "{{ description | default('ansible user description') }}"
      Enabled: true
      RoleId: "Operator"
      BaseValues:
        Enabled: true
      Permissions:
        Standard:
          Lan: "Operator"
          Serial: "Operator"
  delegate_to: localhost
  tags:
    - set

# Create or change user account, with all parameters given by variables
# Only the given variables are passed to the module, e.g.
#   --tags set_all -e role_id=ReadOnly -e email_address=user@example.com
# The variable names are the keys of 'account' in snake case
# (prefixed with 'email_' for 'Email', and 'email_alert_' for 'Email.AlertFilter').
# Some of them follow the parameter names of the deprecated module 'irmc_user'
# (redfish_enabled, enabled, lan_privilege, serial_privilege, snmpv3_enabled).
# Note: 'AlertChassisEventsUser' is 'Enable email alerting' in the Web UI.
- name: Create or change user account with all parameters
  fsas.primergy.irmc_account:
    irmc_url: "{{ inventory_hostname }}"
    irmc_username: "{{ irmc_user }}"
    irmc_password: "{{ irmc_password }}"
    validate_certs: "{{ validate_certificate }}"
    command: "set"
    name: "{{ username | default('ansibleuser') }}"
    password: "{{ password | default(omit) }}"
    account:
      Description: "{{ description | default(omit) }}"
      Enabled: "{{ redfish_enabled | default(omit) }}"
      RoleId: "{{ role_id | default(omit) }}"
      PasswordChangeRequired: "{{ password_change_required | default(omit) }}"
      BaseValues:
        Enabled: "{{ enabled | default(omit) }}"
        Shell: "{{ shell | default(omit) }}"
      Permissions:
        Standard:
          Lan: "{{ lan_privilege | default(omit) }}"
          Serial: "{{ serial_privilege | default(omit) }}"
        Extended:
          ConfigureUsers: "{{ configure_users | default(omit) }}"
          ConfigureIrmc: "{{ configure_irmc | default(omit) }}"
          UseVideoRedirection: "{{ use_video_redirection | default(omit) }}"
          UseRemoteStorage: "{{ use_remote_storage | default(omit) }}"
      SnmpV3:
        ServiceEnabled: "{{ snmpv3_enabled | default(omit) }}"
        AuthPrivType: "{{ snmpv3_auth_priv_type | default(omit) }}"
      Email:
        AlertChassisEventsUser: "{{ email_alert_chassis_events_user | default(omit) }}"
        PagingEnabled: "{{ email_paging_enabled | default(omit) }}"
        Address: "{{ email_address | default(omit) }}"
        Layout: "{{ email_layout | default(omit) }}"
        PreferredMailServer: "{{ email_preferred_mail_server | default(omit) }}"
        SendEncryptedAlerts: "{{ email_send_encrypted_alerts | default(omit) }}"
        AttachSystemReport: "{{ email_attach_system_report | default(omit) }}"
        ExtraSubjectEnabled: "{{ email_extra_subject_enabled | default(omit) }}"
        ExtraSubject: "{{ email_extra_subject | default(omit) }}"
        AlertFilter:
          Fans: "{{ email_alert_fans | default(omit) }}"
          Temperature: "{{ email_alert_temperature | default(omit) }}"
          Hardware: "{{ email_alert_hardware | default(omit) }}"
          SystemHang: "{{ email_alert_system_hang | default(omit) }}"
          Post: "{{ email_alert_post | default(omit) }}"
          Security: "{{ email_alert_security | default(omit) }}"
          SystemStatus: "{{ email_alert_system_status | default(omit) }}"
          Harddisk: "{{ email_alert_harddisk | default(omit) }}"
          NetworkError: "{{ email_alert_network_error | default(omit) }}"
          RemoteManagement: "{{ email_alert_remote_management | default(omit) }}"
          PowerSupply: "{{ email_alert_power_supply | default(omit) }}"
          Spare: "{{ email_alert_spare | default(omit) }}"
          Memory: "{{ email_alert_memory | default(omit) }}"
          Others: "{{ email_alert_others | default(omit) }}"
      TwoFactorAuth:
        Enabled: "{{ two_factor_auth_enabled | default(omit) }}"
    ssh_public_key_path: "{{ ssh_public_key_path | default(omit) }}"
    smime_certificate_path: "{{ smime_certificate_path | default(omit) }}"
  delegate_to: localhost
  tags:
    - set_all

# Create or change a user account with the same settings as another user account
#   Only 'account' (the settings) is copied. 'account_info' (e.g. SnmpV3.AccessType),
#   the SSH public key and the S/MIME certificate are not copied.
#   'new_username' and 'new_password' have no default, so that a user is not created with a default password
- name: Copy user account
  tags:
    - copy
  block:
    - name: Get settings of the source user
      fsas.primergy.irmc_account:
        irmc_url: "{{ inventory_hostname }}"
        irmc_username: "{{ irmc_user }}"
        irmc_password: "{{ irmc_password }}"
        validate_certs: "{{ validate_certificate }}"
        command: "get"
        name: "{{ username | default('ansibleuser') }}"
      register: source
      delegate_to: localhost
    - name: Create or change the new user with the same settings
      fsas.primergy.irmc_account:
        irmc_url: "{{ inventory_hostname }}"
        irmc_username: "{{ irmc_user }}"
        irmc_password: "{{ irmc_password }}"
        validate_certs: "{{ validate_certificate }}"
        command: "set"
        name: "{{ new_username }}"
        password: "{{ new_password }}"
        account: "{{ source.account }}"
      delegate_to: localhost

# Export the settings of a user account to a file in JSON format
#   Only 'account' (the settings) is copied. 'account_info' (e.g. SnmpV3.AccessType),
#   the SSH public key and the S/MIME certificate are not copied.
#   make sure not to overwrite the file 'account_file' if you do not intend to
- name: Export user account to file
  tags:
    - export
  block:
    - name: Get user account
      fsas.primergy.irmc_account:
        irmc_url: "{{ inventory_hostname }}"
        irmc_username: "{{ irmc_user }}"
        irmc_password: "{{ irmc_password }}"
        validate_certs: "{{ validate_certificate }}"
        command: "get"
        name: "{{ username | default('ansibleuser') }}"
      register: user
      delegate_to: localhost
    - name: Write settings of user account to file
      ansible.builtin.copy:
        content: "{{ user.account | to_nice_json }}"
        dest: "{{ account_file }}"
        mode: "0600"
      delegate_to: localhost

# Create or change a user account with the settings in a file exported above
#   'username' and 'password' have no default, so that an existing user is not changed by mistake
- name: Import user account from file
  fsas.primergy.irmc_account:
    irmc_url: "{{ inventory_hostname }}"
    irmc_username: "{{ irmc_user }}"
    irmc_password: "{{ irmc_password }}"
    validate_certs: "{{ validate_certificate }}"
    command: "set"
    name: "{{ username }}"
    password: "{{ password }}"
    account: "{{ lookup('ansible.builtin.file', account_file) | from_json }}"
  delegate_to: localhost
  tags:
    - import

# Delete user account
- name: Delete user account
  fsas.primergy.irmc_account:
    irmc_url: "{{ inventory_hostname }}"
    irmc_username: "{{ irmc_user }}"
    irmc_password: "{{ irmc_password }}"
    validate_certs: "{{ validate_certificate }}"
    command: "delete"
    name: "{{ username }}"
  delegate_to: localhost
  tags:
    - delete
'''

RETURN = r'''
account:
    description:
        - Settings of the user (after the change for command C(set)), in the same structure as the option C(account).
        - Contains only the settings which can be changed with command C(set).
          Therefore it can be passed as it is to the option C(account) of command C(set) for another user,
          for example to copy a user, or to export the settings to a file and import them later.
        - The values are the ones of the iRMC Redfish interface.
    returned: when command is get or set
    type: dict
    sample:
        Description: "ansible user description"
        Enabled: true
        RoleId: Operator
        PasswordChangeRequired: false
        BaseValues: {Enabled: true, Shell: RemoteManager}
        Permissions:
            Standard: {Lan: Operator, Serial: Operator}
            Extended:
                ConfigureUsers: false
                ConfigureIrmc: false
                UseVideoRedirection: false
                UseRemoteStorage: false
        SnmpV3: {ServiceEnabled: false, AuthPrivType: SHA256_AES}
        Email:
            AlertChassisEventsUser: false
            PagingEnabled: true
            Address: "user@example.com"
            Layout: Standard
            PreferredMailServer: Auto
            SendEncryptedAlerts: false
            AttachSystemReport: false
            ExtraSubjectEnabled: false
            ExtraSubject: ""
            AlertFilter:
                Fans: Warning
                Temperature: Warning
                Hardware: All
                SystemHang: Critical
                Post: All
                Security: Warning
                SystemStatus: None
                Harddisk: Critical
                NetworkError: Warning
                RemoteManagement: Critical
                PowerSupply: Warning
                Spare: None
                Memory: Critical
                Others: None
        TwoFactorAuth: {Enabled: false}
account_info:
    description:
        - Information of the user which cannot be changed with this module (after the change for command C(set)),
          such as the identity of the user, its state,
          and the values which are read-only in the iRMC Redfish interface.
        - It cannot be passed to the option C(account), and it is not copied when C(account) is passed to another user.
          It is separated from C(account) so that the identity of the user (C(UserName), C(Id)) is not copied
          to another user by mistake.
        - The values are the ones of the iRMC Redfish interface.
    returned: when command is get or set
    type: dict
    contains:
        Id:
            description: Id of the account resource. Identifies the user in the iRMC.
            returned: always
            type: str
            sample: "3"
        UserName:
            description: Name of the user. Use the option C(name) to specify the user.
            returned: always
            type: str
            sample: ansibleuser
        Locked:
            description: Whether the user is locked out because of failed logins.
            returned: always
            type: bool
            sample: false
        SNMPPasswordRequirement:
            description: Whether the password meets the requirement of SNMPv3.
            returned: always
            type: bool
            sample: true
        SSHv2KeyFingerprint:
            description:
                - Type, size and fingerprint of the registered SSHv2 public key. C(null) if not registered.
                - The fingerprint is the MD5 of the key, or the first 16 bytes of the SHA-256 of the key,
                  depending on the iRMC generation (the former for M7 and earlier, the latter for M8 and later).
                - The key is registered with the option C(ssh_public_key_path). The key itself cannot be read
                  from the iRMC, so it is not copied to another user.
            returned: always
            type: str
            sample: "RSA 4096 e9:a4:db:62:86:6f:67:d4:2b:04:b7:68:47:df:08:5e:"
        SMIMECertificate:
            description:
                - Information of the registered S/MIME certificate. C(null) if not registered.
                - The certificate is registered with the option C(smime_certificate_path). The certificate itself
                  cannot be read from the iRMC, so it is not copied to another user.
            returned: always
            type: dict
            sample:
                SHA1FingerPrint: "22:a8:b7:92:7a:be:ba:a4:e9:77:31:85:98:5b:75:9a:c7:f6:dc:1d"
                ValidFrom: "2026-10-18T04:37:04+00:00"
                ValidTo: "2027-10-18T04:37:04+00:00"
                IssuedTo: {CommonName: alert-user, Email: alert-user@example.com}
        SnmpV3:
            description: Read-only SNMPv3 information.
            returned: always
            type: dict
            contains:
                AccessType:
                    description:
                        - Access type of the user for SNMPv3.
                        - It cannot be changed via the iRMC Redfish interface,
                          even while SNMPv3 is enabled for the user.
                          The Web UI offers only 'Read only'.
                        - The iRMC may keep a value set before (for example by the deprecated module 'irmc_user')
                          even after the user is deleted and created again. Therefore it may differ from the user
                          whose settings were copied.
                    returned: always
                    type: str
                    sample: ReadOnly
        TwoFactorAuth:
            description: Read-only two-factor authentication information (C(2FAuth) in the Redfish interface).
            returned: always
            type: dict
            contains:
                Configured:
                    description: Whether two-factor authentication has been configured for the user.
                    returned: always
                    type: bool
                    sample: false
'''


import base64
import binascii
import hashlib
import ntpath
import re
import traceback
from typing import Any, Callable, Mapping

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

SERVICE_ROOT_PATH = '/redfish/v1'

SEVERITIES = ['None', 'Critical', 'Warning', 'All']
PRIVILEGES = ['Administrator', 'Operator', 'User', 'Oem', 'Callback', 'NoAccess']

# account パラメータの argument_spec
# get の出力（account）もこの構造に合わせて作るので、そのまま set に渡せる
ACCOUNT_OPTIONS = dict(
    Description=dict(type='str'),
    Enabled=dict(type='bool'),
    RoleId=dict(type='str', choices=['Administrator', 'Operator', 'ReadOnly']),
    PasswordChangeRequired=dict(type='bool', no_log=False),
    BaseValues=dict(type='dict', options=dict(
        Enabled=dict(type='bool'),
        Shell=dict(type='str', choices=['RemoteManager', 'None']),
    )),
    Permissions=dict(type='dict', options=dict(
        Standard=dict(type='dict', options=dict(
            Lan=dict(type='str', choices=PRIVILEGES),
            Serial=dict(type='str', choices=PRIVILEGES),
        )),
        Extended=dict(type='dict', options=dict(
            ConfigureUsers=dict(type='bool'),
            ConfigureIrmc=dict(type='bool'),
            UseVideoRedirection=dict(type='bool'),
            UseRemoteStorage=dict(type='bool'),
        )),
    )),
    SnmpV3=dict(type='dict', options=dict(
        ServiceEnabled=dict(type='bool'),
        AuthPrivType=dict(type='str', choices=['SHA256_AES', 'SHA384_AES', 'SHA512_AES',
                                               'SHA256_DES', 'SHA384_DES', 'SHA512_DES']),
    )),
    Email=dict(type='dict', options=dict(
        AlertChassisEventsUser=dict(type='bool'),
        PagingEnabled=dict(type='bool'),
        Address=dict(type='str'),
        Layout=dict(type='str', choices=['Standard', 'ITS', 'REMCS', 'FixedSubject']),
        PreferredMailServer=dict(type='str', choices=['Auto', 'Primary', 'Secondary']),
        SendEncryptedAlerts=dict(type='bool'),
        AttachSystemReport=dict(type='bool'),
        ExtraSubjectEnabled=dict(type='bool'),
        ExtraSubject=dict(type='str'),
        AlertFilter=dict(type='dict', options={
            name: dict(type='str', choices=SEVERITIES)
            for name in ('Fans', 'Temperature', 'Hardware', 'SystemHang', 'Post', 'Security', 'SystemStatus',
                         'Harddisk', 'NetworkError', 'RemoteManagement', 'PowerSupply', 'Spare', 'Memory', 'Others')
        }),
    )),
    TwoFactorAuth=dict(type='dict', options=dict(
        Enabled=dict(type='bool'),
    )),
)

# Account リソースの直下（Oem の外）にある項目
STANDARD_KEYS = ('Description', 'Enabled', 'RoleId', 'PasswordChangeRequired')

# Oem.{vendor} の中の項目のうち、モジュールで名前を変えるもの（モジュールでの名前 -> Redfish での名前）
# "2FAuth" は数字で始まり、Ansible のオプション名・戻り値のキーに使えないため
OEM_RENAMES = {'TwoFactorAuth': '2FAuth'}

# ユーザーを作成するときに POST で送れる項目（ManagerAccount の標準の項目）
CREATE_KEYS = ('RoleId', 'Description', 'Enabled')

# 現在と同じパスワードを送ったときに iRMC が返すステータス（M7以前の世代は500、M8以降の世代は400）
SAME_PASSWORD_STATUSES = (400, 500)

# SNMPv3 を無効にすると、iRMC は AuthPrivType をこの値に戻す
SNMPV3_DISABLED_AUTH_PRIV_TYPE = 'SHA256_AES'

UPLOAD_CONTENT_TYPE = 'application/octet-stream'

# SSHv2KeyFingerprint のフィンガープリントの部分（16バイトを':'で区切ったもの）
SSH_FINGERPRINT_PATTERN = re.compile(r'[0-9a-f]{2}(?::[0-9a-f]{2}){15}')


def _ssh_public_key_blob(public_key: str) -> bytes:
    """OpenSSH形式の公開鍵から、鍵のデータ（base64をデコードしたもの）を取り出します。

    引数:
        public_key - OpenSSH形式の公開鍵（"ssh-rsa AAAA... comment"）

    戻り値:
        鍵のデータ

    例外:
        ValueError - 公開鍵の形式が正しくない場合
    """
    fields = public_key.split()
    if len(fields) < 2:
        raise ValueError('Not an OpenSSH public key (expected "<type> <base64> [comment]")')
    try:
        return base64.b64decode(fields[1], validate=True)
    except (binascii.Error, ValueError) as e:
        raise ValueError(f'Public key is not valid base64: {e}') from e


def _colon_hex(digest: str) -> str:
    """16進数の文字列を、2文字ずつ':'で区切ります。"""
    return ':'.join(digest[i:i + 2] for i in range(0, len(digest), 2))


def ssh_public_key_md5_fingerprint(public_key: str) -> str:
    """OpenSSH形式の公開鍵からMD5フィンガープリントを計算します。

    'ssh-keygen -l -E md5' の値（'MD5:' を除いたもの）と同じです。

    引数:
        public_key - OpenSSH形式の公開鍵（"ssh-rsa AAAA... comment"）

    戻り値:
        MD5フィンガープリント（小文字16進数の':'区切り）

    例外:
        ValueError - 公開鍵の形式が正しくない場合
    """
    # 鍵の識別に使うもので、セキュリティ目的のハッシュではない
    return _colon_hex(hashlib.md5(_ssh_public_key_blob(public_key), usedforsecurity=False).hexdigest())


def ssh_public_key_irmc_fingerprints(public_key: str) -> tuple[str, str]:
    """iRMCがSSHv2KeyFingerprintとして返しうるフィンガープリントを、公開鍵から計算します。

    iRMCの世代で計算方法が違うため、両方を返します（実機で確認）。
        M7以前の世代(ts_fujitsu): 鍵のデータのMD5
        M8以降の世代(Fsas):       鍵のデータのSHA-256の先頭16バイト（表示の形はMD5と同じ）

    引数:
        public_key - OpenSSH形式の公開鍵（"ssh-rsa AAAA... comment"）

    戻り値:
        (MD5, SHA-256の先頭16バイト)。どちらも小文字16進数の':'区切り

    例外:
        ValueError - 公開鍵の形式が正しくない場合
    """
    blob = _ssh_public_key_blob(public_key)
    return (
        _colon_hex(hashlib.md5(blob, usedforsecurity=False).hexdigest()),
        _colon_hex(hashlib.sha256(blob).hexdigest()[:32]),
    )


def project(data: Any, options: Mapping[str, Any]) -> dict:
    """argument_specの構造に合わせて、データから該当する項目だけを取り出します。

    引数:
        data - 取り出し元のデータ（dict以外なら空のdictを返す）
        options - argument_specのoptions

    戻り値:
        optionsにある項目だけを持つdict（データに無い項目は含まない）
    """
    if not isinstance(data, dict):
        return {}
    result = {}
    for name, spec in options.items():
        if name not in data:
            continue
        if spec.get('type') == 'dict':
            result[name] = project(data[name], spec['options'])
        else:
            result[name] = data[name]
    return result


def diff(desired: Mapping[str, Any], current: Any) -> dict:
    """指定された値のうち、現在の値と異なるものを返します。

    Noneの項目は指定されていないものとして扱います。

    引数:
        desired - 指定された値（入れ子のdict）
        current - 現在の値（入れ子のdict）

    戻り値:
        現在の値と異なる項目だけを持つ入れ子のdict
    """
    current = current if isinstance(current, dict) else {}
    result = {}
    for name, value in desired.items():
        if value is None:
            continue
        if isinstance(value, dict):
            sub = diff(value, current.get(name))
            if sub:
                result[name] = sub
        elif current.get(name) != value:
            result[name] = value
    return result


class AccountController:
    """iRMCのローカルユーザーアカウントを管理するControllerクラスです。
    """

    def __init__(self, irmc: iRMC, logger: Logger, irmc_factory: Callable[[str, str], iRMC]):
        """AccountControllerを初期化します。

        引数:
            irmc - iRMCクライアントインスタンス
            logger - ログ出力用のLoggerインスタンス
            irmc_factory - ユーザー名とパスワードから別のiRMCクライアントを作る関数
                           （パスワードが変わっていないことをログインで確かめるために使う）
        """
        self.irmc = irmc
        self.logger = logger
        self.irmc_factory = irmc_factory
        # エラーメッセージから伏せる文字列（iRMCのエラーメッセージは送った値をそのまま含むことがある）
        self._secrets: list[str] = []

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

    def _error(self, response: Any, changed: list[str] | None = None) -> HttpError:
        """失敗したレスポンスからHttpErrorを作ります。

        引数:
            response - 失敗したレスポンス
            changed - これまでに変更済みの内容（失敗時のメッセージに使用）

        戻り値:
            HttpError
        """
        body = response.body
        error_message = None
        if isinstance(body, dict):
            # ExtendedInfo の Message の方が具体的（例: 409 のときの SNMPv3 の前提条件）
            infos = dig(body, 'error', '@Message.ExtendedInfo', default=None)
            if isinstance(infos, list) and infos and isinstance(infos[0], dict):
                error_message = infos[0].get('Message')
            error_message = error_message or dig(body, 'error', 'message')
        msg = f"Failed to {response.request.method} {response.request.path}: {error_message or body}"
        # 例: "The value <パスワード> for the property Password exceeds allowed range or size"
        # module.warn() の出力は Ansible の no_log で伏せられないので、ここで伏せる
        for secret in self._secrets:
            msg = msg.replace(secret, '********')
        # 1回のsetで複数のリクエストを送るため、途中で失敗すると一部だけ変更された状態になる
        if changed:
            msg += f" (already changed: {', '.join(changed)})"
        self.logger.warn(msg)
        return HttpError(msg, status=response.status)

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
        if response.status != 200 or not isinstance(response.body, dict):
            raise self._error(response)
        return response.body

    def _accounts_path(self) -> str:
        """アカウントのコレクションのパスを返します。

        戻り値:
            アカウントのコレクションのパス

        例外:
            HttpError - HTTPリクエストが失敗した場合
            ModuleError - リンクが見つからない場合
        """
        # 以下のリンクを辿る
        #   GET /redfish/v1
        #     -> .AccountService."@odata.id" (/redfish/v1/AccountService)
        #   GET /redfish/v1/AccountService
        #     -> .Accounts."@odata.id" (/redfish/v1/AccountService/Accounts)
        service_path = dig(self._fetch(SERVICE_ROOT_PATH), 'AccountService', '@odata.id')
        if not service_path:
            raise ModuleError(f"'AccountService' link not found in {SERVICE_ROOT_PATH}")
        accounts_path = dig(self._fetch(service_path), 'Accounts', '@odata.id')
        if not accounts_path:
            raise ModuleError(f"'Accounts' link not found in {service_path}")
        return accounts_path

    def _find(self, name: str) -> tuple[str, dict] | None:
        """ユーザー名からアカウントを探します。

        引数:
            name - ユーザー名

        戻り値:
            (アカウントのパス, アカウントのリソース)。見つからなければNone

        例外:
            HttpError - HTTPリクエストが失敗した場合
            ModuleError - リンクが見つからない場合
        """
        # コレクションはユーザー名を持たないので、メンバーを順に取得して探す
        #   GET /redfish/v1/AccountService/Accounts
        #     -> .Members[]."@odata.id" (/redfish/v1/AccountService/Accounts/{id})
        for member in dig(self._fetch(self._accounts_path()), 'Members', default=None) or []:
            path = dig(member, '@odata.id')
            if not path:
                continue
            body = self._fetch(path)
            if body.get('UserName') == name:
                return path, body
        return None

    def _to_module(self, body: Mapping[str, Any]) -> dict:
        """Accountリソースを、モジュールの構造（Oem.{vendor}の中身を1段上に出したもの）に変換します。

        引数:
            body - Accountリソース

        戻り値:
            モジュールの構造に変換したもの（全項目）
        """
        data = dict(body)
        oem = dig(body, 'Oem', self._vendor(), default=None)
        if isinstance(oem, dict):
            renamed = {redfish: module for module, redfish in OEM_RENAMES.items()}
            data.update({renamed.get(key, key): value for key, value in oem.items()})
        data.pop('Oem', None)
        return data

    def _to_redfish(self, changes: Mapping[str, Any]) -> dict:
        """モジュールの構造の変更内容を、AccountリソースのPATCHのボディに変換します。

        引数:
            changes - モジュールの構造の変更内容

        戻り値:
            PATCHのボディ（OEMの項目はOem.{vendor}の中に入れる）
        """
        body = {key: value for key, value in changes.items() if key in STANDARD_KEYS}
        oem = {OEM_RENAMES.get(key, key): value for key, value in changes.items() if key not in STANDARD_KEYS}
        if oem:
            body['Oem'] = {self._vendor(): oem}
        return body

    def _account(self, body: Mapping[str, Any]) -> dict:
        """Accountリソースから、戻り値のaccount（設定値）を作ります。

        引数:
            body - Accountリソース

        戻り値:
            accountパラメータと同じ構造の設定値
        """
        return project(self._to_module(body), ACCOUNT_OPTIONS)

    def _account_info(self, body: Mapping[str, Any]) -> dict:
        """Accountリソースから、戻り値のaccount_info（読み取り専用の情報）を作ります。

        引数:
            body - Accountリソース

        戻り値:
            読み取り専用の情報
        """
        data = self._to_module(body)
        return remove_odata_keys({
            'Id': data.get('Id'),
            'UserName': data.get('UserName'),
            'Locked': data.get('Locked'),
            'SNMPPasswordRequirement': data.get('SNMPPasswordRequirement'),
            'SSHv2KeyFingerprint': data.get('SSHv2KeyFingerprint'),
            'SMIMECertificate': data.get('SMIMECertificate'),
            'SnmpV3': {'AccessType': dig(data, 'SnmpV3', 'AccessType')},
            'TwoFactorAuth': {'Configured': dig(data, 'TwoFactorAuth', 'Configured')},
        })

    def _result(self, path: str) -> dict:
        """アカウントを取得し、戻り値（account / account_info）にまとめます。

        引数:
            path - アカウントのパス

        戻り値:
            account / account_info を持つdict

        例外:
            HttpError - HTTPリクエストが失敗した場合
            ModuleError - iRMCのベンダーを判別できない場合
        """
        body = self._fetch(path)
        return {'account': self._account(body), 'account_info': self._account_info(body)}

    def _check_snmpv3(self, desired: Mapping[str, Any], current: Mapping[str, Any], changes: dict) -> None:
        """SNMPv3の指定を検証し、無効にする場合はAuthPrivTypeを変更内容から外します。

        iRMCは、SNMPv3が無効なユーザーのAuthPrivTypeを変更できず（409）、無効にするとSHA256_AESに戻します。
        また、無効化とAuthPrivTypeの変更を1回で送ると409になるのに、AuthPrivTypeだけが反映されます。

        引数:
            desired - 指定された値（モジュールの構造）
            current - 現在の値（モジュールの構造）
            changes - 変更内容（必要ならSnmpV3.AuthPrivTypeを取り除く）

        例外:
            ValidationError - SNMPv3が無効になるのに、SHA256_AES以外のAuthPrivTypeが指定された場合
        """
        enabled = dig(desired, 'SnmpV3', 'ServiceEnabled')
        if enabled is None:
            enabled = dig(current, 'SnmpV3', 'ServiceEnabled')
        if enabled is not False:
            return

        auth_priv_type = dig(desired, 'SnmpV3', 'AuthPrivType')
        if auth_priv_type not in (None, SNMPV3_DISABLED_AUTH_PRIV_TYPE):
            raise ValidationError(
                f"'SnmpV3.AuthPrivType' can be {auth_priv_type!r} only while 'SnmpV3.ServiceEnabled' is true "
                f"(the iRMC resets it to {SNMPV3_DISABLED_AUTH_PRIV_TYPE!r} when SNMPv3 is disabled)"
            )
        snmpv3 = changes.get('SnmpV3')
        if snmpv3:
            snmpv3.pop('AuthPrivType', None)
            if not snmpv3:
                del changes['SnmpV3']

    def _patch(self, path: str, body: dict) -> Any:
        """AccountリソースをPATCHします（ETagをIf-Matchに付ける）。

        ステータスの確認は呼び出し側で行います（パスワードの変更では500を特別に扱うため）。

        引数:
            path - アカウントのパス
            body - PATCHのボディ

        戻り値:
            レスポンス
        """
        response = self.irmc.get(path)
        etag = dig(response.body, '@odata.etag') if isinstance(response.body, dict) else None
        etag = etag or response.headers.get('ETag')
        headers = {'If-Match': str(etag)} if etag else None
        self.logger.debug(f"Patching {', '.join(body)} of {path}")
        return self.irmc.patch(path, body, headers=headers)

    def _create(self, params: Mapping[str, Any], desired: Mapping[str, Any]) -> str:
        """ユーザーを作成します。

        引数:
            params - パラメータ辞書（name / password）
            desired - 指定された値（モジュールの構造）

        戻り値:
            作成したアカウントのパス

        例外:
            ValidationError - passwordが指定されていない場合
            HttpError - HTTPリクエストが失敗した場合
            ModuleError - 作成したアカウントのパスが分からない場合
        """
        if not params.get('password'):
            raise ValidationError(f"'password' is required to create the user {params['name']!r}")
        body = {'UserName': params['name'], 'Password': params['password']}
        body.update({key: desired[key] for key in CREATE_KEYS if desired.get(key) is not None})

        response = self.irmc.post(self._accounts_path(), body)
        if response.status not in (200, 201):
            raise self._error(response)
        path = response.headers.get('Location') or dig(response.body, '@odata.id')
        if not path:
            raise ModuleError(f"Could not find the path of the created user {params['name']!r}")
        self.logger.log(f"User {params['name']!r} created: {path}")
        return path

    def _change_password(self, path: str, params: Mapping[str, Any], changed: list[str]) -> bool:
        """パスワードを変更します。

        iRMCは現在と同じパスワードを拒否します（返すステータスは世代で違い、M7以前は500、M8以降は400）。
        そのため400と500のときは、そのユーザーとしてログインできるかで、同じパスワードかどうかを確かめます。
        ログインできなければ、iRMCのエラーをそのまま返します（パスワードの規則に合わないときなど）。

        引数:
            path - アカウントのパス
            params - パラメータ辞書（name / password）
            changed - これまでに変更済みの内容（失敗時のメッセージに使用）

        戻り値:
            変更した場合はTrue、現在と同じパスワードだった場合はFalse

        例外:
            HttpError - パスワードの変更に失敗し、同じパスワードであることも確かめられなかった場合
        """
        # 同じパスワードだとPATCH全体が捨てられるので、他の項目とは別に送る
        response = self._patch(path, {'Password': params['password']})
        if response.status in (200, 204):
            return True
        # 実機の応答:
        #   M7以前の世代(ts_fujitsu): 500 "Accessing property Password failed because of backend error."
        #   M8以降の世代(Fsas):       400 "The same password is already in use."
        if response.status not in SAME_PASSWORD_STATUSES:
            raise self._error(response, changed)

        login = self.irmc_factory(params['name'], params['password']).get(path, use_cache=False)
        if login.status == 200:
            self.logger.debug(f"Password of {params['name']!r} is unchanged (login succeeded)")
            return False
        error = self._error(response, changed)
        error.message += (
            f" (could not confirm that the password is unchanged: login as {params['name']!r} "
            f"returned status {login.status})"
        )
        raise error

    def _upload(self, body: Mapping[str, Any], action: str, file_path: str, content: bytes,
                changed: list[str]) -> None:
        """アカウントのOEMアクションでファイルを登録します。

        引数:
            body - Accountリソース（アクションのパスを取り出す）
            action - アクション名（"AddUserSSHKey" / "AddUserMIMECert"）
            file_path - 登録するファイルのパス
            content - 登録するファイルの内容
            changed - これまでに変更済みの内容（失敗時のメッセージに使用）

        例外:
            HttpError - HTTPリクエストが失敗した場合
            ModuleError - アクションが見つからない場合
        """
        # 以下のリンクを辿る
        #   GET /redfish/v1/AccountService/Accounts/{id}
        #     -> .Actions.Oem."#{oem_prefix}User.{action}".target
        actions = dig(body, 'Actions', 'Oem', default=None) or {}
        target = next((dig(value, 'target') for key, value in actions.items() if key.endswith(f'User.{action}')),
                      None)
        if not target:
            raise ModuleError(f"Action '{action}' not found in {body.get('@odata.id')}")

        self.logger.debug(f"Posting {file_path} to {target}")
        fields = {'data': (ntpath.basename(file_path), content, UPLOAD_CONTENT_TYPE)}
        response = self.irmc.post(target, MultipartEncoder(fields=fields))
        if response.status not in (200, 202, 204):
            raise self._error(response, changed)

    def _read_file(self, path: str) -> bytes:
        """公開鍵・証明書のファイルを読み込みます。

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
            raise ModuleError(f"Could not read file at '{path}': {e}") from e

    def _ssh_key_differs(self, content: bytes, path: str, current: Any) -> bool:
        """SSH公開鍵が登録済みのものと異なるかを判定します。

        引数:
            content - 公開鍵ファイルの内容
            path - エラーメッセージに使うファイルのパス
            current - 登録済みのSSHv2KeyFingerprint（"RSA 4096 e9:a4:...:5e:"。未登録ならNone）

        戻り値:
            異なる（または未登録）ならTrue

        例外:
            ValidationError - OpenSSH形式の公開鍵ではない場合
        """
        try:
            fingerprints = ssh_public_key_irmc_fingerprints(content.decode('ascii', errors='replace'))
        except ValueError as e:
            raise ValidationError(f"'{path}' is not an OpenSSH public key: {e}") from e
        # 鍵の種類の大文字小文字（RSA / rsa）と末尾の':'は機種によって違うので、フィンガープリントだけを比べる
        # 計算方法も世代で違う（MD5 / SHA-256の先頭16バイト）ので、どちらかと一致すれば登録済みとする
        match = SSH_FINGERPRINT_PATTERN.search(str(current or '').lower())
        return match is None or match.group(0) not in fingerprints

    def _smime_certificate_differs(self, content: bytes, path: str, current: Any) -> bool:
        """S/MIME証明書が登録済みのものと異なるかを判定します。

        引数:
            content - 証明書ファイルの内容
            path - エラーメッセージに使うファイルのパス
            current - 登録済みのSMIMECertificate（未登録ならNone）

        戻り値:
            異なる（または未登録）ならTrue

        例外:
            ValidationError - PEM形式の証明書ではない場合
        """
        try:
            fingerprint = pem_sha1_fingerprint(content.decode('ascii', errors='replace'))
        except ValueError as e:
            raise ValidationError(f"'{path}' is not a PEM certificate: {e}") from e
        return str(dig(current, 'SHA1FingerPrint') or '').lower() != fingerprint

    def get_state(self, params: Mapping[str, Any]) -> ControllerResult:
        """ユーザーの設定を取得します。

        引数:
            params - パラメータ辞書（必須: name）

        戻り値:
            ControllerResult（changed=False, account / account_info属性を含む）

        例外:
            HttpError - HTTPリクエストが失敗した場合
            ModuleError - ユーザーが見つからない場合、またはiRMCのベンダーを判別できない場合
        """
        self.logger.debug(f"Getting user {params['name']!r} from iRMC")
        found = self._find(params['name'])
        if found is None:
            raise ModuleError(f"User {params['name']!r} not found")
        path, _ = found
        return ControllerResult.unchanged(**self._result(path))

    def set_state(self, params: Mapping[str, Any]) -> ControllerResult:
        """ユーザーを作成または変更します。

        次の順に行い、必要なものだけを送ります。
        ユーザーの作成 → 設定の変更（1回のPATCH） → SSH公開鍵 → S/MIME証明書 → パスワード。
        パスワードを最後にするのは、自分自身のパスワードを変えた後はiRMCにアクセスできなくなるためです。

        引数:
            params - パラメータ辞書（必須: name。任意: password, account, ssh_public_key_path,
                     smime_certificate_path。空文字のパスは未指定として扱う）

        戻り値:
            ControllerResult（changed=TrueまたはFalse, account / account_info属性を含む）

        例外:
            ValidationError - 指定が不正な場合
            HttpError - HTTPリクエストが失敗した場合
            ModuleError - ファイルを読み込めない場合、またはiRMCのベンダーを判別できない場合
        """
        name = params['name']
        if params.get('password'):
            self._secrets.append(params['password'])
        desired = params.get('account') or {}
        ssh_key_path = params.get('ssh_public_key_path') or None
        smime_path = params.get('smime_certificate_path') or None

        # ファイルは iRMC に何か送る前に読んで検証する
        ssh_key = self._read_file(ssh_key_path) if ssh_key_path else None
        smime = self._read_file(smime_path) if smime_path else None

        changed: list[str] = []
        found = self._find(name)
        if found is None:
            path = self._create(params, desired)
            changed.append('user created')
            password_sent = True
        else:
            path, _ = found
            password_sent = False

        body = self._fetch(path)
        current = self._account(body)
        changes = diff(desired, current)
        self._check_snmpv3(desired, current, changes)

        if changes:
            response = self._patch(path, self._to_redfish(changes))
            if response.status not in (200, 204):
                raise self._error(response, changed)
            changed.append(f"settings ({', '.join(sorted(changes))})")

        if ssh_key is not None and self._ssh_key_differs(ssh_key, ssh_key_path,
                                                         self._to_module(body).get('SSHv2KeyFingerprint')):
            self._upload(body, 'AddUserSSHKey', ssh_key_path, ssh_key, changed)
            changed.append('SSH public key')

        if smime is not None and self._smime_certificate_differs(smime, smime_path,
                                                                 self._to_module(body).get('SMIMECertificate')):
            self._upload(body, 'AddUserMIMECert', smime_path, smime, changed)
            changed.append('S/MIME certificate')

        # 戻り値はパスワードの変更前に取得する（自分自身のパスワードを変えると、以降はアクセスできないため）
        result = self._result(path)

        if params.get('password') and not password_sent and self._change_password(path, params, changed):
            changed.append('password')

        if not changed:
            return ControllerResult.unchanged(msg=f"User {name!r} is already in the desired state", **result)

        self.logger.log(f"User {name!r} changed: {', '.join(changed)}")
        return ControllerResult.changed_success(msg=f"User {name!r} changed: {', '.join(changed)}", **result)

    def delete_state(self, params: Mapping[str, Any]) -> ControllerResult:
        """ユーザーを削除します。

        引数:
            params - パラメータ辞書（必須: name）

        戻り値:
            ControllerResult（ユーザーがいなければchanged=False）

        例外:
            HttpError - HTTPリクエストが失敗した場合
            ModuleError - リンクが見つからない場合
        """
        name = params['name']
        found = self._find(name)
        if found is None:
            return ControllerResult.unchanged(msg=f"User {name!r} does not exist")

        path, _ = found
        response = self.irmc.delete(path)
        if response.status not in (200, 202, 204):
            raise self._error(response)
        self.logger.log(f"User {name!r} deleted: {path}")
        return ControllerResult.changed_success(msg=f"User {name!r} deleted")


def irmc_account(module: AnsibleModule) -> None:
    """irmc_accountモジュールのメイン処理です。

    引数:
        module - AnsibleModuleインスタンス
    """
    if module.check_mode:
        module.exit_json(changed=False, msg='module was not run')

    uses_upload = module.params.get('ssh_public_key_path') or module.params.get('smime_certificate_path')
    if module.params['command'] == 'set' and uses_upload and not HAS_REQUESTS_TOOLBELT:
        module.fail_json(msg=missing_required_lib('requests_toolbelt'))

    # ロガー初期化
    logger = AnsibleLogger(module)

    def irmc_factory(username: str, password: str) -> iRMC:
        return iRMC(
            ipaddress=module.params['irmc_url'],
            username=username,
            password=password,
            validate_certs=module.params['validate_certs'],
            logger=logger,
            raise_on_error=True,
        )

    # iRMCクライアント初期化
    irmc = irmc_factory(module.params['irmc_username'], module.params['irmc_password'])

    # Controller初期化
    controller = AccountController(irmc, logger, irmc_factory)

    # ビジネスロジック実行
    try:
        if module.params['command'] == 'get':
            controller_result = controller.get_state(module.params)
        elif module.params['command'] == 'set':
            controller_result = controller.set_state(module.params)
        elif module.params['command'] == 'delete':
            controller_result = controller.delete_state(module.params)
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
        command=dict(required=False, type='str', default='get', choices=['get', 'set', 'delete']),
        name=dict(required=True, type='str'),
        password=dict(required=False, type='str', no_log=True),
        account=dict(required=False, type='dict', options=ACCOUNT_OPTIONS),
        ssh_public_key_path=dict(required=False, type='str', no_log=False),
        smime_certificate_path=dict(required=False, type='str'),
    )
    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=False,
    )

    irmc_account(module)


if __name__ == '__main__':
    main()
