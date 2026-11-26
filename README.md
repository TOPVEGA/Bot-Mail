<div align="center">

# 📧 VEGA Mail Bot

**A Telegram email-management bot built with pyTelegramBotAPI and the Mail.tm API, featuring mailbox creation, inbox access, mailbox settings, subscriptions, and administration tools.**

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![pyTelegramBotAPI](https://img.shields.io/badge/Framework-pyTelegramBotAPI-2CA5E0?style=for-the-badge)](https://pypi.org/project/pyTelegramBotAPI/)
[![SQLite](https://img.shields.io/badge/Database-SQLite-003B57?style=for-the-badge&logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![Mail.tm](https://img.shields.io/badge/Email%20API-Mail.tm-2563EB?style=for-the-badge)](https://mail.tm/)

**VEGA & Logic** · By [@TopVeGa](https://t.me/TopVeGa)

</div>

## Overview

VEGA Mail Bot is a Python Telegram bot that creates and manages email accounts through the Mail.tm API. Users interact with the bot through inline menus to create mailboxes, view inbox messages, check mailbox status, manage account settings, and manage subscriptions.

The project uses SQLite for local user, mailbox, subscription, and administration data.

## Features

### Mailbox management
- Create a new Mail.tm email address with a generated address and password.
- Enforce a configurable free-mailbox limit.
- Display a user's saved mailboxes and their status.
- View mailbox creation date, message count, notification setting, and enabled/disabled state.
- Delete one mailbox or delete all of a user's mailboxes.
- Retrieve inbox messages for a selected enabled mailbox.
- Display up to five inbox messages per inbox request.
- Check the message count and mailbox status.

### Mailbox settings
- Change a mailbox password through the Mail.tm API.
- Update the stored mailbox access token.
- Save a Telegram photo as the mailbox avatar file reference.
- Enable or disable inbox-notification preferences.
- Toggle the mailbox's local enabled state.

**Implementation note:** In the supplied source, `set_account_enabled()` is currently a placeholder that returns `True`; it does not make a remote API request to enable or disable the Mail.tm account. The avatar handler stores a Telegram `file_id`; it does not upload the image to Mail.tm. The notification preference is stored in the database, but the source does not contain a background inbox watcher that sends automatic new-mail alerts.

### Subscriptions and payments
- Display the monthly subscription options.
- Create a Telegram Stars invoice.
- Activate a 30-day subscription after Telegram reports a successful Stars payment.
- Display TON payment instructions with a user-specific payment comment.
- Provide `/verify_ton` with the details required for manual payment verification.

**TON payment note:** The source explicitly states that automatic TON verification requires a TON Center API integration and is not implemented. TON payments therefore require manual administrator verification; `/verify_ton` only displays payment information and does not verify a transaction.

### Developer and administration tools
- Restrict developer commands and the developer keyboard to configured developer IDs.
- View registered users.
- View statistics for users, mailboxes, and active subscriptions.
- Export users as a TXT file.
- Import users from a TXT file.
- Export mailbox records as JSON.
- Import mailbox records from a JSON file.
- Enable or disable user-to-developer contact forwarding.
- Receive user messages and reply to them by replying to the forwarded message.
- Notify configured developers when a user starts the bot, including account and subscription summary information.

### User access and contact
- Register users when they start the bot.
- Block access for users marked as blocked in the database.
- Restrict `/mail` to private chats.
- Allow users to contact the developer while the contact feature is enabled.
- Support `/cancel` during administrator import workflows.

## Project structure

```text
MailBot/
├── config.py          # Bot configuration, developer IDs, prices, and Mail.tm API URL
├── database.py        # SQLite schema and database operations
├── main.py            # Telegram handlers, menus, mailbox workflows, and payments
├── utils.py           # Mail.tm API requests, mailbox operations, and inbox parsing
└── requirements.txt   # Declared Python dependencies
```

## Technology stack

- **Python** — application runtime.
- **pyTelegramBotAPI** — Telegram bot framework and message handlers.
- **SQLite** — local persistent storage in `bot_mail.db`.
- **Requests** — HTTP communication with the Mail.tm API.
- **Mail.tm API** — email domains, account creation, authentication, inbox retrieval, and password updates.
- **python-dotenv** — imported by `config.py` to load environment variables from a `.env` file; it is not listed in the supplied `requirements.txt`.

## Requirements

- Python 3.10 or newer is recommended.
- A Telegram bot token from [@BotFather](https://t.me/BotFather).
- Access to the Mail.tm API.
- The Python dependencies listed below.

Install dependencies:

```bash
pip install -r requirements.txt
pip install python-dotenv
```

The second command installs `python-dotenv`, which is imported by the supplied `config.py` but omitted from `requirements.txt`.

## Configuration

The main configuration is in `config.py`.

| Setting | Purpose |
|---|---|
| `BOT_TOKEN` | Telegram bot token; the source provides a default value and also reads the environment |
| `dev` | Comma-separated developer Telegram user IDs |
| `TON_WALLET` | Wallet address displayed in TON payment instructions |
| `FREE_EMAIL_LIMIT` | Maximum number of mailboxes for a user without an active subscription |
| `STARS_MONTHLY_PRICE` | Monthly subscription price in Telegram Stars |
| `TON_MONTHLY_PRICE_NANO` | Monthly TON price represented in nanoTON |
| `TON_PAYMENT_COMMENT_PREFIX` | Prefix used to build the user's TON payment comment |
| `API_BASE` | Mail.tm API base URL |

The code calls `load_dotenv()`, so environment variables can be loaded from a `.env` file. Review `config.py` and move credentials and deployment-specific values into environment variables before deployment.

**Important credential warning:** The supplied archive contains a bot-token value directly in `config.py`. Treat that token as exposed: revoke it through BotFather and replace it before running or publishing this project. Do not copy the existing token into a README, commit it to Git, or share it publicly. Keep all credentials in a private environment configuration.

Example `.env` layout (use your own values):

```env
BOT_TOKEN=YOUR_NEW_TELEGRAM_BOT_TOKEN
dev=YOUR_TELEGRAM_USER_ID
TON_WALLET=YOUR_TON_WALLET_ADDRESS
```

## Installation and startup

1. Extract the project archive.
2. Open a terminal in the `MailBot/` directory.
3. Install the dependencies:

   ```bash
   pip install -r requirements.txt
   pip install python-dotenv
   ```

4. Configure the environment variables and review `config.py`.
5. Start the bot:

   ```bash
   python main.py
   ```

The bot initializes the SQLite database automatically when `main.py` starts. The database file is named `bot_mail.db` and is created in the current working directory.

## Bot commands

| Command | Description |
|---|---|
| `/start` | Register the user and display the main menu |
| `/restart` | Run the same start/menu flow |
| `/mail` | Open the bot menu in a private chat |
| `/dev` | Display the developer control panel for configured developers |
| `/verify_ton` | Display TON payment details for manual verification |
| `/cancel` | Cancel a pending administrator import operation |

Most mailbox actions are available through inline buttons rather than text commands.

## Database

The SQLite database contains tables for:

- `users` — Telegram user details, registration timestamp, and blocked status.
- `subscriptions` — subscription plan, start and expiry dates, payment method, payment reference, and active state.
- `mailboxes` — email address, password, token, domain, creation date, label, avatar file reference, notification preference, enabled state, and 2FA-related fields.
- `admin_state` — pending developer import action.
- `contact_settings` — global user-to-developer contact setting.
- `contact_map` — maps forwarded developer messages to their originating user.

The source includes database helper functions and fields for mailbox two-factor authentication, but the supplied bot interface does not expose a complete 2FA setup or verification workflow. These fields should not be described as an active user-facing feature.

## API behavior

The `utils.py` module communicates with `https://api.mail.tm` and includes:
- Retrieval of active email domains.
- Creation of email accounts.
- Retrieval of account access tokens.
- Inbox message retrieval and message-count lookup.
- Decoding of selected Base64 MIME text/plain content.
- Password changes and token refresh.
- Remote account deletion.
- A retry-enabled HTTP session for selected transient HTTP status codes.

Mail.tm availability, account limits, and API behavior are external dependencies and may change independently of this project.

## Project limitations

- Automatic TON payment verification is not implemented.
- Mailbox enable/disable currently changes the local database state, while the remote helper is a placeholder.
- The avatar setting stores a Telegram photo file ID; it does not update the Mail.tm account avatar through the API.
- The notification setting is a stored preference; no automatic inbox polling or notification scheduler is present in the supplied files.
- Two-factor-authentication database fields and helper functions exist, but a complete user-facing 2FA workflow is not wired into the bot menus.
- `python-dotenv` is imported by `config.py` but is missing from the provided `requirements.txt`.
- The archive does not include a deployment service file, Docker configuration, or automated tests.

## Responsible use and privacy

Email addresses, passwords, and access tokens are stored in the local SQLite database. Protect `bot_mail.db`, restrict server access, and do not share database exports because they may contain sensitive mailbox credentials. Use strong server security and back up the database securely.

Use the bot and Mail.tm service in accordance with their terms and applicable laws. Do not use generated mailboxes for spam, abuse, impersonation, or bypassing service restrictions.

## Credits

**VEGA & Logic**  
Developer: [@TopVeGa](https://t.me/TopVeGa)

Third-party services and libraries remain the property of their respective owners. Review their terms and licenses before redistribution.

---

<!-- ═══════════════════════════════════════════════════════════════════════ -->
<!--                       Copyright | Footer                              -->
<!-- ═══════════════════════════════════════════════════════════════════════ -->
<div align="center">
  <img src="https://capsule-render.vercel.app/api?type=rect&color=0:3B82F6,100:0F172A&height=4&width=40%&section=header" />
  <br><br>
  <p style="color: #9CA3AF; font-size: 14px;">
    <b style="color: #3B82F6;">Brand:</b> VEGA &amp; Logic &nbsp;|&nbsp;
    <b style="color: #3B82F6;">Copyright:</b> © 2015 - 2025
  </p>
  <p style="color: #6B7280; font-size: 12px;">
  </p>
</div>
<br>
<!-- Smooth Gradient Footer Background -->
<img src="https://capsule-render.vercel.app/api?type=waving&color=0:3B82F6,50:1E3A8A,100:0F172A&height=120&section=footer" width="100%" />
