# recording

## Getting Started

### CPU版

初回起動

```bash
docker compose up --build
```

二回目以降

```bash
docker compose up
```

### GPU版

初回起動

```bash
docker compose -f docker-compose.gpu.yml up --build
```

二回目以降

```bash
docker compose -f docker-compose.gpu.yml up
```

## 環境変数

`.env.example`をコピーして`.env`を作成し、必要な環境変数を設定してください。

## 開発フロー

devcontainerを使用して開発する。

## 補足

- Python 3.11が必要
  - 一部ライブラリが3.12以降で非推奨になったため
- GPU版はNVIDIAドライバとDockerのNVIDIAランタイムが必要
- 環境変数の`GITHUB_REPO_URL`は、プライベートリポジトリの場合、PATを組み込む
