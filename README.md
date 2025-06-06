# recording

## Getting Started

### CPU版

```bash
docker compose up bot --build
```

### GPU版

```bash
docker compose -f docker-compose.gpu.yml up bot --build
```

## 環境変数

`.env.example`をコピーして`.env`を作成し、必要な環境変数を設定してください。

## 開発フロー

devcontainerを利用して開発

左下の「><」アイコンをクリックし、「Reopen in Container」を選択

### Windowsで開発する場合

デフォルトでGPUが無効になっている。正確にはCPU環境で動作する設定になっている

GPU環境でのテストをしたい場合は、`devcontainer.json`の`dockerComposeFile`を適切に変更すること

## 補足

- Python 3.11で開発
  - 一部ライブラリが3.12以降で非推奨になったため
- 環境変数の`GITHUB_REPO_URL`は、プライベートリポジトリの場合、PATを組み込む
