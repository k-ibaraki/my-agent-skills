---
allowed-tools: Bash(gh issue view:*), Bash(gh search:*), Bash(gh issue list:*), Bash(gh pr comment:*), Bash(gh pr diff:*), Bash(gh pr view:*), Bash(gh pr list:*), Bash(gh api:*), Bash(gh repo view:*)
description: Code review a GitHub pull request and post the findings back to the PR as a review. Use this skill whenever the user asks to review OR re-review a pull request — in any phrasing or language, e.g. "PRレビューして", "PRをレビューしてください", "プルリクをレビューして", "PR #123 をレビュー", "このPRをコードレビューして", "再レビューして", "レビュー指摘の修正を確認して", "code review this PR", "review the PR", "re-review the PR" — with OR without an explicit PR number (when no number is given, detect the PR for the current branch). Also invoked directly via /pr-code-review. Trigger this BEFORE starting any manual review work. Exception: when the request names Jev / TypeSafe / System One (e.g. "jevでPRレビューして"), use pr-code-review-jev instead.
disable-model-invocation: false
license: MIT
---

Provide a code review for the given pull request.

**Language rule**: Write all review content — issue descriptions shown to the user (step 7) and all text posted to GitHub (step 8) — in Japanese, unless the user explicitly requests a different language. Avoid literal translations of English jargon (eg. contract → 契約); use natural Japanese terms instead (eg. API仕様・API定義, 値の一致を確認するテスト). This rule also applies when incorporating text returned by subagents: do not paste their wording as-is into step 7/8 output — rephrase it to comply (subagent reports are a common source of such 直訳語).

First, determine which PR to review:
- If the user specified a PR number (eg. `/pr-code-review 1003`), use that number.
- Otherwise, detect the PR for the current branch: `gh pr view --json number -q .number`. If this fails (eg. detached HEAD, not on a branch with a PR), first try matching HEAD to a PR branch with `git branch -a --contains HEAD`: if it matches exactly one open PR's branch, proceed with it and tell the user which PR was selected so they can correct it. Otherwise run `gh pr list --state open`: if exactly one open PR exists, proceed with it (same notification); if there are multiple (or zero) open PRs, ask the user for the PR number.

**Pre-agreed findings mode:** If the user brings a list of findings already agreed upon in the current conversation (eg. 「今回の指摘内容を投稿して」), skip the discovery phase (steps 2-7) and run only the eligibility check (step 1, lightweight is fine) and the posting step (step 8), using the agreed findings verbatim. This avoids redundant re-discovery and prevents the posted content from diverging from what the user approved.

To do this, follow these steps precisely:

