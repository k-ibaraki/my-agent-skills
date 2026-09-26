---
name: github-activity-report
description: Generate a Markdown report of GitHub activities (issues, PRs) for a specified date or period. Use when the user asks for GitHub activity summary, their work history, contribution report, or wants to see what they did on GitHub on specific dates like "today", "yesterday", "last week", "last Friday", or date ranges like "this week" or "from April 1 to April 5". Also use when they mention wanting to generate reports for standups, retrospectives, or tracking their contributions.
license: MIT
---

# GitHub Activity Report

You interpret the user's date/period and repository yourself; leave fetching the activities and building the report to the bundled script.

## Step 1: Get the reference time

```bash
TZ=Asia/Tokyo date '+%Y-%m-%d %A'
```

Use this date and weekday as the anchor for all relative expressions.

## Step 2: Interpret the request

### A. Date range

Convert to **YYYY-MM-DD**. Be generous with Japanese date expressions, and prefer calendar-based interpretation over rolling windows:

- **今日** / **昨日** / **2週間前** → that single day as both start and end
- **先週** → the calendar week (Mon-Sun) *before* the current week, NOT a rolling 7 days
- **今週** → this Monday through today
- **先月** → all days of the previous month
- **先週の金曜** / a bare day name → the most recent past occurrence of that weekday
- **4月1日から4月10日** → April 1 to April 10; a month without a year means the current year unless context says otherwise

If the expression is ambiguous, ask before running the script and offer concrete readings: "Did you mean last week (April 1-7) or the past 7 days?" For ranges, state your interpretation explicitly and confirm.

### B. Repository

Nothing specified → the current directory's repo (`gh repo view --json nameWithOwner -q .nameWithOwner`). `owner/repo` → use as-is. A GitHub URL → extract `owner/repo` from it. A bare repo name that is ambiguous → ask.

## Step 3: Fetch the activities

```bash
python ~/.claude/skills/github-activity-report/scripts/fetch_activity.py \
  --start-date YYYY-MM-DD \
  --end-date YYYY-MM-DD \
  --repo owner/repo \
  [--format slack]
```

Add `--format slack` when the user mentions **Slack**, **スラック**, **貼り付け**, or similar; otherwise the default markdown format applies. The script fetches the activities, groups actions by issue/PR number, and writes the complete report to stdout.

| Feature | markdown | slack |
|---------|----------|-------|
| Headers | `## Section` | `*Section*` |
| Bold | `**text**` | `*text*` |
| List items | `- item` | `• item` |
| Links | `[text](url)` | `<url\|text>` (clickable in Slack) |

## Step 4: Present the report

**IMPORTANT**: You MUST wrap the entire script output in a code block (triple backticks). Do NOT render it as markdown — that makes Claude Code add unwanted indentation to list items.

````
```
<script output here>
```
````

For **Slack format**, remind the user to paste the content without the code block markers. If the script outputs "No activities found for this period", tell the user there were no activities in that range.

## Error handling

| Symptom | Check | Fix |
|---|---|---|
| gh not available | `which gh` | Have the user install GitHub CLI |
| Not authenticated | `gh auth status` | Have the user run `gh auth login` |
| Invalid repository | script error output | Help correct the repo specification |
| API rate limit | script error output | Suggest waiting (requests are already authenticated) |
