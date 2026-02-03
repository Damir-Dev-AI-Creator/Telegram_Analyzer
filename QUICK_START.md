# 🚀 Quick Start Guide

## Minimal Setup (Multi-User Bot)

### 1. Get Bot Token

1. Open Telegram and message [@BotFather](https://t.me/BotFather)
2. Send `/newbot`
3. Follow instructions to create your bot
4. Copy the **Bot Token**

### 2. Configure Environment

Create `.env` file in project root:

```bash
# Only BOT_TOKEN is required!
BOT_TOKEN=your_bot_token_from_botfather
```

That's it! **No other .env variables needed** for multi-user mode.

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Run Bot

```bash
python main.py --bot
```

You should see:
```
🤖 Telegram Analyzer Bot (Multi-User)
✅ База данных инициализирована
✅ FSM storage настроен
✅ Обработчики зарегистрированы
✅ Бот запущен и готов к работе!
Режим: Multi-User (любой пользователь может настроить)
```

### 5. Configure Your Account

1. Open your bot in Telegram
2. Send `/start`
3. Follow `/setup` command to configure:
   - Telegram API credentials (API_ID, API_HASH)
   - QR-code authorization
   - Optional: Claude API key

## Why Only BOT_TOKEN?

### Before (Single-User):
```env
BOT_TOKEN=...
OWNER_ID=...        # Global, only one user
API_ID=...          # Global, shared
API_HASH=...        # Global, shared
PHONE=...           # Global, shared
CLAUDE_API_KEY=...  # Global, shared
```
❌ Only OWNER_ID could use bot

### After (Multi-User):
```env
BOT_TOKEN=...  # Only this is needed!
```
✅ Each user configures their own credentials via `/setup`
✅ All data stored encrypted in database
✅ Complete per-user isolation

## 📁 Directory Structure

After first user setup:
```
data/
├── telegram_analyzer.db      # User database (encrypted)
├── .encryption_key           # Encryption key (auto-generated)
└── users/
    └── {user_id}/
        ├── exports/          # CSV exports
        └── analysis/         # DOCX analysis
```

## 🔧 Advanced: Optional .env Variables

### For Legacy GUI/CLI Mode:
```env
API_ID=12345678
API_HASH=your_api_hash
PHONE=+79991234567
CLAUDE_API_KEY=sk-ant-...
```

### Custom Paths:
```env
# Export folder (default: data/exports)
EXPORT_FOLDER=custom/path/exports

# Output folder for analysis (default: data/output)
OUTPUT_FOLDER=custom/path/output
```

## 🎯 Commands

Once configured, users can:
- `/export @channel` - Export chat to CSV
- `/analyze file.csv` - Analyze with Claude AI
- `/exportanalyze @channel` - Export + analyze
- `/setup` - Reconfigure credentials
- `/help` - Full command reference

## 🔐 Security

- ✅ All Telegram sessions encrypted (Fernet)
- ✅ QR-code authorization (no code sharing in chats)
- ✅ Per-user data isolation
- ✅ Credentials never stored in plain text

## 🐛 Troubleshooting

### Bot won't start
```
Error: BOT_TOKEN не настроен!
```
**Solution:** Create `.env` file with `BOT_TOKEN=...`

### Database errors
```
Error: Unable to open database file
```
**Solution:**
```bash
mkdir -p data
# Bot will auto-create database on next start
```

### QR code not showing
```
Error: No module named 'qrcode'
```
**Solution:**
```bash
pip install qrcode>=8.0 Pillow>=12.0.0
```

## 📚 Full Documentation

- `MULTI_USER_IMPLEMENTATION.md` - Complete architecture
- `QR_AUTH_UPDATE.md` - QR authorization details
- `BOT_SETUP.md` - Bot mode documentation (if exists)

## 💡 Tips

1. **Multiple Bots**: Create separate bots with different BOT_TOKENs for testing
2. **Backup**: Regularly backup `data/` folder (contains database and encryption key)
3. **Monitoring**: Check logs with `tail -f logs/bot.log` (if logging configured)

## ✅ Success!

If you see "✅ Бот запущен и готов к работе!" - you're all set!

Now open your bot in Telegram and send `/start` to begin! 🎉