1. Use a Haiku agent to check if the pull request (a) is closed, (b) is a draft, (c) does not need a code review (eg. because it is an automated pull request, or is very simple and obviously ok), or (d) already has a code review from Claude Code or from your own GitHub account (run `gh api user -q .login` to get your own login, then check reviews for that login). Reviews from other bots (eg. Copilot, Gemini, etc.) or from other human reviewers do NOT make the PR ineligible. If ineligible, do not proceed.

   **Exception — explicit user request:** The (d) check exists mainly to prevent duplicate automated reviews (eg. cron/loop runs). If the user explicitly requested this review (eg. directly invoked the skill, named the PR, or asked to "re-review" /「再レビューして」 / 「レビュー指摘の修正を確認して」), a prior review from yourself or Claude Code does NOT make it ineligible — proceed. The (a)/(b)/(c) checks still apply.

   **Re-review mode:** If a prior review from yourself/Claude Code exists on this PR and new commits were pushed after it, run the rest of this skill in re-review mode: fetch your prior review body, its inline comments, the author's replies, and the fix commits (`gh api repos/{owner}/{repo}/pulls/{N}/reviews`, `.../pulls/{N}/comments`, `git show <sha>`). Focus the review on what changed since the prior review, and switch Agent #4's role as described in step 4d. In the final review body (step 8), lead with the status of prior findings (how many addressed / deferred / remaining). Size the panel per the rule at the head of step 4, measuring the delta as the fix commits: a prior-findings verifier (Agent #4) plus a fix-regression scanner (and a migration/schema-integrity check when the fix touches migrations) is normally enough. Process artefacts the author added in response to your last review — checklists, PR templates, contributing/dev guides — are not review targets: unless one contradicts the code, do not flag its wording, scope, or completeness. Critiquing text written to absorb your own feedback moves the goalposts; credit it in the review body instead.

2. Use another Haiku agent to give you a list of file paths to (but not the contents of) any relevant CLAUDE.md files from the codebase: the root CLAUDE.md file (if one exists), as well as any CLAUDE.md files in the directories whose files the pull request modified.

3. In parallel, run two Haiku agents:
   a. Agent A: View the pull request and return a concise summary of the change (title, description, files changed, purpose).
   b. Agent B: Detect the linked Issue for this pull request. Check in this order:
      - PR body for `Closes #N`, `Fixes #N`, `Resolves #N`, or bare `#N` references
      - PR title for `#N` references
      - Branch name for patterns like `issue123`, `issue-123`, `issue/123`, `feat/issueN...`
      If an Issue number is found, fetch its title and body with `gh issue view <N>`. Return the Issue number, title, and body. If `gh issue view` fails (eg. Issue not found, different repo), treat it as if no Issue was found. If no Issue is found or fetch fails, return `{"issue": null}`.

   Skip either agent (and the step 1 check) when this session already holds the authoritative equivalent — eg. you authored this PR in this session, or already fetched the Issue — and use what you have.

4. Using the PR summary (from 3a) and Issue content (from 3b), launch 9 parallel Sonnet agents to independently review the change. All agents receive both the PR diff AND the Issue content (if available). The agents should return a list of issues with file path, line number (if applicable), a category label, and the reason each issue was flagged. If the user requested additional review perspectives (eg. via ARGUMENTS), add one dedicated agent per perspective alongside the 9 below, and carry its findings through steps 5-8 like any other; instruct its scoring agent that the perspective was user-requested (do not dismiss findings wholesale as nitpicks, but still verify each one strictly). Include in every subagent prompt (steps 4, 5, and 8a): do NOT run tests, builds, or typecheckers — judge by reading the diff and code only (agents that run the test suite stall without adding signal). See Notes for why build signal is never evidence either way.

   **Size the panel to the change (this applies to every review, not only re-reviews):** 9 is the ceiling for a substantial diff, not a quota to fill. Judge the delta before fanning out. For a small, single-concern change — a few dozen lines, one or two files — or for a PR that already carries reviews from other bots or humans, a reduced panel gives better signal: a full panel on a thin diff mostly manufactures duplicates and nitpicks. Keep the roles that can still find something (typically the dedup-aware bug/security scan, Issue scope, CLAUDE.md, and the prior-feedback verifier retargeted at this PR's own thread) and drop the ones with nothing to work on. Name the roles you ran in step 7 so the user can ask for the full panel. Run all 9 when the diff is broad or mixes several concerns.

   **Same-PR dedup (do this BEFORE fanning out):** Fetch the existing review comments on THIS PR and the author's replies (`gh api repos/{owner}/{repo}/pulls/{N}/comments --paginate`, `gh api repos/{owner}/{repo}/issues/{N}/comments`). Build a compact "already raised / claimed fixed / explicitly deferred" list and hand it to every agent in step 4, instructing them that a finding matching the list may only be reported with line-level evidence that it is still present at head — otherwise a PR that already carries bot reviews yields mostly duplicates. When you have already refuted one of those findings, put the refutation and its evidence in the list, not just the claim — a long, confidently formatted HIGH from another bot is otherwise rediscovered and re-scored on its presentation alone. Split the list by whether the author replied: bot findings posted as issue-level comments (`gh api .../issues/{N}/comments`) often have no inline anchor and so sit unanswered — mark those "unanswered, re-verify at head" rather than "already raised", since silence is not a fix. (Step 4d's default role covers *prior* PRs, not this one.)

   **Authoritative state:** Review the PR's remote head, not the local working tree — otherwise agents that read files directly (git blame, full-file context in 4c/4e/4h) can see a stale state. If the local checkout differs from the PR head (eg. GitHub rebased the PR after its base PR merged), sync it to the origin head first — after confirming the working tree is clean. Any on-disk finding that contradicts `gh pr diff` must be reconciled against the diff (the PR head wins) — treat such a finding as a false positive unless the diff confirms it. Every line number you cite, including inline-comment anchors in step 8, comes from the `gh pr diff` hunk headers at head, or from the file fetched at the head ref: `gh api "repos/{owner}/{repo}/contents/{path}?ref={head_sha}"` (quote the URL so the shell does not glob the `?`). For stacked PRs (base is another PR's branch), the PR's changes are the full base...head range that `gh pr diff` reports — never judge a line as "outside this PR" from a single commit's diff or blame; verify membership against the `gh pr diff` hunks. Also check the head is not behind its own base (`git log <head>..origin/<baseRefName>`): commits missing there can silently undo review fixes already made on the base PR.

   **PR-modified docs are not ground truth:** If the PR itself changes a design document (ADR, ER diagram, ubiquitous-language, architecture docs, etc.), do not treat that document as pre-existing, authoritative context — the document was written or edited by the same author to match this PR's implementation, so it can itself be wrong (eg. marking a nullable column "required"). Verify the doc's updated content against the actual code changes in the same PR independently, rather than checking code against doc and stopping there.

   **Docs-only PRs:** Keep the panel structure but retarget the code-centric roles at the document: internal contradictions (values defined one way and used another, examples breaking their own stated rules), claims about code/ADRs/issue numbers checked against the repo at head, and stated behaviour checked against the docstrings and comments of the sources it references.

   a. Agent #1 [CLAUDE.md]: Audit the changes to make sure they comply with the CLAUDE.md. Note that CLAUDE.md is guidance for Claude as it writes code, so not all instructions will be applicable during code review. Only flag issues that are clearly relevant to the changed code.
   b. Agent #2 [Bug]: Read the file changes in the pull request, then do a shallow scan for obvious bugs. Avoid reading extra context beyond the changes, focusing just on the changes themselves. Focus on large bugs, and avoid small issues and nitpicks. Ignore likely false positives.
   c. Agent #3 [Bug]: Read the git blame and history of the code modified, to identify any bugs in light of that historical context.
   d. Agent #4 [Prior feedback]: **In re-review mode**, verify each finding from YOUR prior review on this PR against the current head instead: classify as fully addressed (do not flag), partially addressed or unaddressed (re-flag, stating exactly what remains), or intentionally deferred to a tracking issue (do not flag, but verify the issue actually exists). The author's reply is not evidence: a fix claimed as done is sometimes reverted by a later commit, so decide every classification from the code at head. Also flag NEW problems introduced by the fix commits themselves — fixes for review feedback are a common source of fresh regressions. **Otherwise**, find prior PRs whose review comments could still apply. If the PR body or branch names its lineage (a stack, a split-from PR, prerequisite PRs), start there; otherwise search by overlapping files (`gh pr list --state closed --limit 30 --json number,title,files`). Fetch review comments for the most relevant 2-3 with `gh pr view <number> --json reviews,comments`, and check whether each comment also applies to the current changes. Verify whether each prior comment was already addressed (subsequent commits modified the code, or the author replied it was resolved) and only flag those that were NOT.
   e. Agent #5 [Code comments]: Read code comments in the modified files, and make sure the changes in the pull request comply with any guidance in the comments.
   f. Agent #6 [Issue: scope]: If an Issue was found in step 3b, compare the Issue requirements against the actual PR changes and identify:
      - **Under-scope**: requirements described in the Issue that are not implemented in this PR
      - **Over-scope**: changes in this PR that go beyond what the Issue describes (unrelated changes mixed in)
      If the PR description explicitly says this is a partial implementation (eg. "first step of #N"), treat under-scope as intentional and do not flag it.
      A scope decision justified by a design document this PR edits is not settled by that fact alone — apply "PR-modified docs are not ground truth" above, and flag genuine doc/code mismatches as `Doc: inconsistency`.
      If no Issue was found, return a list containing a single finding: `[{"file": null, "line": null, "category": "Issue: no link", "issue": "PR has no linked Issue", "reason": "Could not detect a linked Issue from branch name, PR title, or PR body.", "fixed_score": 50}]`. This finding skips the scoring agent (use the fixed score of 50 directly).
   g. Agent #7 [Issue: PR size]: Analyze whether the PR is too large to review effectively. Focus on qualitative criteria: does the PR mix multiple independent concerns that could have been separate PRs? Would a reviewer struggle to understand the full scope in one sitting? Large file counts or line counts alone are not sufficient — focus on whether the changes represent a single coherent unit of work. Use the Issue content (if available) to judge whether a large PR is justified by a large Issue scope. If the PR appears to be an appropriate size and scope, return an empty list `[]`.
   h. Agent #8 [Design]: Review the changes for universal engineering concerns that apply regardless of project-specific guidelines. Do NOT reference or consult CLAUDE.md — this agent's role is to catch issues that any experienced engineer would flag. Focus on:
      - **Security**: missing input validation, insufficient authorization checks, sensitive data exposed in logs or responses, injection risks
      - **Backward compatibility**: changes that silently break existing callers, remove or change public interfaces, alter DB schema behavior in ways that affect existing data, or change configuration formats without migration
      - **Error propagation**: exceptions that are swallowed silently, failure paths where errors do not reach the caller, cases where a failure produces no observable signal
   i. Agent #9 [Approach]: Evaluate whether the PR's design/implementation approach is an appropriate way to solve the linked Issue (or the PR's stated purpose, if no Issue). Return two things: (1) a short validity assessment (2-4 sentences) for the step 7 summary — always, even when the approach is fine; (2) findings ONLY for significant design concerns where a clearly more natural alternative exists — these go through scoring (step 5) like any other finding. Do not emit findings for mere stylistic preference between comparable approaches.

