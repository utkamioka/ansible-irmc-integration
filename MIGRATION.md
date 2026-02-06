# Migration and Rebranding Notice / 移行措置とリブランディングについて

[日本語 (Japanese)](#現在の暫定措置)

**Important**: This collection has been transferred from Fujitsu to Fsas Technologies Inc.

## Current Temporary Measures

This Ansible Collection has implemented the following temporary measures due to rebranding:

### Ansible Galaxy Namespace

- Current namespace: `fsas_temp_ns`
- Uses Python-valid identifiers and is fully functional as Ansible modules
- Will be replaced once the official namespace is secured

### GitHub Organization

- GitHub Organization references in this repository: `{{ NEW_ORG }}`
- Used as a placeholder and replacement is required once the official Organization is determined

## Required Future Actions

### 1. Establish GitHub Organization

- Creation or securing of a GitHub Organization for hosting this repository is required
- Once Organization name is determined, please replace `{{ NEW_ORG }}` with actual Organization name

### 2. Apply for Ansible Galaxy Namespace

- Please apply for Ansible Galaxy namespace after GitHub Organization is established
- Application URL: <https://github.com/ansible/galaxy/issues>
- Please wait for application approval

### 3. Official Namespace Migration

- Once new namespace is approved, please replace `fsas_temp_ns` with official namespace
- Please execute all tests and verify functionality

### 4. GitHub Repository Publication

- After namespace replacement is completed, please push this Git repository to the new Organization
- Use repository name `ansible-irmc-integration` (changed from previous `fujitsu-ansible-irmc-integration`)
- Please make official release under the new namespace

### 5. End Migration Measures

- Please delete this file (MIGRATION.md) once all above tasks are completed
- Please remove migration notice from README.md as well

---

**重要**: このコレクションは富士通からエフサステクノロジーズ株式会社へ移管されました

## 現在の暫定措置

本Ansible Collectionは、リブランディングに伴い以下の暫定措置を講じています：

### Ansible Galaxy名前空間

- 現在の名前空間: `fsas_temp_ns`
- Pythonシンボルとして有効な文字列を適用しており、Ansibleモジュールとして完全に動作します
- 正式な名前空間が確保され次第、一括置換が必要です

### GitHub Organization

- 本リポジトリ中のGitHub Organization参照: `{{ NEW_ORG }}`
- プレースホルダーとして記述しており、正式なOrganizationが決定され次第置換が必要です

## 今後必要な作業

### 1. GitHub Organization確立

- 本リポジトリを配置するためのGitHub Organizationの作成または確保が必要です
- Organization名が決定したら、`{{ NEW_ORG }}` を実際のOrganization名に一括置換してください

### 2. Ansible Galaxy名前空間申請

- GitHub Organizationが確立した後、Ansible Galaxyの名前空間を申請してください
- 申請先: <https://github.com/ansible/galaxy/issues>
- 申請が承認されるまで待機してください

### 3. 名前空間の正式移行

- 新しい名前空間が承認されたら、`fsas_temp_ns` を正式な名前空間に一括置換してください
- 全テストの実行と動作確認を行ってください

### 4. GitHub Repository公開

- 名前空間置換完了後、このGitリポジトリを新しいOrganizationにプッシュしてください
- リポジトリ名は `ansible-irmc-integration` としてください（旧名 `fujitsu-ansible-irmc-integration` から変更）
- 新しい名前空間での正式リリースを行ってください

### 5. 移行措置の終了

- 上記すべての作業が完了したら、本ファイル（MIGRATION.md）を削除してください
- README.mdの移行案内も削除してください
