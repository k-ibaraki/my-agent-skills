#!/usr/bin/env python3
"""
GitHub Activity Report Generator

Fetches GitHub activities (issues and PRs) for a specified date range and repository,
then outputs a formatted Markdown report.
"""

import argparse
import json
import subprocess
import sys
from collections import defaultdict
from datetime import date, datetime
from typing import Any


def run_gh_command(args: list[str]) -> dict[str, Any]:
    """Run a gh CLI command and return JSON output."""
    try:
        result = subprocess.run(
            ["gh"] + args,
            capture_output=True,
            text=True,
            check=True,
        )
        return json.loads(result.stdout) if result.stdout.strip() else {}
    except subprocess.CalledProcessError as e:
        print(f"Error running gh command: {e.stderr}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}", file=sys.stderr)
        sys.exit(1)


def get_authenticated_user() -> str:
    """Get the currently authenticated GitHub user."""
    try:
        result = subprocess.run(
            ["gh", "api", "user", "--jq", ".login"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error getting authenticated user: {e.stderr}", file=sys.stderr)
        return "unknown"


def parse_date(date_str: str) -> datetime:
    """Parse YYYY-MM-DD date string."""
    return datetime.strptime(date_str, "%Y-%m-%d")


def state_badge(state: str) -> str:
    """Convert GitHub PR state to a human-readable badge."""
    return {"MERGED": "[Merged]", "OPEN": "[Open]", "CLOSED": "[Closed]"}.get(state, f"[{state}]")


def fetch_issues_activity(
    repo: str, username: str, start_date: date, end_date: date
) -> dict[int, dict]:
    """Fetch issue activities for the user in the date range."""
    activities = defaultdict(lambda: {"number": 0, "title": "", "url": "", "actions": []})

    # Fetch all issues (created, commented, or participated)
    issues_json = run_gh_command([
        "issue",
        "list",
        "--repo", repo,
        "--state", "all",
        "--author", username,
        "--json", "number,title,url,createdAt,closedAt,state",
        "--limit", "1000",
    ])

    for issue in issues_json:
        issue_num = issue["number"]
        created_at = datetime.fromisoformat(issue["createdAt"].replace("Z", "+00:00"))

        # Check if created in date range
        if start_date <= created_at.date() <= end_date:
            activities[issue_num]["number"] = issue_num
            activities[issue_num]["title"] = issue["title"]
            activities[issue_num]["url"] = issue["url"]
            activities[issue_num]["actions"].append("Created")

        # Check if closed in date range
        if issue.get("closedAt"):
            closed_at = datetime.fromisoformat(issue["closedAt"].replace("Z", "+00:00"))
            if start_date <= closed_at.date() <= end_date:
                activities[issue_num]["number"] = issue_num
                activities[issue_num]["title"] = issue["title"]
                activities[issue_num]["url"] = issue["url"]
                activities[issue_num]["actions"].append("Closed")

    # Fetch comments on all issues in the repo (this is expensive but necessary)
    # We'll use GraphQL for efficiency
    query = """
    query($repo_owner: String!, $repo_name: String!) {
      repository(owner: $repo_owner, name: $repo_name) {
        issues(first: 100, orderBy: {field: UPDATED_AT, direction: DESC}) {
          nodes {
            number
            title
            url
            comments(first: 100) {
              nodes {
                author {
                  login
                }
                createdAt
              }
            }
          }
        }
      }
    }
    """

    owner, name = repo.split("/")

    try:
        graphql_result = subprocess.run(
            [
                "gh", "api", "graphql",
                "-f", f"query={query}",
                "-F", f"repo_owner={owner}",
                "-F", f"repo_name={name}",
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        data = json.loads(graphql_result.stdout)

        if "data" in data and data["data"]["repository"]:
            for issue in data["data"]["repository"]["issues"]["nodes"]:
                issue_num = issue["number"]
                comment_count = 0

                for comment in issue["comments"]["nodes"]:
                    if comment["author"]["login"] == username:
                        comment_date = datetime.fromisoformat(comment["createdAt"].replace("Z", "+00:00"))
                        if start_date <= comment_date.date() <= end_date:
                            comment_count += 1

                if comment_count > 0:
                    if issue_num not in activities:
                        activities[issue_num]["number"] = issue_num
                        activities[issue_num]["title"] = issue["title"]
                        activities[issue_num]["url"] = issue["url"]
                    activities[issue_num]["actions"].append(f"Commented ({comment_count} comment{'s' if comment_count > 1 else ''})")

    except (subprocess.CalledProcessError, json.JSONDecodeError, KeyError) as e:
        print(f"Warning: Could not fetch issue comments: {e}", file=sys.stderr)

    return dict(activities)


def fetch_authored_prs(
    repo: str, username: str, start_date: date, end_date: date
) -> dict[int, dict]:
    """Fetch PRs authored by the user that had activity in the date range."""
    activities: dict[int, dict] = {}

    prs_json = run_gh_command([
        "pr", "list",
        "--repo", repo,
        "--state", "all",
        "--author", username,
        "--json", "number,title,url,createdAt,mergedAt,state",
        "--limit", "1000",
    ])

    for pr in prs_json:
        pr_num = pr["number"]
        created_at = datetime.fromisoformat(pr["createdAt"].replace("Z", "+00:00"))

        in_range = start_date <= created_at.date() <= end_date

        if pr.get("mergedAt"):
            merged_at = datetime.fromisoformat(pr["mergedAt"].replace("Z", "+00:00"))
            if start_date <= merged_at.date() <= end_date:
                in_range = True

        if in_range:
            activities[pr_num] = {
                "number": pr_num,
                "title": pr["title"],
                "url": pr["url"],
                "state": pr["state"],  # "OPEN", "MERGED", "CLOSED"
            }

    return activities


def fetch_reviewed_prs(
    repo: str, username: str, start_date: date, end_date: date,
    authored_pr_nums: set[int],
) -> dict[int, dict]:
    """Fetch PRs reviewed or commented on by the user (excluding authored ones)."""
    activities: dict[int, dict] = defaultdict(
        lambda: {"number": 0, "title": "", "url": "", "state": "", "actions": []}
    )

    query = """
    query($repo_owner: String!, $repo_name: String!) {
      repository(owner: $repo_owner, name: $repo_name) {
        pullRequests(first: 100, orderBy: {field: UPDATED_AT, direction: DESC}) {
          nodes {
            number
            title
            url
            state
            reviews(first: 100) {
              nodes {
                author { login }
                state
                createdAt
              }
            }
            comments(first: 100) {
              nodes {
                author { login }
                createdAt
              }
            }
          }
        }
      }
    }
    """

    owner, name = repo.split("/")

    try:
        graphql_result = subprocess.run(
            [
                "gh", "api", "graphql",
                "-f", f"query={query}",
                "-F", f"repo_owner={owner}",
                "-F", f"repo_name={name}",
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        data = json.loads(graphql_result.stdout)

        if "data" in data and data["data"]["repository"]:
            for pr in data["data"]["repository"]["pullRequests"]["nodes"]:
                pr_num = pr["number"]

                # Skip PRs authored by the user
                if pr_num in authored_pr_nums:
                    continue

                review_states = []
                for review in pr["reviews"]["nodes"]:
                    if review["author"]["login"] == username:
                        review_date = datetime.fromisoformat(review["createdAt"].replace("Z", "+00:00"))
                        if start_date <= review_date.date() <= end_date:
                            state = review["state"]
                            if state == "APPROVED":
                                review_states.append("Approved")
                            elif state == "CHANGES_REQUESTED":
                                review_states.append("Changes requested")
                            elif state == "COMMENTED":
                                review_states.append("Commented")

                comment_count = 0
                for comment in pr["comments"]["nodes"]:
                    if comment["author"]["login"] == username:
                        comment_date = datetime.fromisoformat(comment["createdAt"].replace("Z", "+00:00"))
                        if start_date <= comment_date.date() <= end_date:
                            comment_count += 1

                if review_states or comment_count > 0:
                    activities[pr_num]["number"] = pr_num
                    activities[pr_num]["title"] = pr["title"]
                    activities[pr_num]["url"] = pr["url"]
                    activities[pr_num]["state"] = pr["state"]

                    if review_states:
                        for state in set(review_states):
                            activities[pr_num]["actions"].append(f"Reviewed ({state})")

                    if comment_count > 0 and not review_states:
                        activities[pr_num]["actions"].append(
                            f"Commented ({comment_count} comment{'s' if comment_count > 1 else ''})"
                        )

    except (subprocess.CalledProcessError, json.JSONDecodeError, KeyError) as e:
        print(f"Warning: Could not fetch PR reviews: {e}", file=sys.stderr)

    return dict(activities)


def generate_markdown_report(
    repo: str,
    username: str,
    start_date: str,
    end_date: str,
    issues: dict[int, dict],
    authored_prs: dict[int, dict],
    reviewed_prs: dict[int, dict],
) -> str:
    """Generate a Markdown report from the activities."""
    merged_count = sum(1 for pr in authored_prs.values() if pr["state"] == "MERGED")

    authored_summary = f"{len(authored_prs)} authored PR{'s' if len(authored_prs) != 1 else ''}"
    if authored_prs:
        authored_summary += f" ({merged_count} merged)"

    report_lines = [
        "# GitHub Activity Report",
        "",
        f"**Period**: {start_date} to {end_date}",
        f"**Repository**: {repo}",
        f"**User**: {username}",
        "",
        "## Summary",
        f"- {len(issues)} issue{'s' if len(issues) != 1 else ''}",
        f"- {authored_summary}",
        f"- {len(reviewed_prs)} reviewed PR{'s' if len(reviewed_prs) != 1 else ''}",
        "",
    ]

    if issues:
        report_lines.extend(["## Issues", ""])
        for issue_num in sorted(issues.keys()):
            issue = issues[issue_num]
            report_lines.append(f"- #{issue_num}: {issue['title']}")
            report_lines.append(f"  - {issue['url']}")
        report_lines.append("")

    if authored_prs:
        report_lines.extend(["## Pull Requests (Authored)", ""])
        for pr_num in sorted(authored_prs.keys()):
            pr = authored_prs[pr_num]
            badge = state_badge(pr["state"])
            report_lines.append(f"- #{pr_num}: {badge} {pr['title']}")
            report_lines.append(f"  - {pr['url']}")
        report_lines.append("")

    if reviewed_prs:
        report_lines.extend(["## Pull Requests (Reviewed)", ""])
        for pr_num in sorted(reviewed_prs.keys()):
            pr = reviewed_prs[pr_num]
            actions_str = ", ".join(pr["actions"]) if pr["actions"] else "Participated"
            report_lines.append(f"- #{pr_num}: {pr['title']} — {actions_str}")
            report_lines.append(f"  - {pr['url']}")
        report_lines.append("")

    if not issues and not authored_prs and not reviewed_prs:
        report_lines.append("No activities found for this period.")

    return "\n".join(report_lines)


def generate_slack_report(
    repo: str,
    username: str,
    start_date: str,
    end_date: str,
    issues: dict[int, dict],
    authored_prs: dict[int, dict],
    reviewed_prs: dict[int, dict],
) -> str:
    """Generate a Slack-formatted (mrkdwn) report from the activities."""
    merged_count = sum(1 for pr in authored_prs.values() if pr["state"] == "MERGED")

    authored_summary = f"{len(authored_prs)} authored PR{'s' if len(authored_prs) != 1 else ''}"
    if authored_prs:
        authored_summary += f" ({merged_count} merged)"

    report_lines = [
        "*GitHub Activity Report*",
        "",
        f"*Period*: {start_date} to {end_date}",
        f"*Repository*: {repo}",
        f"*User*: {username}",
        "",
        "*Summary*",
        f"• {len(issues)} issue{'s' if len(issues) != 1 else ''}",
        f"• {authored_summary}",
        f"• {len(reviewed_prs)} reviewed PR{'s' if len(reviewed_prs) != 1 else ''}",
    ]

    if issues:
        report_lines.extend(["", "*Issues*"])
        for issue_num in sorted(issues.keys()):
            issue = issues[issue_num]
            report_lines.append(f"• #{issue_num}: {issue['title']}")
            report_lines.append(f"  {issue['url']}")

    if authored_prs:
        report_lines.extend(["", "*Pull Requests (Authored)*"])
        for pr_num in sorted(authored_prs.keys()):
            pr = authored_prs[pr_num]
            badge = state_badge(pr["state"])
            report_lines.append(f"• #{pr_num}: {pr['title']} {badge}")
            report_lines.append(f"  {pr['url']}")

    if reviewed_prs:
        report_lines.extend(["", "*Pull Requests (Reviewed)*"])
        for pr_num in sorted(reviewed_prs.keys()):
            pr = reviewed_prs[pr_num]
            actions_str = ", ".join(pr["actions"]) if pr["actions"] else "Participated"
            report_lines.append(f"• #{pr_num}: {pr['title']} — {actions_str}")
            report_lines.append(f"  {pr['url']}")

    if not issues and not authored_prs and not reviewed_prs:
        report_lines.append("")
        report_lines.append("No activities found for this period.")

    return "\n".join(report_lines)


def main():
    parser = argparse.ArgumentParser(
        description="Generate GitHub activity report for a date range"
    )
    parser.add_argument(
        "--start-date",
        required=True,
        help="Start date in YYYY-MM-DD format",
    )
    parser.add_argument(
        "--end-date",
        required=True,
        help="End date in YYYY-MM-DD format",
    )
    parser.add_argument(
        "--repo",
        required=True,
        help="Repository in owner/repo format",
    )
    parser.add_argument(
        "--format",
        choices=["markdown", "slack"],
        default="markdown",
        help="Output format: markdown (default) or slack (mrkdwn)",
    )

    args = parser.parse_args()

    # Parse dates
    start_date = parse_date(args.start_date).date()
    end_date = parse_date(args.end_date).date()

    if start_date > end_date:
        print("Error: start-date must be before or equal to end-date", file=sys.stderr)
        sys.exit(1)

    # Get authenticated user
    username = get_authenticated_user()

    # Fetch activities
    issues = fetch_issues_activity(args.repo, username, start_date, end_date)
    authored_prs = fetch_authored_prs(args.repo, username, start_date, end_date)
    reviewed_prs = fetch_reviewed_prs(
        args.repo, username, start_date, end_date,
        authored_pr_nums=set(authored_prs.keys()),
    )

    # Generate and print report
    if args.format == "slack":
        report = generate_slack_report(
            args.repo, username, args.start_date, args.end_date,
            issues, authored_prs, reviewed_prs,
        )
    else:
        report = generate_markdown_report(
            args.repo, username, args.start_date, args.end_date,
            issues, authored_prs, reviewed_prs,
        )

    print(report)


if __name__ == "__main__":
    main()
