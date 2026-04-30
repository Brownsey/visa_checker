## Summary
Implement the Telegram Bot alert channel — the primary notification method. Telegram delivers messages to your phone instantly and for free.

## Setup Requirements
1. Create a bot via @BotFather → get `TELEGRAM_BOT_TOKEN`
2. Start a conversation with the bot or add it to a group → get `TELEGRAM_CHAT_ID`

## Tasks
- [ ] Implement `TelegramChannel(AlertChannel)` in `visa_checker/alerts/telegram.py`
- [ ] Use `httpx` to call the Telegram Bot API (`sendMessage`)
- [ ] Format messages with Markdown v2 (bold country/date, code-formatted URL)
- [ ] Include a direct "Book Now" button via `InlineKeyboardMarkup` if possible
- [ ] Handle Telegram rate limits (429 response): back off and retry
- [ ] Handle invalid chat ID gracefully (log error, don't crash)
- [ ] Write unit tests mocking the Telegram API endpoint

## Message Example
```
*VISA SLOT AVAILABLE*

*Country:* France (Schengen)
*Centre:* London \- TLScontact  
*Date:* Tuesday 15 July 2026  
*Time:* 10:30 AM

[Book Now](https://booking-url)

_Detected: 2026\-04\-29 14:32 UTC_
```

## Acceptance Criteria
- `test_all()` successfully delivers a test message to the configured chat
- Rate limit (429) causes a retry after the `Retry-After` header value
- `AlertError` is raised (not unhandled exception) on permanent failures
