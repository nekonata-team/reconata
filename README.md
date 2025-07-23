# reconata

## Getting Started

### 環境変数

`.env.example`をコピーして`.env`を作成し、必要な環境変数を設定してください。

`DISCORD_BOT_TOKEN`と`GOOGLE_API_KEY`を用意する必要があります。

### CPU版

```bash
# Bot
docker compose up bot --build

# CLI
docker compose run --rm bot cli.py --help
```

### GPU版

```bash
# Bot
docker compose -f docker-compose.gpu.yml up bot --build

# WebSocket
docker compose -f docker-compose.gpu.yml up websocket --build
```