5. First dedupe: if multiple step-4 agents flagged the same issue, merge them into one finding before scoring (note that multiple agents flagged it). Then, for each issue found in step 4 (except the "no linked Issue" finding which has a fixed score of 50), launch a parallel Haiku agent that takes the PR and issue description, and returns a score indicating confidence that the issue is real and not a false positive. The agent may consult the CLAUDE.md files (from step 2) solely to verify whether an issue is a genuine concern for this project — but CLAUDE.md mention must NOT be used to increase the score. Score on a scale from 0-100 based purely on the likely real-world impact, frequency, and certainty of the issue. The scale is (give this rubric to the agent verbatim):
   a. 0: Not confident at all. This is a false positive that doesn't stand up to light scrutiny, or is a pre-existing issue. Also score 0 if the "issue" is actually an improvement over the previous behavior — e.g., adding a tiebreaker for deterministic ordering — even if it technically changes existing behavior. If fixing the flagged issue would make things worse than leaving it, score 0.
   b. 25: Somewhat confident. This might be a real issue, but the agent was unable to verify it. The impact in practice is unclear or very limited.
   c. 50: Moderately confident. The agent was able to verify this is a real issue, but it is a nitpick or unlikely to cause problems in practice. Relative to the rest of the PR, it is not very important.
   d. 75: Highly confident. The agent double-checked the issue and verified it is very likely to be hit in practice. The existing approach in the PR is insufficient. The issue will directly impact functionality, reliability, or security.
   e. 100: Absolutely certain. The agent confirmed this is definitely a real issue that will occur frequently. The evidence directly confirms it.

   Audit each returned score before using it: the stated reason must rest on the rubric's three axes (impact, frequency, certainty). If it leans on "already flagged in a prior review", "another reviewer rated it HIGH", or a failure mode the agent did not verify in the code, re-score it yourself.

   Verify the finding's own evidence here, not only at step 8a: open each cited file and line and confirm the quoted code says what the finder claims and supports the conclusion drawn from it. Agents do cite a line that shows the opposite of their claim, or quote a test whose assertion they misread. If the citation collapses, re-anchor the finding on evidence that holds, or score it 0 — never carry a plausible-sounding claim forward on a broken citation.

   Fallback: if a scoring agent fails to launch or return, do NOT block the review or silently drop the finding — score it yourself by reading the flagged code and the finder's evidence against this same rubric.

