---
name: pr-code-review
allowed-tools: Bash(gh issue view:*), Bash(gh search:*), Bash(gh issue list:*), Bash(gh pr comment:*), Bash(gh pr diff:*), Bash(gh pr view:*), Bash(gh pr list:*), Bash(gh api:*), Bash(gh repo view:*)
description: Code review a GitHub pull request and post the findings back to the PR as a review. Use this skill whenever the user asks to review OR re-review a pull request — in any phrasing or language, e.g. "PRレビューして", "PRをレビューしてください", "プルリクをレビューして", "PR #123 をレビュー", "このPRをコードレビューして", "再レビューして", "レビュー指摘の修正を確認して", "code review this PR", "review the PR", "re-review the PR" — with OR without an explicit PR number (when no number is given, detect the PR for the current branch). Also invoked directly via /pr-code-review. Trigger this BEFORE starting any manual review work.
disable-model-invocation: false
license: MIT
---

Provide a code review for the given pull request.

**Language rule**: Write all review content — issue descriptions shown to the user (step 7) and all text posted to GitHub (step 8) — in Japanese, unless the user explicitly requests a different language.

First, determine which PR to review:
- If the user specified a PR number (eg. `/pr-code-review 1003`), use that number.
- Otherwise, detect the PR for the current branch: `gh pr view --json number -q .number`. If this fails (eg. detached HEAD, not on a branch with a PR), run `gh pr list --state open`: if exactly one open PR exists, proceed with it and tell the user which PR was selected so they can correct it; if there are multiple (or zero) open PRs, ask the user for the PR number.

To do this, follow these steps precisely:

1. Use a Haiku agent to check if the pull request (a) is closed, (b) is a draft, (c) does not need a code review (eg. because it is an automated pull request, or is very simple and obviously ok), or (d) already has a code review from Claude Code or from your own GitHub account (run `gh api user -q .login` to get your own login, then check reviews for that login). Reviews from other bots (eg. Copilot, Gemini, etc.) or from other human reviewers do NOT make the PR ineligible. If ineligible, do not proceed.

   **Exception — explicit user request:** The (d) check exists mainly to prevent duplicate automated reviews (eg. cron/loop runs). If the user explicitly requested this review (eg. directly invoked the skill, named the PR, or asked to "re-review" /「再レビューして」 / 「レビュー指摘の修正を確認して」), a prior review from yourself or Claude Code does NOT make it ineligible — proceed. The (a)/(b)/(c) checks still apply.

   **Re-review mode:** If a prior review from yourself/Claude Code exists on this PR and new commits were pushed after it, run the rest of this skill in re-review mode: fetch your prior review body, its inline comments, the author's replies, and the fix commits (`gh api repos/{owner}/{repo}/pulls/{N}/reviews`, `.../pulls/{N}/comments`, `git show <sha>`). Focus the review on what changed since the prior review, and switch Agent #4's role as described in step 4d. In the final review body (step 8), lead with the status of prior findings (how many addressed / deferred / remaining).

2. Use another Haiku agent to give you a list of file paths to (but not the contents of) any relevant CLAUDE.md files from the codebase: the root CLAUDE.md file (if one exists), as well as any CLAUDE.md files in the directories whose files the pull request modified.

3. In parallel, run two Haiku agents:
   a. Agent A: View the pull request and return a concise summary of the change (title, description, files changed, purpose).
   b. Agent B: Detect the linked Issue for this pull request. Check in this order:
      - PR body for `Closes #N`, `Fixes #N`, `Resolves #N`, or bare `#N` references
      - PR title for `#N` references
      - Branch name for patterns like `issue123`, `issue-123`, `issue/123`, `feat/issueN...`
      If an Issue number is found, fetch its title and body with `gh issue view <N>`. Return the Issue number, title, and body. If `gh issue view` fails (eg. Issue not found, different repo), treat it as if no Issue was found. If no Issue is found or fetch fails, return `{"issue": null}`.

