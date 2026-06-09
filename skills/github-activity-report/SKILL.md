---
name: github-activity-report
description: Generate a Markdown report of GitHub activities (issues, PRs) for a specified date or period. Use when the user asks for GitHub activity summary, their work history, contribution report, or wants to see what they did on GitHub on specific dates like "today", "yesterday", "last week", "last Friday", or date ranges like "this week" or "from April 1 to April 5". Also use when they mention wanting to generate reports for standups, retrospectives, or tracking their contributions.
license: MIT
---

# GitHub Activity Report

Generate a detailed Markdown report of GitHub activities (issues and PRs) for specified dates or periods.

## Overview

This skill helps generate activity reports by:
1. **You interpret** the user's date/period expression and repository specification
2. **Script fetches** activities from GitHub API 
3. **Script outputs** a standardized Markdown report

Your role is to handle the flexible, interpretive parts. The script handles the fixed, deterministic parts.

## Step 1: Get Current Time

First, get the current date/time in Asia/Tokyo using the date command:

```bash
TZ=Asia/Tokyo date '+%Y-%m-%d %A'
```

This gives you:
- The current date in YYYY-MM-DD format
- The day of the week (for interpreting "last Friday" etc.)

Use this as the reference point for interpreting relative dates.

## Step 2: Interpret User's Request

Parse the user's natural language request to determine:

### A. Date Range

The user might say things like:
- **今日** → today's date to today's date
- **昨日** → yesterday's date to yesterday's date  
- **先週の金曜** → the most recent past Friday to that Friday
- **先週** → previous Monday through Sunday (NOT rolling 7 days)
- **今週** → current Monday through today
- **先月** → all days of the previous month
- **4月1日から4月10日** → April 1 to April 10 of current year
- **2週間前** → 14 days ago to 14 days ago

**Important interpretation rules**:
- "先週" means the calendar week (Mon-Sun) before the current week
- For day names like "金曜", find the most recent occurrence in the past
- For month references without year, assume current year unless context suggests otherwise
- When a single day is mentioned, use that day as both start and end date

Convert the interpreted dates to **YYYY-MM-DD** format.

### B. Repository

The user might specify:
- **Nothing** → Use current directory's git repository
- **owner/repo** format → Use as-is
- **GitHub URL** → Extract owner/repo from URL
- **Just a repo name** → If ambiguous, ask for clarification

To get current directory's repo:
```bash
gh repo view --json nameWithOwner -q .nameWithOwner
```

## Step 3: Determine Output Format

Check whether the user wants Slack-friendly output:
- If the user mentions **Slack**, **スラック**, **貼り付け**, **slack format**, or similar → use `--format slack`
- Otherwise → use `--format markdown` (default)

## Step 4: Fetch Activities

Run the bundled script with the interpreted parameters:

```bash
# Default Markdown format
python ~/.claude/skills/github-activity-report/scripts/fetch_activity.py \
  --start-date YYYY-MM-DD \
  --end-date YYYY-MM-DD \
  --repo owner/repo

# Slack mrkdwn format
python ~/.claude/skills/github-activity-report/scripts/fetch_activity.py \
  --start-date YYYY-MM-DD \
  --end-date YYYY-MM-DD \
  --repo owner/repo \
  --format slack
```

The script will:
- Fetch all relevant activities from GitHub API
- Group actions by issue/PR number
- Output a complete report to stdout in the requested format

### Format differences

| Feature | markdown | slack |
|---------|----------|-------|
| Headers | `## Section` | `*Section*` |
| Bold | `**text**` | `*text*` |
| List items | `- item` | `• item` |
| Links | `[text](url)` | `<url\|text>` (clickable in Slack) |

## Step 5: Present the Report

**IMPORTANT**: You MUST wrap the entire script output in a code block (triple backticks). Do NOT render it as markdown. This is required to prevent Claude Code from adding unwanted indentation to list items.

Output it exactly like this — the outer triple backticks are mandatory:

````
```
<script output here>
```
````

For **Slack format**, remind the user to paste without the code block markers — the content inside is ready to paste directly into Slack.

If the script outputs "No activities found for this period", inform the user that there were no activities in the specified date range.

## Error Handling

### Script Errors

If the script fails, check:

1. **GitHub CLI not available**:
   - Verify: `which gh`
   - Fix: Instruct user to install GitHub CLI

2. **Not authenticated**:
   - Verify: `gh auth status`
   - Fix: Instruct user to run `gh auth login`

3. **Invalid repository**:
   - The script will output an error message
   - Help the user correct the repository specification

4. **API rate limit**:
   - The script will indicate rate limit errors
   - Suggest waiting or using authenticated requests (should already be authenticated)

### Ambiguous Requests

If the user's date expression is ambiguous or unclear:
- Ask for clarification
- Provide examples: "Did you mean last week (April 1-7) or the past 7 days?"

## Examples

**Example 1**: Simple single-day request
```
User: "今日のGitHub活動を教えて"
You: 
1. Get current time → 2026-04-11
2. Interpret: start=2026-04-11, end=2026-04-11, repo=current
3. Run script with those parameters
4. Display the output
```

**Example 2**: Period with repo specification
```
User: "先週の ncdcdev/mcp-chat-backend-api での活動"
You:
1. Get current time → 2026-04-11 (Friday)
2. Interpret: start=2026-04-07 (Mon), end=2026-04-13 (Sun), repo=ncdcdev/mcp-chat-backend-api
3. Run script
4. Display output
```

**Example 3**: Relative day name
```
User: "先週の水曜日に何をした？"
You:
1. Get current time → 2026-04-11
2. Find most recent past Wednesday → 2026-04-09
3. Interpret: start=2026-04-09, end=2026-04-09, repo=current
4. Run script
5. Display output
```

## Tips for Interpretation

- Be generous in understanding Japanese date expressions
- When in doubt about "last X", prefer calendar-based interpretation (last week = last Mon-Sun, not rolling 7 days)
- If the user mentions a day name without "last" or "this", assume they mean the most recent past occurrence
- For ranges, be explicit: "I interpreted this as April 7-13. Is that correct?" before running the script
