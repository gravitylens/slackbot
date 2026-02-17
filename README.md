# SlackBot

A standalone executable for sending messages to Slack channels via pipeline.

## Usage

```bash
# Basic usage
echo "Hello World!" | slackbot

# Send to specific channel or user
echo "Hello team!" | slackbot "#general"
echo "Hello!" | slackbot "@username"

# Pipe files or command output
cat message.txt | slackbot
python script.py | slackbot "#notifications"
```

## Message Types

**Plain text with markdown:**
```bash
echo "*Bold* and _italic_ text" | slackbot
echo "**Tables** are automatically formatted" | slackbot
```

**Slack blocks (JSON):**
```bash
echo '{"blocks":[{"type":"section","text":{"type":"mrkdwn","text":"*Rich formatting*"}}]}' | slackbot
```

## Command Options

```bash
slackbot [destination] [--text-only]
```

- `destination`: Channel (#channel) or user (@user). Uses default from `.env` if not specified
- `--text-only`: Force plain text mode, skip JSON block detection

## Configuration

Create `.env` file (local directory or `~/.env`):
```
SLACK_BOT_TOKEN=xoxb-your-token-here
SLACK_CHANNEL=#default-channel
```