SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c
.ONESHELL:

SSH_BITS   ?= 4096
SMIME_BITS ?= 2048
SMIME_DAYS ?= 365

# Subject とコメントは tests/manual/assets/certs と同じ方針にしている。
# 「実在の企業・地名と衝突しないこと」と「鍵・証明書だけを見て出所が辿れること」を満たす値。
# ドメインは RFC 2606 で文書用に予約されている example.com 配下を使う。
#
# openssl の -subj は '/' が項目の区切りなので、値に含める '/' は '\/' とエスケープする。
# エスケープを忘れるとそれ以降の項目(CN を含む)が黙って捨てられる。verify で CN と OU を確認している。
C  ?= JP
ST ?= Example
L  ?= Example
O  ?= iRMC Manual Test
OU ?= tests\/manual

DOMAIN := irmc-test.example.com

# 2組ずつ作るのは、手動テストの arrange と act で別々のものを登録し、
# 何回実行しても before と after に差が出るようにするため。
# irmc_account の set は、登録済みとフィンガープリントが同じなら何もしない(changed=False)。
SSH_KEYS := ssh1 ssh2
SMIMES   := smime1 smime2

# openssl の Subject 表示の形式を固定する(tests/manual/assets/certs の Makefile と同じ理由)
NAMEOPT := -nameopt RFC2253

.PHONY: all clean verify inspect

all: $(addsuffix .pub,$(SSH_KEYS)) $(addsuffix .crt,$(SMIMES)) verify

# --- SSH 公開鍵(秘密鍵は sshN、公開鍵は sshN.pub) ---
# RSA 4096 は、iRMC に登録できることを実機(M7以前の世代と M8以降の世代)で確かめた形式。
# コメントに出所を書いておくと、iRMC に残った鍵のフィンガープリントからここへ辿り着ける。
ssh1.pub ssh2.pub: %.pub:
	rm -f $* $*.pub
	ssh-keygen -q -t rsa -b $(SSH_BITS) -N '' -C '$*@$(DOMAIN)' -f $*

# --- S/MIME 証明書(自己署名) ---
# 秘密鍵は PKCS#8 で作る(tests/manual/assets/certs の Makefile と同じ理由)。
smime1.key smime2.key:
	openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:$(SMIME_BITS) -out $@
	test "$$(head -n 1 $@)" = "-----BEGIN PRIVATE KEY-----"

smime1.crt smime2.crt: %.crt: %.key
	openssl req -new -x509 -key $< -sha256 -days $(SMIME_DAYS) -out $@ \
	  -subj "/C=$(C)/ST=$(ST)/L=$(L)/O=$(O)/OU=$(OU)/CN=$*.$(DOMAIN)/emailAddress=$*@$(DOMAIN)" \
	  -addext "subjectAltName=email:$*@$(DOMAIN)" \
	  -addext "basicConstraints=critical,CA:FALSE" \
	  -addext "keyUsage=critical,digitalSignature,keyEncipherment" \
	  -addext "extendedKeyUsage=emailProtection"

verify: $(addsuffix .pub,$(SSH_KEYS)) $(addsuffix .crt,$(SMIMES))
	for k in $(SSH_KEYS); do
	  ssh-keygen -l -E md5 -f $$k.pub | grep -qF "$$k@$(DOMAIN)"
	  diff -u <(ssh-keygen -y -f $$k | awk '{print $$1, $$2}') <(awk '{print $$1, $$2}' $$k.pub)
	done
	# 2組のフィンガープリントが違わないと、act で変更が起きずテストにならない
	test "$$(ssh-keygen -l -E md5 -f ssh1.pub | awk '{print $$2}')" \
	  != "$$(ssh-keygen -l -E md5 -f ssh2.pub | awk '{print $$2}')"
	for s in $(SMIMES); do
	  openssl x509 -in $$s.crt -noout -subject $(NAMEOPT) | grep -qF "CN=$$s.$(DOMAIN)"
	  openssl x509 -in $$s.crt -noout -subject $(NAMEOPT) | grep -qF "OU=tests/manual"
	  openssl x509 -in $$s.crt -noout -ext extendedKeyUsage | grep -qF "E-mail Protection"
	  diff -u <(openssl x509 -in $$s.crt -noout -pubkey) <(openssl pkey -in $$s.key -pubout)
	done
	test "$$(openssl x509 -in smime1.crt -noout -fingerprint -sha1)" \
	  != "$$(openssl x509 -in smime2.crt -noout -fingerprint -sha1)"
	echo "OK"

inspect: $(addsuffix .pub,$(SSH_KEYS)) $(addsuffix .crt,$(SMIMES))
	for k in $(SSH_KEYS); do
	  echo "== $$k =="
	  ssh-keygen -l -E md5 -f $$k.pub
	done
	for s in $(SMIMES); do
	  echo "== $$s =="
	  openssl x509 -in $$s.crt -noout -subject -dates -fingerprint -sha1
	done

clean:
	rm -f $(SSH_KEYS) $(addsuffix .pub,$(SSH_KEYS)) $(addsuffix .key,$(SMIMES)) $(addsuffix .crt,$(SMIMES))
