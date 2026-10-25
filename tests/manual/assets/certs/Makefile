SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c
.ONESHELL:

BITS        ?= 2048
CA_DAYS     ?= 3650
SERVER_DAYS ?= 365

# Subject は「実在の企業・地名と衝突しないこと」と「証明書だけを見て出所が辿れること」を
# 満たす値にしている。この証明書は Ansible では元に戻せず iRMC に残り続けるため、後日
# openssl x509 -subject で見た人が何のための証明書か分かる必要がある。
# ドメインは RFC 2606 で文書用に予約されている example.com 配下を使う。
#
# openssl の -subj は '/' が項目の区切りなので、値に含める '/' は '\/' とエスケープする。
# エスケープを忘れるとそれ以降の項目(CN を含む)が黙って捨てられる。
# verify ターゲットで CN を確認しているので、間違えれば必ず気付ける。
C  ?= JP
ST ?= Example
L  ?= Example
O  ?= iRMC Manual Test
OU ?= tests\/manual

CA1_CN     ?= ca1.irmc-test.example.com
CA2_CN     ?= ca2.irmc-test.example.com
SERVER1_CN ?= server1.irmc-test.example.com
SERVER2_CN ?= server2.irmc-test.example.com

CA1_SUBJ := /C=$(C)/ST=$(ST)/L=$(L)/O=$(O)/OU=$(OU)/CN=$(CA1_CN)
CA2_SUBJ := /C=$(C)/ST=$(ST)/L=$(L)/O=$(O)/OU=$(OU)/CN=$(CA2_CN)

# サーバ証明書を2組作るのは、手動テストの arrange と act で別々の証明書を登録し、
# 何回実行しても before と after に差が出るようにするため。
# irmc_certificate の set は登録済みと同じ証明書なら何もしない(changed=False)ので、
# 同じ証明書だけでは act で変更が起きず、エビデンスにならない。
SERVERS := server1 server2
CRTS    := $(addsuffix .crt,$(SERVERS))
KEYS    := $(addsuffix .key,$(SERVERS))

# openssl の Subject 表示は既定の -nameopt が版によって違い、"CN = x" と "CN=x" で揺れる。
# verify の grep が環境依存で落ちるため、RFC2253 を明示して形式を固定する。
# compat は OU の '/' を '\/' とエスケープしてしまうので使えない。
NAMEOPT := -nameopt RFC2253

.PHONY: all clean verify inspect

all: ca1.crt ca2.crt $(CRTS) verify

# --- CA(明示ルールなので下のパターンルールより優先される) ---
# ca1 はサーバ証明書を署名する CA。ca2 は何も署名しない2枚目の CA で、
# 手動テストの set_ca_cert ケースで arrange に登録し、act の ca1 との間で差を出すためだけに使う。
ca1.key ca2.key:
	openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:$(BITS) -out $@
	test "$$(head -n 1 $@)" = "-----BEGIN PRIVATE KEY-----"

ca1.crt: SUBJ = $(CA1_SUBJ)
ca2.crt: SUBJ = $(CA2_SUBJ)
ca1.crt ca2.crt: %.crt: %.key
	openssl req -new -x509 -key $< -sha256 -days $(CA_DAYS) -out $@ \
	  -subj "$(SUBJ)" \
	  -addext "basicConstraints=critical,CA:TRUE" \
	  -addext "keyUsage=critical,keyCertSign,cRLSign" \
	  -addext "subjectKeyIdentifier=hash"

# --- サーバ証明書(CN だけがサーバごとに異なる) ---
server1.csr server1.ext: CN = $(SERVER1_CN)
server2.csr server2.ext: CN = $(SERVER2_CN)

# 秘密鍵は PKCS#8 (-----BEGIN PRIVATE KEY-----) で作る。openssl 3.x の既定の形式で、
# 利用者が普通に作る鍵と同じ形式でテストするため。
# genrsa は openssl 1.1 では PKCS#1 を出力するので、版によらず PKCS#8 になる genpkey を使う。
%.key:
	openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:$(BITS) -out $@
	test "$$(head -n 1 $@)" = "-----BEGIN PRIVATE KEY-----"

%.csr: %.key
	openssl req -new -key $< -out $@ \
	  -subj "/C=$(C)/ST=$(ST)/L=$(L)/O=$(O)/OU=$(OU)/CN=$(CN)"

%.ext:
	printf '%s\n' \
	  'basicConstraints=CA:FALSE' \
	  'keyUsage=critical,digitalSignature,keyEncipherment' \
	  'extendedKeyUsage=serverAuth' \
	  'subjectAltName=DNS:$(CN)' \
	  > $@

%.crt: %.csr %.ext ca1.crt ca1.key
	openssl x509 -req -in $< -CA ca1.crt -CAkey ca1.key -CAcreateserial \
	  -out $@ -days $(SERVER_DAYS) -sha256 -extfile $*.ext

verify: ca1.crt ca2.crt $(CRTS) $(KEYS)
	# Subject の '/' をエスケープし忘れると CN ごと欠落し、server1 と server2 が
	# 区別できなくなる。黙って壊れるので必ず確認する。
	openssl x509 -in ca1.crt      -noout -subject $(NAMEOPT) | grep -qF "CN=$(CA1_CN)"
	openssl x509 -in ca2.crt     -noout -subject $(NAMEOPT) | grep -qF "CN=$(CA2_CN)"
	openssl verify -CAfile ca2.crt ca2.crt
	openssl x509 -in server1.crt -noout -subject $(NAMEOPT) | grep -qF "CN=$(SERVER1_CN)"
	openssl x509 -in server2.crt -noout -subject $(NAMEOPT) | grep -qF "CN=$(SERVER2_CN)"
	openssl x509 -in server1.crt -noout -subject $(NAMEOPT) | grep -qF "OU=tests/manual"
	for s in $(SERVERS); do
	  openssl verify -CAfile ca1.crt $$s.crt
	  test "$$(head -n 1 $$s.key)" = "-----BEGIN PRIVATE KEY-----"
	  diff -u <(openssl x509 -in $$s.crt -noout -pubkey) \
	          <(openssl pkey -in $$s.key -pubout)
	done
	echo "OK"

inspect: ca1.crt $(CRTS)
	echo "== CA =="
	openssl x509 -in ca1.crt -noout -subject -issuer -dates
	for s in $(SERVERS); do
	  echo
	  echo "== $$s =="
	  openssl x509 -in $$s.crt -noout -subject -issuer -dates -ext subjectAltName
	done

clean:
	rm -f ca1.key ca1.crt ca1.srl ca2.key ca2.crt $(addsuffix .key,$(SERVERS)) \
	      $(addsuffix .csr,$(SERVERS)) $(addsuffix .ext,$(SERVERS)) $(CRTS)
