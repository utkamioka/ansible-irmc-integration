# 手動テスト用の SSH 公開鍵と S/MIME 証明書

`tests/manual/cases/irmc_account.yml` の `ssh_public_key` / `smime_certificate` ケースが、
iRMC のユーザー（`ansibleuser`）に登録するテスト専用の鍵と証明書です。

**本番用ではありません。** テスト以外の目的で使わないでください。

## 生成する

**鍵と証明書は git 管理下にありません。** ケースを実行する前に生成してください。

```bash
cd tests/manual/assets/account
make
```

`make` は2組の SSH 鍵と2枚の S/MIME 証明書を作り、`verify` まで実行します。
作り直したいときは `make clean && make` です。生成物は `.gitignore` で除外されているので、
何度作り直しても git に差分は出ません。

追跡しているのは `Makefile` と、このファイルだけです。秘密鍵をリポジトリに入れないためです
（`tests/manual/assets/certs/` と同じ扱い）。

macOS 標準の make 3.81 は `.ONESHELL` に対応していないため、`verify` が構文エラーで失敗します
（`tests/manual/assets/certs/` と同じ）。鍵と証明書そのものは作られます。
`verify` まで確かめるときは GNU make 4 以降を使ってください。

## ファイル

| ファイル | 用途 |
| --- | --- |
| `ssh1.pub`（秘密鍵 `ssh1`） | `ssh_public_key` ケースの `arrange` で登録する |
| `ssh2.pub`（秘密鍵 `ssh2`） | `ssh_public_key` ケースの `act` で登録する |
| `smime1.crt`（秘密鍵 `smime1.key`） | `smime_certificate` ケースの `arrange` で登録する |
| `smime2.crt`（秘密鍵 `smime2.key`） | `smime_certificate` ケースの `act` で登録する |

iRMC に登録するのは公開鍵（`*.pub`）と証明書（`*.crt`）だけです。秘密鍵は登録しません。

- SSH 鍵は RSA 4096 ビットです。iRMC に登録できることを実機（M7以前の世代と M8以降の世代）で確かめた形式です。
- S/MIME 証明書は自己署名で、`extendedKeyUsage=emailProtection` を持ちます。
  秘密鍵は PKCS#8（`-----BEGIN PRIVATE KEY-----`）で作ります。

## 2組ずつある理由

`irmc_account` の `set` は、登録済みのものとフィンガープリント（SSH 公開鍵は MD5、S/MIME 証明書は SHA1）が
同じなら何もしません（`changed=False`）。同じものだけでは `act` で変更が起きず、
`before` と `after` も同一になってエビデンスになりません。
`arrange` で1つ目、`act` で2つ目を登録することで、何回実行しても差が出ます。

## 後片付け

`irmc_account` では、登録した鍵と証明書を削除できません。
そのため各ケースは、最初にユーザーを削除してから作り直し、最後にユーザーごと削除します。
ケースを途中で止めたときは、`ansibleuser` に鍵や証明書が残っていることがあります。
example の `delete` タグでユーザーを削除すれば消えます。

## 出所を辿れます

iRMC に残った鍵や証明書から、ここへ辿り着けるようにしてあります。

- SSH 鍵のコメントは `ssh1@irmc-test.example.com` / `ssh2@irmc-test.example.com` です。
- S/MIME 証明書の Subject は `O=iRMC Manual Test`、`OU=tests/manual`、
  `CN=smime1.irmc-test.example.com` などです（`tests/manual/assets/certs/` の証明書と同じ方針）。
  ただし iRMC は OU の `/` 以降を正しく表示せず、M7以前の世代では `tests`、M8以降の世代では `tests\` と表示されます。

iRMC に登録されているもののフィンガープリントは、モジュールの `account_info.SSHv2KeyFingerprint` /
`account_info.SMIMECertificate.SHA1FingerPrint` で見られます。手元のファイルと比べるときは次を使います。

```bash
ssh-keygen -l -E md5 -f ssh2.pub                                     # SSH 公開鍵(M7以前の世代)
awk '{print $2}' ssh2.pub | base64 -d | sha256sum | cut -c1-32 | sed 's/../&:/g; s/:$//'  # SSH 公開鍵(M8以降の世代)
openssl x509 -in smime2.crt -noout -fingerprint -sha1                # S/MIME 証明書
```

SSH 公開鍵のフィンガープリントは、iRMC の世代で計算方法が違います。
M7以前の世代では鍵のデータの MD5、M8以降の世代では鍵のデータの SHA-256 の先頭16バイトです（表示の形はどちらも同じ）。
`irmc_account` は両方を計算し、どちらかと一致すれば登録済みと判断します。

ドメインは RFC 2606 で文書用に予約されている `example.com` 配下を使っています。
組織名・地名は実在のものと衝突しない値にしてあります。
