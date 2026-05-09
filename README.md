# GitHub Activity Email Notifier for Windows + QQ Mail

This project watches a GitHub user's **public activity** and sends an email through **QQ Mail** when new public activity appears.

It uses this GitHub API endpoint:

```http
GET https://api.github.com/users/<username>/events/public
```

The project is designed for Windows and includes batch files for setup, testing, manual running, and Windows Task Scheduler.

---

## 1. What this project does

Every time it runs, the script:

1. Calls GitHub's public user events API.
2. Reads the local state file at `data/state.json`.
3. Compares the latest GitHub event IDs with IDs already seen.
4. Sends an email through QQ Mail if there are new events.
5. Saves the latest event IDs and GitHub `ETag`.

It can detect public GitHub activity such as:

- `PushEvent`
- `PullRequestEvent`
- `IssuesEvent`
- `IssueCommentEvent`
- `ReleaseEvent`
- `CreateEvent`
- `DeleteEvent`
- `ForkEvent`
- `WatchEvent`
- and other public event types

---

## 2. Important limitations

### Public activity only

This project uses:

```http
GET /users/<username>/events/public
```

That means it only checks **public** GitHub activity.

It cannot see private repository activity of another user.

### Not real-time

GitHub's Events API is designed for polling, but it is not guaranteed to be instant. GitHub may delay events. The script also respects GitHub's polling model by using `ETag`.

### First run does not send old events

By default:

```json
"first_run_behavior": "record_only"
```

On the first run, the script records current events but does **not** send an email for old activity. This prevents your mailbox from receiving a batch of historical events.

If you want an email even on the first run, change it to:

```json
"first_run_behavior": "notify"
```

---

## 3. Folder structure

```text
github_activity_email_windows_qq/
├─ github_activity_email.py        Main Python script
├─ config.example.json             Example configuration
├─ requirements.txt                Python dependencies
├─ setup_venv.bat                  Creates virtual environment and installs dependencies
├─ run_once.bat                    Runs once, for Task Scheduler
├─ run_once_visible.bat            Runs once and keeps the window open
├─ send_test_email.bat             Sends a QQ Mail test email
├─ install_windows_task.bat        Adds a Windows scheduled task, every 10 minutes
├─ uninstall_windows_task.bat      Removes the scheduled task
├─ run_monitor_loop.bat            Optional always-on loop, checks every 10 minutes
├─ .gitignore                      Prevents secrets and runtime files from being committed
├─ data/
│  └─ .gitkeep                     Placeholder folder for logs and state
└─ README.md                       This guide
```

---

## 4. Requirements

You need:

- Windows 10 or Windows 11
- Python 3.9 or newer
- A QQ Mail account
- QQ Mail SMTP service enabled
- A QQ Mail authorization code
- Optional but recommended: a GitHub personal access token

---

## 5. Install Python on Windows

Open PowerShell or Command Prompt and check:

```bat
python --version
```

If Python is not installed, install it from:

```text
https://www.python.org/downloads/windows/
```

During installation, select:

```text
Add python.exe to PATH
```

---

## 6. Set up the project

Unzip the project.

Open the project folder.

Double-click:

```text
setup_venv.bat
```

This will:

1. Create `.venv`
2. Install Python dependencies
3. Create `config.json` from `config.example.json` if it does not already exist

---

## 7. Configure QQ Mail

Open:

```text
config.json
```

Find this section:

```json
"email": {
  "smtp_host": "smtp.qq.com",
  "smtp_port": 465,
  "use_ssl": true,
  "use_starttls": false,
  "sender": "123456789@qq.com",
  "sender_name": "GitHub Activity Monitor",
  "auth_code": "paste_your_QQ_mail_authorization_code_here",
  "recipients": [
    "123456789@qq.com"
  ],
  "subject_prefix": "[GitHub Activity]"
}
```

Change:

```json
"sender": "123456789@qq.com"
```

to your QQ email address.

Change:

```json
"auth_code": "paste_your_QQ_mail_authorization_code_here"
```

to your QQ Mail authorization code.

Change:

```json
"recipients": [
  "123456789@qq.com"
]
```

to the email address that should receive notifications. It can be the same QQ email address.

### QQ Mail SMTP notes

QQ Mail commonly uses:

```text
SMTP server: smtp.qq.com
SSL port: 465
```

This project uses port `465` with SSL by default.

If you prefer port `587`, use:

```json
"smtp_port": 587,
"use_ssl": false,
"use_starttls": true
```

### Where to get the QQ Mail authorization code

In QQ Mail, enable SMTP/POP3 service and generate an authorization code.

Usually the path is similar to:

```text
QQ Mail -> Settings -> Account -> POP3/IMAP/SMTP/Exchange/CardDAV/CalDAV Service
```

Then enable the SMTP-related service and generate an authorization code.

Use the authorization code in `config.json`, not your normal QQ password.

---

## 8. Configure the GitHub user to watch

In `config.json`, find:

```json
"github": {
  "username_to_watch": "octocat",
  "token": "",
  "api_version": "2022-11-28",
  "events_per_page": 30,
  "notify_event_types": [],
  "ignore_repos": []
}
```

Change:

```json
"username_to_watch": "octocat"
```

to the GitHub username you want to monitor.

Example:

```json
"username_to_watch": "torvalds"
```

---

## 9. Optional: add a GitHub token

For one user checked every 10 minutes, you may not need a token.

However, a token is recommended because GitHub applies stricter rate limits to unauthenticated requests.

Create a GitHub token and put it here:

```json
"token": "github_pat_xxxxxxxxxxxxxxxxx"
```

For this public events endpoint, no special permission is needed if you only monitor public activity.

Never share your GitHub token.

---

## 10. Test QQ Mail sending

Double-click:

```text
send_test_email.bat
```

If the configuration is correct, you should receive a test email.

If it fails, check:

```text
data/monitor.log
```

Common causes:

- SMTP service is not enabled in QQ Mail
- You used your normal QQ password instead of authorization code
- Wrong sender email
- Firewall or network blocking SMTP
- Wrong SSL/TLS settings

---

## 11. Run the monitor once

Double-click:

```text
run_once_visible.bat
```

On the first run, the script usually says it recorded current events without sending an email.

This is normal because the default first-run behavior is:

```json
"first_run_behavior": "record_only"
```

The next time the watched user has new public GitHub activity, you should receive an email.

---

## 12. Run automatically every 10 minutes

Double-click:

```text
install_windows_task.bat
```

This creates a Windows scheduled task named:

```text
GitHubActivityEmailQQ
```

It runs:

```text
run_once.bat
```

every 10 minutes.

To remove the scheduled task, double-click:

```text
uninstall_windows_task.bat
```

---

## 13. Optional: run in a loop instead of Task Scheduler

You can also double-click:

```text
run_monitor_loop.bat
```

This keeps a command window open and checks every 10 minutes.

Task Scheduler is usually better because it continues working after reboot if configured correctly.

---

## 14. Filtering event types

By default:

```json
"notify_event_types": []
```

An empty list means notify for all event types.

To notify only for pushes and pull requests:

```json
"notify_event_types": [
  "PushEvent",
  "PullRequestEvent"
]
```

To ignore certain repositories:

```json
"ignore_repos": [
  "some-user/some-repo"
]
```

---

## 15. How the code works

### `load_config`

Reads `config.json`, validates important fields, and converts it into Python dataclasses.

### `fetch_public_events`

Calls GitHub:

```http
GET https://api.github.com/users/<username>/events/public
```

It sends:

- `Accept: application/vnd.github+json`
- `User-Agent`
- optional `Authorization`
- optional `If-None-Match`

If GitHub returns:

```http
304 Not Modified
```

the script knows there is no new activity.

### `get_new_events`

Compares the latest GitHub event IDs against `data/state.json`.

Only unseen events are considered new.

### `summarize_event`

Turns a GitHub event into a readable email section.

For example, for `PushEvent`, it includes:

- repository
- branch/ref
- commit count
- commit messages
- commit URLs

For pull requests, issues, releases, and comments, it includes the most useful URL when GitHub provides one.

### `send_email`

Sends the email with Python's built-in `smtplib`.

For QQ Mail default config, it connects to:

```text
smtp.qq.com:465
```

using SSL.

### `save_state`

Writes the current state to:

```text
data/state.json
```

The state includes:

- seen event IDs
- GitHub `ETag`
- last run time
- last successful run time
- last `X-Poll-Interval`

---

## 16. Security notes

Your `config.json` contains secrets:

- QQ Mail authorization code
- optional GitHub token

Do not upload `config.json` to GitHub.

The included `.gitignore` excludes:

```text
config.json
data/
.venv/
```

---

## 17. Troubleshooting

### I do not receive email

Check:

```text
data/monitor.log
```

Then verify:

- QQ SMTP service is enabled
- Authorization code is correct
- `sender` is your QQ email
- `recipients` contains a valid email
- Port `465` is not blocked by your network

### It says `GitHub returned 403 Forbidden`

Possible causes:

- Rate limit
- Network restriction
- Bad token

Try adding a GitHub token or run less often.

### It sends no email even though the user has activity

Possible causes:

- First run only recorded events
- Activity is private
- GitHub has not exposed the event yet
- You filtered the event type
- You ignored the repository

### I want to reset the monitor

Delete:

```text
data/state.json
```

Then run the monitor again.

Be aware that if `first_run_behavior` is set to `notify`, it may email current events after reset.

---

## 18. Useful commands

Run once:

```bat
.venv\Scripts\python.exe github_activity_email.py
```

Dry run without sending email:

```bat
.venv\Scripts\python.exe github_activity_email.py --dry-run
```

Send test email:

```bat
.venv\Scripts\python.exe github_activity_email.py --send-test
```

Create config from example:

```bat
.venv\Scripts\python.exe github_activity_email.py --init-config
```

Verbose logs:

```bat
.venv\Scripts\python.exe github_activity_email.py --verbose
```
