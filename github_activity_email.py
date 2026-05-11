#!/usr/bin/env python3
"""
GitHub Public Activity -> QQ Mail Email Notifier

This script checks a GitHub user's public activity via:
    GET https://api.github.com/users/<username>/events/public

It remembers event IDs in a local state file and emails you through QQ Mail SMTP
when new public events appear.

Windows-friendly usage:
    1. Run setup_venv.bat
    2. Edit config.json
    3. Run send_test_email.bat
    4. Run run_once_visible.bat
    5. Run install_windows_task.bat to check every 10 minutes
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import smtplib
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from email.header import Header
from email.mime.text import MIMEText
from email.utils import formataddr
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import requests


APP_NAME = "github-activity-email-qq"
DEFAULT_CONFIG_FILE = "config.json"


# -----------------------------
# Configuration data structures
# -----------------------------

@dataclass
class GithubConfig:
    usernames_to_watch: List[str]
    token: str
    api_version: str
    events_per_page: int
    notify_event_types: List[str]
    ignore_repos: List[str]


@dataclass
class EmailConfig:
    smtp_host: str
    smtp_port: int
    use_ssl: bool
    use_starttls: bool
    sender: str
    sender_name: str
    auth_code: str
    recipients: List[str]
    subject_prefix: str


@dataclass
class RuntimeConfig:
    state_file: str
    log_file: str
    first_run_behavior: str
    max_seen_ids: int
    request_timeout_seconds: int


@dataclass
class AppConfig:
    github: GithubConfig
    email: EmailConfig
    runtime: RuntimeConfig


# -----------------------------
# Utility functions
# -----------------------------

def app_dir() -> Path:
    """Return the folder containing this script."""
    return Path(__file__).resolve().parent


def resolve_path(path_text: str) -> Path:
    """Resolve relative paths against the script folder."""
    path = Path(path_text)
    if path.is_absolute():
        return path
    return app_dir() / path


def load_json_file(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json_file(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    with temp_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    temp_path.replace(path)


def require_string(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Missing or invalid config value: {name}")
    return value.strip()


def as_string(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def as_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def as_bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    return default


def as_string_list(value: Any) -> List[str]:
    if not value:
        return []
    if not isinstance(value, list):
        raise ValueError("Expected a list of strings.")
    return [str(item).strip() for item in value if str(item).strip()]


def load_config(config_path: Path) -> AppConfig:
    if not config_path.exists():
        example_path = app_dir() / "config.example.json"
        message = (
            f"Cannot find {config_path}.\n\n"
            f"Copy config.example.json to config.json, then edit your GitHub username "
            f"and QQ Mail settings.\n\n"
            f"Example file: {example_path}"
        )
        raise FileNotFoundError(message)

    raw = load_json_file(config_path)

    github_raw = raw.get("github", {})
    email_raw = raw.get("email", {})
    runtime_raw = raw.get("runtime", {})

    usernames_raw = github_raw.get("usernames_to_watch", github_raw.get("username_to_watch"))

    if isinstance(usernames_raw, list):
        usernames_to_watch = as_string_list(usernames_raw)
    else:
        usernames_to_watch = [
            require_string(usernames_raw, "github.usernames_to_watch")
        ]

    github = GithubConfig(
        usernames_to_watch=usernames_to_watch,
        token=as_string(github_raw.get("token"), "").strip(),
        api_version=as_string(github_raw.get("api_version"), "2022-11-28").strip(),
        events_per_page=max(1, min(as_int(github_raw.get("events_per_page"), 30), 100)),
        notify_event_types=as_string_list(github_raw.get("notify_event_types")),
        ignore_repos=as_string_list(github_raw.get("ignore_repos")),
    )

    email = EmailConfig(
        smtp_host=as_string(email_raw.get("smtp_host"), "smtp.qq.com").strip(),
        smtp_port=as_int(email_raw.get("smtp_port"), 465),
        use_ssl=as_bool(email_raw.get("use_ssl"), True),
        use_starttls=as_bool(email_raw.get("use_starttls"), False),
        sender=as_string(email_raw.get("sender"), "").strip(),
        sender_name=as_string(email_raw.get("sender_name"), "GitHub Activity Monitor").strip(),
        auth_code=as_string(email_raw.get("auth_code"), "").strip(),
        recipients=as_string_list(email_raw.get("recipients")),
        subject_prefix=as_string(email_raw.get("subject_prefix"), "[GitHub Activity]").strip(),
    )

    runtime = RuntimeConfig(
        state_file=as_string(runtime_raw.get("state_file"), "data/state.json"),
        log_file=as_string(runtime_raw.get("log_file"), "data/monitor.log"),
        first_run_behavior=as_string(runtime_raw.get("first_run_behavior"), "record_only").strip(),
        max_seen_ids=max(100, as_int(runtime_raw.get("max_seen_ids"), 500)),
        request_timeout_seconds=max(5, as_int(runtime_raw.get("request_timeout_seconds"), 20)),
    )

    return AppConfig(github=github, email=email, runtime=runtime)


def setup_logging(log_file: Path, verbose: bool = False) -> None:
    log_file.parent.mkdir(parents=True, exist_ok=True)

    level = logging.DEBUG if verbose else logging.INFO
    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    root = logging.getLogger()
    root.setLevel(level)

    # Clear handlers to avoid duplicate logs if called from tests.
    root.handlers.clear()

    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)
    console.setLevel(level)

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)

    root.addHandler(console)
    root.addHandler(file_handler)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# -----------------------------
# State management
# -----------------------------

def default_user_state() -> Dict[str, Any]:
    return {
        "seen_ids": [],
        "etag": None,
        "last_run_at": None,
        "last_success_at": None,
        "last_poll_interval_seconds": None,
    }


def default_state() -> Dict[str, Any]:
    return {
        "users": {}
    }


def get_user_state(state: Dict[str, Any], username: str) -> Dict[str, Any]:
    users = state.setdefault("users", {})

    merged = default_user_state()
    merged.update(users.get(username, {}))

    if not isinstance(merged.get("seen_ids"), list):
        merged["seen_ids"] = []

    users[username] = merged
    return merged


def load_state(state_file: Path) -> Dict[str, Any]:
    if not state_file.exists():
        return default_state()

    try:
        state = load_json_file(state_file)
    except json.JSONDecodeError:
        backup = state_file.with_suffix(".broken.json")
        state_file.replace(backup)
        logging.warning("State file was invalid JSON. Backed it up to %s.", backup)
        return default_state()

    merged = default_state()
    merged.update(state)
    if not isinstance(merged.get("seen_ids"), list):
        merged["seen_ids"] = []
    return merged


def save_state(state_file: Path, state: Dict[str, Any]) -> None:
    write_json_file(state_file, state)


def maybe_save_state(state_file: Path, state: Dict[str, Any], dry_run: bool) -> None:
    """Save state unless this is a dry run."""
    if dry_run:
        logging.info("Dry run enabled. State file was not changed.")
        return
    save_state(state_file, state)


# -----------------------------
# GitHub API
# -----------------------------

def build_github_headers(config: GithubConfig, etag: Optional[str]) -> Dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": APP_NAME,
        "X-GitHub-Api-Version": config.api_version,
    }

    if config.token:
        headers["Authorization"] = f"Bearer {config.token}"

    if etag:
        headers["If-None-Match"] = etag

    return headers


def fetch_public_events(
    config: GithubConfig,
    username: str,
    etag: Optional[str],
    timeout_seconds: int,
) -> Tuple[List[Dict[str, Any]], Optional[str], Optional[int], bool]:
    """
    Return:
        events, new_etag, poll_interval_seconds, not_modified
    """
    url = f"https://api.github.com/users/{username}/events/public"
    params = {"per_page": config.events_per_page}
    headers = build_github_headers(config, etag)

    logging.info("Checking GitHub public events for user '%s'.", username)
    response = requests.get(url, headers=headers, params=params, timeout=timeout_seconds)

    poll_interval_raw = response.headers.get("X-Poll-Interval")
    poll_interval = None
    if poll_interval_raw:
        try:
            poll_interval = int(poll_interval_raw)
        except ValueError:
            poll_interval = None

    if response.status_code == 304:
        logging.info("GitHub returned 304 Not Modified. No new events.")
        return [], etag, poll_interval, True

    if response.status_code == 404:
        raise RuntimeError(
            f"GitHub user '{username}' was not found, "
            "or the events endpoint is unavailable for this user."
        )

    if response.status_code == 403:
        rate_remaining = response.headers.get("X-RateLimit-Remaining")
        rate_reset = response.headers.get("X-RateLimit-Reset")
        raise RuntimeError(
            "GitHub returned 403 Forbidden. This is often a rate-limit issue. "
            f"X-RateLimit-Remaining={rate_remaining}, X-RateLimit-Reset={rate_reset}. "
            "Add a GitHub token in config.json or run less frequently."
        )

    response.raise_for_status()

    events = response.json()
    if not isinstance(events, list):
        raise RuntimeError("Unexpected GitHub API response: expected a JSON list.")

    new_etag = response.headers.get("ETag")
    logging.info("Fetched %d event(s) from GitHub.", len(events))
    return events, new_etag, poll_interval, False

def fetch_compare(
    config: GithubConfig,
    repo: str,
    before: str,
    head: str,
    timeout_seconds: int,
) -> Dict[str, Any]:
    url = f"https://api.github.com/repos/{repo}/compare/{before}...{head}"
    headers = build_github_headers(config, etag=None)

    response = requests.get(url, headers=headers, timeout=timeout_seconds)
    response.raise_for_status()
    return response.json()

# -----------------------------
# Event formatting and filtering
# -----------------------------

def repo_name(event: Dict[str, Any]) -> str:
    return event.get("repo", {}).get("name") or "unknown/repo"


def repo_url(repo: str) -> str:
    if "/" in repo:
        return f"https://github.com/{repo}"
    return ""


def event_created_at(event: Dict[str, Any]) -> str:
    return as_string(event.get("created_at"), "unknown time")


def should_notify(event: Dict[str, Any], github: GithubConfig) -> bool:
    event_type = as_string(event.get("type"), "")
    repo = repo_name(event)

    if github.notify_event_types and event_type not in set(github.notify_event_types):
        return False

    if github.ignore_repos and repo in set(github.ignore_repos):
        return False

    return True


def summarize_push_event(
    event: Dict[str, Any],
    github: GithubConfig,
    timeout_seconds: int,
) -> List[str]:
    payload = event.get("payload", {}) or {}
    repo = repo_name(event)
    lines = []

    ref = as_string(payload.get("ref"), "")
    if ref:
        lines.append(f"Branch/ref: {ref}")

    commits = payload.get("commits", []) or []
    lines.append(f"Commits included in event payload: {len(commits)}")

    before = as_string(payload.get("before"), "")
    head = as_string(payload.get("head"), "")
    zero_sha = "0" * 40

    if not commits and before and head and before != zero_sha and "/" in repo:
        try:
            compare = fetch_compare(github, repo, before, head, timeout_seconds)
            compare_commits = compare.get("commits", []) or []
            lines.append(f"Commits found by compare API: {len(compare_commits)}")

            commits = [
                {
                    "sha": c.get("sha", ""),
                    "message": c.get("commit", {}).get("message", ""),
                    "author": c.get("commit", {}).get("author", {}),
                }
                for c in compare_commits
            ]

            lines.append(f"Compare URL: https://github.com/{repo}/compare/{before}...{head}")

        except requests.RequestException as exc:
            lines.append("Could not fetch commit details from compare API.")
            lines.append(f"Reason: {exc}")

    before = as_string(payload.get("before"), "")
    head = as_string(payload.get("head"), "")

    if head and "/" in repo:
        lines.append(f"Head commit: {head[:7]}")
        lines.append(f"Head commit URL: https://github.com/{repo}/commit/{head}")

    if before and head and "/" in repo:
        zero_sha = "0" * 40
        if before != zero_sha:
            lines.append(f"Compare URL: https://github.com/{repo}/compare/{before}...{head}")

    for commit in commits[:10]:
        sha = as_string(commit.get("sha"), "")
        short_sha = sha[:7] if sha else "unknown"
        message = as_string(commit.get("message"), "").splitlines()[0]
        author = commit.get("author", {}) or {}
        author_name = as_string(author.get("name"), "")
        commit_url = f"https://github.com/{repo}/commit/{sha}" if sha and "/" in repo else ""

        bullet = f"- {short_sha}"
        if author_name:
            bullet += f" by {author_name}"
        if message:
            bullet += f": {message}"
        if commit_url:
            bullet += f"\n  {commit_url}"

        lines.append(bullet)

    if len(commits) > 10:
        lines.append(f"...and {len(commits) - 10} more commit(s).")

    return lines


def summarize_event(
    event: Dict[str, Any],
    github: GithubConfig,
    timeout_seconds: int,
) -> str:
    event_type = as_string(event.get("type"), "UnknownEvent")
    actor = event.get("actor", {}) or {}
    actor_login = as_string(actor.get("login"), "unknown")
    repo = repo_name(event)
    payload = event.get("payload", {}) or {}

    lines = [
        f"Type: {event_type}",
        f"User: {actor_login}",
        f"Repo: {repo}",
        f"Time: {event_created_at(event)}",
    ]

    r_url = repo_url(repo)
    if r_url:
        lines.append(f"Repo URL: {r_url}")

    if event_type == "PushEvent":
        lines.extend(summarize_push_event(event, github, timeout_seconds))

    elif event_type == "PullRequestEvent":
        pr = payload.get("pull_request", {}) or {}
        lines.append(f"Action: {as_string(payload.get('action'), '')}")
        lines.append(f"PR: {as_string(pr.get('title'), '')}")
        if pr.get("html_url"):
            lines.append(f"URL: {pr.get('html_url')}")

    elif event_type == "PullRequestReviewEvent":
        review = payload.get("review", {}) or {}
        pr = payload.get("pull_request", {}) or {}
        lines.append(f"Action: {as_string(payload.get('action'), '')}")
        lines.append(f"PR: {as_string(pr.get('title'), '')}")
        lines.append(f"Review state: {as_string(review.get('state'), '')}")
        if review.get("html_url"):
            lines.append(f"URL: {review.get('html_url')}")

    elif event_type == "PullRequestReviewCommentEvent":
        comment = payload.get("comment", {}) or {}
        pr = payload.get("pull_request", {}) or {}
        lines.append(f"Action: {as_string(payload.get('action'), '')}")
        lines.append(f"PR: {as_string(pr.get('title'), '')}")
        if comment.get("html_url"):
            lines.append(f"Comment URL: {comment.get('html_url')}")

    elif event_type == "IssuesEvent":
        issue = payload.get("issue", {}) or {}
        lines.append(f"Action: {as_string(payload.get('action'), '')}")
        lines.append(f"Issue: {as_string(issue.get('title'), '')}")
        if issue.get("html_url"):
            lines.append(f"URL: {issue.get('html_url')}")

    elif event_type == "IssueCommentEvent":
        issue = payload.get("issue", {}) or {}
        comment = payload.get("comment", {}) or {}
        lines.append(f"Action: {as_string(payload.get('action'), '')}")
        lines.append(f"Issue: {as_string(issue.get('title'), '')}")
        if comment.get("html_url"):
            lines.append(f"Comment URL: {comment.get('html_url')}")

    elif event_type == "ReleaseEvent":
        release = payload.get("release", {}) or {}
        lines.append(f"Action: {as_string(payload.get('action'), '')}")
        lines.append(f"Release: {as_string(release.get('name') or release.get('tag_name'), '')}")
        if release.get("html_url"):
            lines.append(f"URL: {release.get('html_url')}")

    elif event_type == "CreateEvent":
        lines.append(f"Created: {as_string(payload.get('ref_type'), '')}")
        if payload.get("ref"):
            lines.append(f"Ref: {payload.get('ref')}")

    elif event_type == "DeleteEvent":
        lines.append(f"Deleted: {as_string(payload.get('ref_type'), '')}")
        if payload.get("ref"):
            lines.append(f"Ref: {payload.get('ref')}")

    elif event_type == "ForkEvent":
        forkee = payload.get("forkee", {}) or {}
        lines.append("Action: forked a repository")
        if forkee.get("html_url"):
            lines.append(f"Fork URL: {forkee.get('html_url')}")

    elif event_type == "WatchEvent":
        lines.append("Action: starred a repository")

    elif event_type == "PublicEvent":
        lines.append("Action: made a repository public")

    else:
        # Keep the fallback short. The raw payload can be very large.
        action = payload.get("action")
        if action:
            lines.append(f"Action: {action}")
        lines.append("Details: This event type is not specially formatted yet.")

    return "\n".join(lines)


def build_email_body(
    username: str,
    new_events: List[Dict[str, Any]],
    github: GithubConfig,
    timeout_seconds: int,
) -> str:
    plural = "event" if len(new_events) == 1 else "events"
    header = [
        f"New public GitHub activity detected for: {username}",
        f"New {plural}: {len(new_events)}",
        "",
        "Note: GitHub Events API is public-activity based and may not be real-time.",
        "",
    ]

    sections = []
    for i, event in enumerate(new_events, start=1):
        sections.append(f"#{i}\n{summarize_event(event, github, timeout_seconds)}")

    separator = "\n\n" + ("-" * 60) + "\n\n"
    if sections:
        return "\n".join(header) + separator + separator.join(sections)
    return "\n".join(header)


# -----------------------------
# Email sending
# -----------------------------

def validate_email_config(email: EmailConfig) -> None:
    missing = []
    if not email.smtp_host:
        missing.append("email.smtp_host")
    if not email.smtp_port:
        missing.append("email.smtp_port")
    if not email.sender:
        missing.append("email.sender")
    if not email.auth_code:
        missing.append("email.auth_code")
    if not email.recipients:
        missing.append("email.recipients")

    if missing:
        raise ValueError("Missing email config values: " + ", ".join(missing))


def send_email(email: EmailConfig, subject: str, body: str) -> None:
    validate_email_config(email)

    message = MIMEText(body, "plain", "utf-8")
    message["Subject"] = str(Header(subject, "utf-8"))
    message["From"] = formataddr((str(Header(email.sender_name, "utf-8")), email.sender))
    message["To"] = ", ".join(email.recipients)

    logging.info("Sending email to %s through %s:%s.", ", ".join(email.recipients), email.smtp_host, email.smtp_port)

    if email.use_ssl:
        with smtplib.SMTP_SSL(email.smtp_host, email.smtp_port, timeout=30) as server:
            server.login(email.sender, email.auth_code)
            server.sendmail(email.sender, email.recipients, message.as_string())
    else:
        with smtplib.SMTP(email.smtp_host, email.smtp_port, timeout=30) as server:
            server.ehlo()
            if email.use_starttls:
                server.starttls()
                server.ehlo()
            server.login(email.sender, email.auth_code)
            server.sendmail(email.sender, email.recipients, message.as_string())

    logging.info("Email sent successfully.")


def send_test_email(config: AppConfig, dry_run: bool) -> None:
    subject = f"{config.email.subject_prefix} Test email"
    body = (
        "This is a test email from GitHub Activity Email QQ.\n\n"
        "If you received this, your QQ Mail SMTP configuration is working.\n\n"
        f"Time: {now_iso()}\n"
    )

    if dry_run:
        print("DRY RUN: would send this email:")
        print("Subject:", subject)
        print(body)
        return

    send_email(config.email, subject, body)


# -----------------------------
# Main monitor workflow
# -----------------------------

def get_new_events(
    events: List[Dict[str, Any]],
    seen_ids: Iterable[str],
    github: GithubConfig,
) -> List[Dict[str, Any]]:
    seen = set(seen_ids)
    new_events = []

    # GitHub usually returns newest first. We later reverse so the email reads oldest -> newest.
    for event in events:
        event_id = as_string(event.get("id"), "")
        if not event_id:
            continue
        if event_id in seen:
            continue
        if not should_notify(event, github):
            continue
        new_events.append(event)

    new_events.reverse()
    return new_events


def update_seen_ids(
    old_seen_ids: Iterable[str],
    fetched_events: List[Dict[str, Any]],
    max_seen_ids: int,
) -> List[str]:
    # Put newest fetched IDs first, then older saved IDs, while preserving uniqueness.
    combined = []
    seen = set()

    for event in fetched_events:
        event_id = as_string(event.get("id"), "")
        if event_id and event_id not in seen:
            combined.append(event_id)
            seen.add(event_id)

    for event_id in old_seen_ids:
        event_id = as_string(event_id, "")
        if event_id and event_id not in seen:
            combined.append(event_id)
            seen.add(event_id)

    return combined[:max_seen_ids]


def run_monitor(config: AppConfig, dry_run: bool = False) -> int:
    state_file = resolve_path(config.runtime.state_file)
    state = load_state(state_file)

    exit_code = 0

    for username in config.github.usernames_to_watch:
        user_state = get_user_state(state, username)

        old_seen_ids = user_state.get("seen_ids", [])
        was_first_run = len(old_seen_ids) == 0 and not user_state.get("last_success_at")

        try:
            events, new_etag, poll_interval, not_modified = fetch_public_events(
                config.github,
                username=username,
                etag=user_state.get("etag"),
                timeout_seconds=config.runtime.request_timeout_seconds,
            )

            user_state["last_run_at"] = now_iso()

            if poll_interval is not None:
                user_state["last_poll_interval_seconds"] = poll_interval
                logging.info(
                    "GitHub X-Poll-Interval for %s: %s seconds.",
                    username,
                    poll_interval,
                )

            if not_modified:
                continue

            if was_first_run and config.runtime.first_run_behavior == "record_only":
                logging.info(
                    "First run detected for %s. Recording current events without sending an email.",
                    username,
                )
                user_state["seen_ids"] = update_seen_ids(
                    old_seen_ids,
                    events,
                    config.runtime.max_seen_ids,
                )
                user_state["etag"] = new_etag or user_state.get("etag")
                user_state["last_success_at"] = now_iso()
                continue

            new_events = get_new_events(events, old_seen_ids, config.github)
            logging.info(
                "Detected %d new notifiable event(s) for %s.",
                len(new_events),
                username,
            )

            if new_events:
                subject = f"{config.email.subject_prefix} {len(new_events)} new event(s) from {username}"
                body = build_email_body(
                    username,
                    new_events,
                    config.github,
                    config.runtime.request_timeout_seconds,
                )

                if dry_run:
                    print("DRY RUN: would send this email:")
                    print("=" * 80)
                    print("Subject:", subject)
                    print(body)
                    print("=" * 80)
                else:
                    send_email(config.email, subject, body)
            else:
                logging.info("No email needed for %s.", username)

            user_state["seen_ids"] = update_seen_ids(
                old_seen_ids,
                events,
                config.runtime.max_seen_ids,
            )
            user_state["etag"] = new_etag or user_state.get("etag")
            user_state["last_success_at"] = now_iso()

        except Exception:
            logging.exception("Failed to monitor GitHub user '%s'.", username)
            exit_code = 1

    maybe_save_state(state_file, state, dry_run)
    return exit_code


def create_config_from_example(config_path: Path) -> int:
    example_path = app_dir() / "config.example.json"
    if config_path.exists():
        print(f"{config_path} already exists. Not overwriting.")
        return 0
    if not example_path.exists():
        print(f"Cannot find {example_path}.")
        return 1

    config_path.write_text(example_path.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"Created {config_path}. Please edit it before running the monitor.")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Email yourself through QQ Mail when a GitHub user's public activity changes."
    )
    parser.add_argument(
        "--config",
        default=DEFAULT_CONFIG_FILE,
        help="Path to config.json. Default: config.json next to this script.",
    )
    parser.add_argument(
        "--init-config",
        action="store_true",
        help="Create config.json from config.example.json if config.json does not exist.",
    )
    parser.add_argument(
        "--send-test",
        action="store_true",
        help="Send a test email using the QQ Mail SMTP settings.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Do everything except actually send email.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print more detailed logs.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = app_dir() / config_path

    if args.init_config:
        return create_config_from_example(config_path)

    # Before config is loaded, log to a safe default.
    default_log_file = app_dir() / "data" / "monitor.log"
    setup_logging(default_log_file, verbose=args.verbose)

    try:
        config = load_config(config_path)
        setup_logging(resolve_path(config.runtime.log_file), verbose=args.verbose)

        if args.send_test:
            send_test_email(config, dry_run=args.dry_run)
            return 0

        return run_monitor(config, dry_run=args.dry_run)

    except KeyboardInterrupt:
        print("\nCancelled.")
        return 130
    except Exception as exc:
        logging.exception("Failed: %s", exc)
        print()
        print("ERROR:", exc)
        print("Check README.md and data/monitor.log for details.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