4. Using the PR summary (from 3a) and Issue content (from 3b), launch 8 parallel Sonnet agents to independently review the change. All agents receive both the PR diff AND the Issue content (if available). The agents should return a list of issues with file path, line number (if applicable), a category label, and the reason each issue was flagged.

   **Authoritative state:** Review the PR's remote head, not the local working tree. The local checkout may be behind the PR head (eg. unpushed/unpulled commits), so agents that read files directly (git blame, full-file context in 4c/4e/4h) can see a stale state and report findings that the PR has already fixed. Any on-disk finding that contradicts `gh pr diff` must be reconciled against the diff — the diff (PR head) wins. When in doubt about the current state of a line, fetch it from the PR head ref rather than trusting the working tree.

   a. Agent #1 [CLAUDE.md]: Audit the changes to make sure they comply with the CLAUDE.md. Note that CLAUDE.md is guidance for Claude as it writes code, so not all instructions will be applicable during code review. Only flag issues that are clearly relevant to the changed code.
   b. Agent #2 [Bug]: Read the file changes in the pull request, then do a shallow scan for obvious bugs. Avoid reading extra context beyond the changes, focusing just on the changes themselves. Focus on large bugs, and avoid small issues and nitpicks. Ignore likely false positives.
   c. Agent #3 [Bug]: Read the git blame and history of the code modified, to identify any bugs in light of that historical context.
   d. Agent #4 [Prior feedback]: **In re-review mode**, verify each finding from YOUR prior review on this PR against the current head instead: classify as fully addressed (do not flag), partially addressed or unaddressed (re-flag, stating exactly what remains), or intentionally deferred to a tracking issue (do not flag, but verify the issue actually exists). Also flag NEW problems introduced by the fix commits themselves — fixes for review feedback are a common source of fresh regressions. **Otherwise**, find previous pull requests that touched the same files as this PR, then check for any review comments that may also apply to the current changes. To find relevant prior PRs, run `gh pr list --state closed --limit 30 --json number,title,files` and filter to PRs that modified at least one of the same files. Then for the most relevant 2-3 PRs, fetch their review comments with `gh pr view <number> --json reviews,comments`. For each prior comment you find, actively verify whether it was already addressed: check if subsequent commits after that comment modified the relevant code, or if the PR author replied indicating it was resolved. Only flag comments that were NOT already addressed.
   e. Agent #5 [Code comments]: Read code comments in the modified files, and make sure the changes in the pull request comply with any guidance in the comments.
   f. Agent #6 [Issue: scope]: If an Issue was found in step 3b, compare the Issue requirements against the actual PR changes and identify:
      - **Under-scope**: requirements described in the Issue that are not implemented in this PR
      - **Over-scope**: changes in this PR that go beyond what the Issue describes (unrelated changes mixed in)
      If the PR description explicitly says this is a partial implementation (eg. "first step of #N"), treat under-scope as intentional and do not flag it.
      If no Issue was found, return a list containing a single finding: `[{"file": null, "line": null, "category": "Issue: no link", "issue": "PR has no linked Issue", "reason": "Could not detect a linked Issue from branch name, PR title, or PR body.", "fixed_score": 50}]`. This finding skips the scoring agent (use the fixed score of 50 directly).
   g. Agent #7 [Issue: PR size]: Analyze whether the PR is too large to review effectively. Focus on qualitative criteria: does the PR mix multiple independent concerns that could have been separate PRs? Would a reviewer struggle to understand the full scope in one sitting? Large file counts or line counts alone are not sufficient — focus on whether the changes represent a single coherent unit of work. Use the Issue content (if available) to judge whether a large PR is justified by a large Issue scope. If the PR appears to be an appropriate size and scope, return an empty list `[]`.
   h. Agent #8 [Design]: Review the changes for universal engineering concerns that apply regardless of project-specific guidelines. Do NOT reference or consult CLAUDE.md — this agent's role is to catch issues that any experienced engineer would flag. Focus on:
      - **Security**: missing input validation, insufficient authorization checks, sensitive data exposed in logs or responses, injection risks
      - **Backward compatibility**: changes that silently break existing callers, remove or change public interfaces, alter DB schema behavior in ways that affect existing data, or change configuration formats without migration
      - **Error propagation**: exceptions that are swallowed silently, failure paths where errors do not reach the caller, cases where a failure produces no observable signal