6. Use a Haiku agent to repeat the eligibility check from step 1 (same rules and explicit-user-request exception as step 1), and to return the current headRefOid. If the head moved since step 4, reconcile per step 8a BEFORE step 7 — the list you present must already reflect the current head.

7. Start the presentation with a summary block (user-facing only — do NOT include it in the GitHub post): the linked Issue's intent (or the PR title/description as the stated purpose if no Issue — mark it 「Issueなし」), what this PR does in response, and Agent #9's validity assessment of the approach. In re-review mode, lead with the status of prior findings instead (as in step 1) and keep this summary brief, focused on the new commits. Then present issues with score > 0 to the user for confirmation (do NOT show score 0 issues — they are false positives or pre-existing issues). Format as a flat list ordered by score descending — one issue per entry with category label, file path, line number (or "N/A"), score, one-line description, and a risk analysis. Example format:

   ```
   1. [Bug] src/services/foo.py:42 — score 82 — OrganizationNotFoundError misclassified as USAGE_LIMIT_EXCEEDED
      修正しない場合のリスク: 課金上限エラーが誤ったエラーコードで返され、クライアントが誤った処理をする可能性がある
      修正した場合のリスク: エラーハンドリングの変更により、既存の呼び出し元の挙動が変わる可能性がある（低）

   2. [Design] src/services/bar.py:229 — score 45 — error_code stored without length validation against String(100) column
      修正しない場合のリスク: 長いエラーコードが渡された場合にDBエラーが発生する（低頻度）
      修正した場合のリスク: バリデーション追加による影響は軽微
   ```

   Ask the user: "Found N issues. Please confirm — reply 'post all' to post them as-is, or tell me which ones to skip (e.g. 'skip 2 and 4')." Wait for the user's response before proceeding. If the user asks to skip or modify any issues, update the list accordingly. If the PR under review is the user's own (eg. authored in this session or by the user's account), also offer the option to fix the findings directly instead of posting them; if the user chooses to fix, skip step 8.

   **Other requested deliverables:** If the user asked for anything besides the findings (eg. a summary of the change, a limited review scope), present that in step 7 as well, and ask whether it should also be posted to GitHub.

   **Fix-here vs separate-issue split:** If the user asks to organize findings (eg. 「別Issueに切り出すものと整理して」), classify each finding by: (a) was it caused by this PR, (b) is the fix small and self-contained, (c) does fixing it properly require changing components shared with code outside this PR's scope. Propose "fix in this PR" for (a)+(b), and "separate issue" only for (c). Do NOT route low-priority self-contained findings to a separate issue — a low-priority issue will be neglected; propose "fix in this PR now, or explicitly drop" instead. Reflect the final classification in the posted comments (mark separate-issue candidates as 別Issue推奨 with the reason).

8. After the user confirms, post the review using the GitHub Pull Request Reviews API via `gh api`. Follow these rules:
   a. **Self-check（投稿直前の内容検証）**: まず `gh pr view <number> --json headRefOid` で現在のheadを再取得する。step 4 以降にheadが動いていたら、差分を取って全指摘を突き合わせ直す。新しいコミットが解消した指摘は落とし、ずれた行番号は付け直し、headが動いた事実をユーザーへ伝える（変更前のheadの行番号のまま投稿しない）。次に、投稿予定の指摘を並列のHaikuエージェントへ渡し、PRヘッド時点の実コードに照らして独立に再検証させる。検証させるのは文体・誤字脱字・体裁ではなく指摘の技術的な主張（バグの発生条件、規約違反の該当箇所、根拠となるコードなど）であり、「この指摘は事実としてコードの実態と一致しているか」「引用しているコード・行番号は指摘内容の根拠として本当に成立しているか」を判定させる。関連する指摘は1体にまとめてよい。ただし、自分で検証済みであることを理由にこの再検証を省略してはならない。指摘の技術的主張が現在のコードと矛盾する、または根拠が崩れていると判定された場合は、その判定の前提自体を実コードで確かめたうえで、投稿対象から外すか、反証の根拠を添えて投稿するかを決め、いずれもユーザーに理由を伝える（黙って進めない）。技術検証とは別に、投稿する本文・各コメントの日本語を通しで読み返し、Language rule に照らして直訳調（英語の構文をそのまま置き換えた言い回しと、直訳の訳語の両方）が残っていないか確認する。特にサブエージェントの出力をそのまま貼った箇所は要注意。不自然な箇所は書き直してから投稿する。
   b. Get the repo name first: `gh repo view --json nameWithOwner -q .nameWithOwner`
   c. For each issue, determine whether the flagged line is part of the PR diff (i.e., the line was added or modified in this PR). Check by running `gh pr diff <number>` and confirming the line appears with a `+` prefix or is within a changed hunk. The GitHub API rejects comments whose line is not part of the diff, so confirm the line is in a changed hunk before anchoring; take line numbers per "Authoritative state" (step 4).
   d. Post a **single review** using the GitHub API with inline comments for issues whose lines are in the diff, and include any remaining issues (including Issue-level findings with no specific line) in the top-level review body:

   Write the body and each inline comment to temp files and let `jq --rawfile` build the payload — never hand-escape quotes/newlines inside JSON (multi-line Japanese text with `"` and `${...}` reliably breaks a raw heredoc and yields a 400):

```bash
cat > /tmp/rv_body.md << 'EOF'
### Code review

<honest overall assessment in 1-2 sentences (see f). Then list any issues not mappable to diff lines.>

🤖 Generated with [Claude Code](https://claude.ai/code)

<sub>- If this code review was useful, please react with 👍. Otherwise, react with 👎.</sub>
EOF
cat > /tmp/rv_c1.md << 'EOF'
<inline comment text>
EOF
jq -n --rawfile body /tmp/rv_body.md --rawfile c1 /tmp/rv_c1.md '{
  body: $body, event: "COMMENT",
  comments: [{path: "src/api/main.py", line: 318, side: "RIGHT", body: $c1}]
}' | gh api repos/{owner}/{repo}/pulls/{pull_number}/reviews --method POST --input -
rm -f /tmp/rv_body.md /tmp/rv_c1.md
```

   e. For multi-line inline comments, add `"start_line"` and `"start_side": "RIGHT"` fields alongside `"line"`.
   f. The top-level `body` must always include an honest overall assessment (1-2 sentences) regardless of whether issues exist or whether all issues are inline comments. If the PR is well-implemented, say so warmly and directly — this provides context for any minor comments that follow.
      When the same-PR dedup (step 4) suppressed findings already raised by other bots or reviewers, add 1-2 sentences to the body saying they were checked but not repeated, and note any that head confirms as fixed — otherwise the review reads as if it missed them.
   g. If NO issues can be placed inline (none of the flagged lines are in the diff), fall back to `gh pr comment` with the same body structure as d: the honest overall assessment first, then the findings as a numbered list with their category labels, then the `🤖 Generated with [Claude Code](https://claude.ai/code)` line and the 👍/👎 `<sub>` line. If there are no findings at all, say so after the assessment and name what you checked (bugs, CLAUDE.md compliance, universal engineering concerns, Issue alignment).
   h. Keep each inline comment body brief and self-contained.
   i. Avoid emojis in comment text.
   j. Review event: default to `"event": "COMMENT"`. Use `"APPROVE"` or `"REQUEST_CHANGES"` ONLY when the user explicitly instructs it in this conversation (eg. 「Approveして」, 「Request changesで」) — never infer it from finding severity. Exception: in re-review mode (step 1), if every prior finding is confirmed fully addressed in step 4d and zero new findings score above 0 in step 5, propose `"APPROVE"` in step 7's summary and post it only after the user approves. First-pass reviews (no prior findings to verify against) always keep the `"COMMENT"` default regardless of finding count. When approving with remaining minor findings, note in each comment that it does not block the merge.

---

Examples of false positives, for steps 4 and 5:

- Pre-existing issues
- Something that looks like a bug but is not actually a bug
- Pedantic nitpicks that a senior engineer wouldn't call out
- Issues that a linter, typechecker, or compiler would catch (eg. missing or incorrect imports, type errors, broken tests, formatting issues, pedantic style issues like newlines). No need to run these build steps yourself — assume CI runs them separately. Exception: if you have evidence the gate is not actually enforcing (eg. the CI script discards the tool's exit code, or a mandated pre-commit hook was plainly skipped), the violations are worth flagging.
- General code quality issues (eg. lack of test coverage, poor documentation), unless explicitly required in CLAUDE.md
- Note: security issues, backward compatibility breaks, and error propagation gaps are NOT false positives — these are explicitly checked by Agent #8
- Issues that are called out in CLAUDE.md, but explicitly silenced in the code (eg. due to a lint ignore comment)
- Changes in functionality that are likely intentional or are directly related to the broader change
- Real issues, but on lines that the user did not modify in their pull request
  - Exception: an unchanged line that becomes wrong *because of* code or config this PR introduces (eg. a doc sentence contradicted by a function this PR adds) is not pre-existing — score it on impact, not on whether the line moved.
- Prior PR comments that were already addressed in a subsequent commit or acknowledged by the PR author
- For Issue-scope findings: partial implementations that are clearly intentional (eg. the PR description says "first step of #N")
- Concerns explicitly deferred to a tracked issue in the PR body or the linked Issue's out-of-scope list (eg. "DoS limits deferred to #NNN") — verify the deferral statement exists and the issue is real, then score 0. If the deferral lives in a doc this PR edits, the sentence existing is not enough: check the doc's accuracy first (step 4, "PR-modified docs are not ground truth")
- Changes that are improvements over the previous behavior (eg. adding a tiebreaker column for deterministic pagination ordering) — reverting them would be a regression, so do not flag them even if behavior technically changes

Notes:

- Never cite CI status as evidence either way: a green check can mean the gate itself is broken, so "CI passed" does not clear a finding and "CI will catch it" does not justify dropping one.
- Steps 4-5 use subagents by default. A session directive like "do not call the Agent tool unless the user requested it" is conditional, not a prohibition — invoking this skill IS the user requesting this review. Only a hard block (tool absent, permission denied) counts as unavailable; in that case do not skip steps 4-5 — run the same dimensions and 0-100 rubric yourself and say plainly that you ran it single-context. Never describe a conditional directive to the user as a ban.
- Use `gh` to interact with GitHub (eg. to fetch a pull request, or to create inline comments), rather than web fetch.
- Make a todo list first.
- You must cite and link each bug (eg. if referring to a CLAUDE.md, you must link it). In a review body, give every finding a permalink formatted exactly as `https://github.com/{owner}/{repo}/blob/{full_sha}/{path}#L{start}-L{end}`, otherwise the Markdown preview will not render. The full SHA must be literal — a `$(git rev-parse HEAD)` substitution will not work, since the text is rendered as-is. Match the repo you are reviewing, and centre the range on the flagged line with at least one line of context either side (for lines 5-6, link `L4-L7`).
