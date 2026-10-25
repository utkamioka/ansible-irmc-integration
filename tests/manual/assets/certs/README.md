# 手動テスト用の SSL 証明書

`tests/manual/cases/irmc_certificate.yml` が iRMC に登録するテスト専用の証明書です。

**本番用ではありません。** テスト以外の目的で使わないでください。

## 生成する

**証明書は git 管理下にありません。** ケースを実行する前に生成してください。

```bash
cd tests/manual/assets/certs
make
```

`make` は2枚の CA と2枚のサーバ証明書を作り、`verify` まで実行します。数秒で終わります。
作り直したいときは `make clean && make` です。生成物は `.gitignore` で除外されているので、
何度作り直しても git に差分は出ません。

追跡しているのは `Makefile` と、このファイルだけです。
秘密鍵をリポジトリに入れないためで、ファームウェアを `assets/firmware/` に
手作業で配置するのと同じ扱いです。

## ファイル

| ファイル | 用途 |
| --- | --- |
| `ca1.crt` / `ca1.key` | 自己署名 CA。2枚のサーバ証明書を署名する。`set_ca_cert` ケースの `act` で登録する |
| `ca2.crt` / `ca2.key` | 何も署名しない2枚目の自己署名 CA。`set_ca_cert` ケースの `arrange` で登録する |
| `server1.crt` / `server1.key` | `set_server_cert` ケースの `arrange` で登録する |
| `server2.crt` / `server2.key` | `set_server_cert` ケースの `act` で登録する |
| `*.csr` / `*.ext` | 生成の中間ファイル |

openssl 3.x は既定でランダムなシリアル番号を使うため `ca1.srl` は生成されません
（古い openssl では生成されます。`make clean` はどちらでも動くようにしてあります）。

## やってはいけないこと

**`ca1.crt` / `ca2.crt` を OS・ブラウザ・CI ランナーの信頼ストアに追加しないでください。**
この CA は `CA:TRUE` / `keyCertSign` を持つため、`ca1.key` を持つ者は任意の名前の
証明書を発行できます。信頼ストアに入れた端末は、その証明書を本物として受け入れます。
iRMC の証明書警告を消す目的でも追加しないでください。

**テスト iRMC で証明書ベース認証（CBA）を有効にしないでください。**
`set_ca_cert` ケースは `ssl_ca_cert_path` でこの `ca1.crt` / `ca2.crt` を iRMC の CA 証明書として
登録します。CBA を有効にしていると、
この CA が署名したクライアント証明書でログインできてしまいます。

なお、この鍵で保護されるものは何もありません。テスト iRMC は
`validate_certificate=false` で運用しており、証明書は検証されていません。
**「ちゃんとした証明書を入れたから検証を有効にしてよい」とは考えないでください。**

## サーバ証明書と CA が2枚ずつある理由

`irmc_certificate` の `set` は、登録済みと同じ証明書なら何もしません（`changed=False`）。
同じ証明書だけでは `act` で変更が起きず、`before` と `after` も同一になってエビデンスになりません。
`set_server_cert` ケースは `arrange` で `server1`、`act` で `server2` を、
`set_ca_cert` ケースは `arrange` で `ca2`、`act` で `ca1` を登録することで、何回実行しても差が出ます。

## Subject から出所を辿れます

この証明書は **Ansible では元に戻せず iRMC に残り続けます**（iRMC の Web UI からは戻せます）。
後日、見慣れない証明書が入っていることに気づいた人がここへ辿り着けるよう、
`O` と `OU` に出所を書いてあります。

```text
subject=C = JP, ST = Example, L = Example, O = iRMC Manual Test, OU = tests/manual,
        CN = server2.irmc-test.example.com
```

iRMC が今どの証明書を提示しているかは次で確認できます。

```bash
openssl s_client -connect <host>:443 </dev/null 2>/dev/null \
  | openssl x509 -noout -subject -issuer -dates
```

ドメインは RFC 2606 で文書用に予約されている `example.com` 配下を使っています。
組織名・地名は実在のものと衝突しない値にしてあります。

### 秘密鍵の形式

秘密鍵は PKCS#8（`-----BEGIN PRIVATE KEY-----`）で作ります。openssl 3.x の既定の形式で、
利用者が普通に作る鍵と同じ形式でテストするためです。
`openssl genrsa` は openssl 1.1 では PKCS#1 を出力するので、版によらず PKCS#8 になる
`openssl genpkey` を使い、生成のたびにヘッダを確認しています。

### 注意: Subject の `/` はエスケープが必要

`openssl req -subj` は `/` が項目の区切りです。`OU=tests/manual` のように値に `/` を含める場合は
`OU=tests\/manual` とエスケープしないと、**それ以降の項目（`CN` を含む）が黙って捨てられます**。
CN が消えると `server1` と `server2` を区別できなくなりテストが無意味になるため、
`make verify` で CN と OU を確認しています。