5. For each issue found in step 4 (except the "no linked Issue" finding which has a fixed score of 50), launch a parallel Haiku agent that takes the PR and issue description, and returns a score indicating confidence that the issue is real and not a false positive. The agent may consult the CLAUDE.md files (from step 2) solely to verify whether an issue is a genuine concern for this project — but CLAUDE.md mention must NOT be used to increase the score. Score on a scale from 0-100 based purely on the likely real-world impact, frequency, and certainty of the issue. The scale is (give this rubric to the agent verbatim):
   a. 0: Not confident at all. This is a false positive that doesn't stand up to light scrutiny, or is a pre-existing issue. Also score 0 if the "issue" is actually an improvement over the previous behavior — e.g., adding a tiebreaker for deterministic ordering — even if it technically changes existing behavior. If fixing the flagged issue would make things worse than leaving it, score 0.
   b. 25: Somewhat confident. This might be a real issue, but the agent was unable to verify it. The impact in practice is unclear or very limited.
   c. 50: Moderately confident. The agent was able to verify this is a real issue, but it is a nitpick or unlikely to cause problems in practice. Relative to the rest of the PR, it is not very important.
   d. 75: Highly confident. The agent double-checked the issue and verified it is very likely to be hit in practice. The existing approach in the PR is insufficient. The issue will directly impact functionality, reliability, or security.
   e. 100: Absolutely certain. The agent confirmed this is definitely a real issue that will occur frequently. The evidence directly confirms it.

6. Use a Haiku agent to repeat the eligibility check from step 1 (same rules: only your own prior Claude Code review makes it ineligible, and the same explicit-user-request exception applies), to make sure that the pull request is still eligible for code review.

7. Present issues with score > 0 to the user for confirmation (do NOT show score 0 issues — they are false positives or pre-existing issues). Format as a flat list ordered by score descending — one issue per entry with category label, file path, line number (or "N/A"), score, one-line description, and a risk analysis. Example format:

   ```
   1. [Bug] src/services/foo.py:42 — score 82 — OrganizationNotFoundError misclassified as USAGE_LIMIT_EXCEEDED
      修正しない場合のリスク: 課金上限エラーが誤ったエラーコードで返され、クライアントが誤った処理をする可能性がある
      修正した場合のリスク: エラーハンドリングの変更により、既存の呼び出し元の挙動が変わる可能性がある（低）

   2. [Design] src/services/bar.py:229 — score 45 — error_code stored without length validation against String(100) column
      修正しない場合のリスク: 長いエラーコードが渡された場合にDBエラーが発生する（低頻度）
      修正した場合のリスク: バリデーション追加による影響は軽微
   ```

   Ask the user: "Found N issues. Please confirm — reply 'post all' to post them as-is, or tell me which ones to skip (e.g. 'skip 2 and 4')." Wait for the user's response before proceeding. If the user asks to skip or modify any issues, update the list accordingly.

   **Fix-here vs separate-issue split:** If the user asks to organize findings (eg. 「別Issueに切り出すものと整理して」), classify each finding by: (a) was it caused by this PR, (b) is the fix small and self-contained, (c) does fixing it properly require changing components shared with code outside this PR's scope. Propose "fix in this PR" for (a)+(b), and "separate issue" only for (c). Do NOT route low-priority self-contained findings to a separate issue — a low-priority issue will be neglected; propose "fix in this PR now, or explicitly drop" instead. Reflect the final classification in the posted comments (mark separate-issue candidates as 別Issue推奨 with the reason).

8. After the user confirms, post the review using the GitHub Pull Request Reviews API via `gh api`. Follow these rules:
   a. Get the repo name first: `gh repo view --json nameWithOwner -q .nameWithOwner`
   b. For each issue, determine whether the flagged line is part of the PR diff (i.e., the line was added or modified in this PR). Check by running `gh pr diff <number>` and confirming the line appears with a `+` prefix or is within a changed hunk.
   c. Post a **single review** using the GitHub API with inline comments for issues whose lines are in the diff, and include any remaining issues (including Issue-level findings with no specific line) in the top-level review body:

```bash
gh api repos/{owner}/{repo}/pulls/{pull_number}/reviews \
  --method POST \
  --input - << 'EOF'
{
  "body": "### Code review\n\n<overall assessment: 1-2 sentences honestly evaluating the PR quality — if the implementation is solid, say so warmly and directly. Then list any issues not mappable to diff lines.>\n\n🤖 Generated with [Claude Code](https://claude.ai/code)\n\n<sub>- If this code review was useful, please react with 👍. Otherwise, react with 👎.</sub>",
  "event": "COMMENT",
  "comments": [
    {
      "path": "src/api/main.py",
      "line": 318,
      "side": "RIGHT",
      "body": "<inline comment text>"
    }
  ]
}
EOF
```

   d. For multi-line inline comments, add `"start_line"` and `"start_side": "RIGHT"` fields alongside `"line"`.
   e. The top-level `body` must always include an honest overall assessment (1-2 sentences) regardless of whether issues exist or whether all issues are inline comments. If the PR is well-implemented, say so genuinely — this provides context for any minor comments that follow.
   f. If NO issues can be placed inline (none of the flagged lines are in the diff), fall back to `gh pr comment` with the standard format below.
   g. Keep each inline comment body brief and self-contained.
   h. Avoid emojis in comment text.
   i. Inline comment line numbers must match the file at the PR head, which can differ from your local checkout if it is behind. Derive line numbers from `gh pr diff` hunk headers, or fetch the file at the PR head ref — eg. `gh api "repos/{owner}/{repo}/contents/{path}?ref={head_sha}"` (quote the URL so the shell does not glob the `?`). The GitHub API rejects comments whose line is not part of the diff, so confirm the line is in a changed hunk first.

---

Examples of false positives, for steps 4 and 5:

- Pre-existing issues
- Something that looks like a bug but is not actually a bug
- Pedantic nitpicks that a senior engineer wouldn't call out
- Issues that a linter, typechecker, or compiler would catch (eg. missing or incorrect imports, type errors, broken tests, formatting issues, pedantic style issues like newlines). No need to run these build steps yourself — it is safe to assume that they will be run separately as part of CI.
- General code quality issues (eg. lack of test coverage, poor documentation), unless explicitly required in CLAUDE.md
- Note: security issues, backward compatibility breaks, and error propagation gaps are NOT false positives — these are explicitly checked by Agent #8
- Issues that are called out in CLAUDE.md, but explicitly silenced in the code (eg. due to a lint ignore comment)
- Changes in functionality that are likely intentional or are directly related to the broader change
- Real issues, but on lines that the user did not modify in their pull request
- Findings based on the local working tree that contradict `gh pr diff` — the local checkout may be behind the PR head, so the diff (PR head) is authoritative. Verify the state at the PR head before flagging.
- Prior PR comments that were already addressed in a subsequent commit or acknowledged by the PR author
- For Issue-scope findings: partial implementations that are clearly intentional (eg. the PR description says "first step of #N")
- Changes that are improvements over the previous behavior (eg. adding a tiebreaker column for deterministic pagination ordering). Even if they technically change existing behavior, they should not be flagged — reverting them would be a regression.

Notes:

- Do not check build signal or attempt to build or typecheck the app. These will run separately, and are not relevant to your code review.
- Use `gh` to interact with Github (eg. to fetch a pull request, or to create inline comments), rather than web fetch.
- Make a todo list first.
- You must cite and link each bug (eg. if referring to a CLAUDE.md, you must link it).
- For the fallback `gh pr comment` format (when no inline comments are possible), follow this format precisely (assuming for this example that you found 3 issues):

---

### Code review

Found 3 issues:

1. [Bug] <brief description> (due to <file and code snippet>)

<link to file and line with full sha1 + line range for context, note that you MUST provide the full sha and not use bash here, eg. https://github.com/anthropics/claude-code/blob/1d54823877c4de72b2316a64032a54afc404e619/README.md#L13-L17>

2. [CLAUDE.md] <brief description> (CLAUDE.md says "<...>")

<link to file and line with full sha1 + line range for context>

3. [Issue: under-scope] <brief description> (Issue #N requires "<...>" but this is not implemented)

🤖 Generated with [Claude Code](https://claude.ai/code)

<sub>- If this code review was useful, please react with 👍. Otherwise, react with 👎.</sub>

---

- Or, if you found no issues:

---

### Code review

<overall assessment: 1-2 sentences honestly describing what is good about this PR. Be specific — mention the implementation approach, test coverage, or design choices that stood out positively.>

No issues found. Checked for bugs, CLAUDE.md compliance, universal engineering concerns, and Issue alignment.

🤖 Generated with [Claude Code](https://claude.ai/code)

- When linking to code in the review body, follow the following format precisely, otherwise the Markdown preview won't render correctly: https://github.com/anthropics/claude-code/blob/d4d8fbbb333c627d8fe2c1c583a5ccc26fdb1aed/README.md#L10-L15
  - Requires full git sha
  - You must provide the full sha. Commands like `https://github.com/owner/repo/blob/$(git rev-parse HEAD)/foo/bar` will not work, since your comment will be directly rendered in Markdown.
  - Repo name must match the repo you're code reviewing
  - # sign after the file name
  - Line range format is L[start]-L[end]
  - Provide at least 1 line of context before and after, centered on the line you are commenting about (eg. if you are commenting about lines 5-6, you should link to `L4-7`)
