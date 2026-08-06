---
name: create-issue
description: >
  Use this skill when creating a new GitHub issue, editing or rewriting an existing issue's
  body, improving issue descriptions, adding sub-issues, or closing issues.
  IMPORTANT: Also use this skill when the user asks to "enrich", "improve", "rewrite", "update",
  or "充実させる" an existing issue — not just when creating new ones. This skill contains
  critical writing guidelines (the "Issue Body Writing Guidelines" section) that govern how
  issue body text should be written for BOTH new and existing issues. The guidelines ensure
  issues delegate implementation decisions to developers rather than prescribing exact steps.
  Scope is the issue body only: posting issue comments needs no special handling, so do not
  invoke this skill for that. Automatically handles gh-sub-issue extension installation.
license: MIT
allowed-tools: Bash, AskUserQuestion
---

# GitHub Issue Management

Comprehensive GitHub issue management using gh CLI and sub-issue functionality.

## Instructions

### Prerequisites

Ensure gh-sub-issue extension is installed before using sub-issue functionality:

```bash
if ! gh extension list | grep -q "yahsan2/gh-sub-issue"; then
    gh extension install yahsan2/gh-sub-issue
fi
```

### Issue Creation

```bash
gh issue create \
  --title "Issue title" \
  --body "Detailed description" \
  --label "label1,label2" \
  --milestone <number>
```

**Template Handling**: If `.github/ISSUE_TEMPLATE/` exists, list the templates in it (`.md` / `.yml`) and offer their use.

**`.yml` (issue form) templates need different handling than `.md` templates.** `gh issue create --template <name>` only reliably works non-interactively for plain `.md` templates. For `.yml` issue forms (GitHub's structured form schema), that flag opens an interactive/browser prompt instead of composing with `--title`/`--body` — it is not scriptable. When the matching template is `.yml`:

1. Read the template file directly (`cat .github/ISSUE_TEMPLATE/<name>.yml`) to learn its section structure (the `body:` list's `attributes.label` values, and any `attributes.value` placeholder text).
2. Construct the `--body` string yourself, mirroring those section headings, via a heredoc passed to `gh issue create --title ... --body "$(cat <<'EOF' ... EOF)"`.
3. Apply the **Issue Body Writing Guidelines** below to fill in each section's content — the template dictates structure (headings), the guidelines dictate what goes under each heading.
4. Check the template's own `labels:` values against **Verify labels before using them** (below) before passing them — forms routinely name labels (eg. `triage`) that were never created in the repo.

**Verify labels before using them.** `gh issue create --label "a,b"` fails the entire command (including title/body) if *any* named label doesn't exist in the repo — there's no partial success. Run `gh label list` first (or catch the `not found` error and retry without the offending label) rather than assuming template-suggested labels (e.g. a form's default `labels:` field) exist as written.

### Sub-Issues

Create an issue and link it as a sub-issue to a parent:

```bash
ISSUE_URL=$(gh issue create --title "Sub-issue title" --body "Description")

# Extract issue number robustly
ISSUE_NUM=$(echo "$ISSUE_URL" | grep -oE '/([0-9]+)/?$' | grep -oE '[0-9]+')

gh sub-issue add <parent-number> "$ISSUE_NUM"
```

Link or unlink an existing issue:

```bash
gh sub-issue add <parent-number> <child-number>
gh sub-issue remove <parent-number> <child-number>
```

### Issue Editing

```bash
gh issue edit <issue-number> \
  --title "New title" \
  --body "New description" \
  --add-label "new-label1,new-label2" \
  --remove-label "old-label" \
  --add-assignee "@username" \
  --milestone <number>
```

**When editing issue body content** (rewriting, improving, or enriching an issue description),
always apply the **Issue Body Writing Guidelines** at the bottom of this skill before writing
any content. The guidelines ensure the body delegates implementation decisions to developers
rather than prescribing exact steps.

### Issue Closing

**Important**: Always confirm with user before closing issues using AskUserQuestion tool. After confirmation:

```bash
gh issue close <issue-number> --comment "Closing reason"
```

### Error Handling

Common errors and solutions:

| Error | Cause | Solution |
|-------|-------|----------|
| `gh: command not found` | GitHub CLI not installed | Install gh CLI |
| `failed to run prompt` | Not authenticated | Run `gh auth login` |
| `GraphQL: Resource not accessible` | No repository access | Check repository permissions |
| `Not Found (HTTP 404)` | Issue doesn't exist | Verify issue number |
| `sub-issue must belong to same repository` | Cross-repo attempt | Both issues must be in same repo |
| `could not add label: '<name>' not found` | Label doesn't exist in repo (whole command aborts) | Run `gh label list`, drop/replace the missing label, retry |

## Output Format

Report each operation result in one line: `✓ <action> #XX: <URL>` on success, `✗ Error: <specific description>` on failure.

## Examples

### Example 1: Sub-Issue Creation with Parent

```
User: Create a sub-issue of #38 titled "Improve token efficiency"

Execute:
# Ensure extension installed
if ! gh extension list | grep -q "yahsan2/gh-sub-issue"; then
    gh extension install yahsan2/gh-sub-issue
fi

# Create issue
ISSUE_URL=$(gh issue create --title "Improve token efficiency" --body "Reduce response size")
ISSUE_NUM=$(echo "$ISSUE_URL" | grep -oE '/([0-9]+)/?$' | grep -oE '[0-9]+')

# Link as sub-issue
gh sub-issue add 38 "$ISSUE_NUM"

Output:
✓ Created issue #44
✓ Linked issue #44 as sub-issue of #38
```

### Example 2: Close Issue with Confirmation

```
User: Close issue #47 as duplicate

Execute:
# Use AskUserQuestion tool to confirm
# After user confirms:

gh issue close 47 --comment "Closing as duplicate of #44"

Output:
✓ Closed issue #47
```

## Issue Body Writing Guidelines

issue の本文は、開発者が単なる作業者にならないよう、**何を達成したいか（What）** と **どう実装するかの示唆（How）** を意識的に分けて書く。

### 構成の原則

| セクション | 書き方 |
|---|---|
| **背景・やりたいこと** | 目的・課題・制約を明確に。達成したいゴールを書く |
| **想定される対応内容** | 実装の方向性をぼかして示す。箇条書きで What レベルに留める |
| **実装の詳細** | 原則として書かない。担当者が判断する領域 |

### 良い例と悪い例

**❌ 悪い例（作業指示になっている）**:
```
## 対応内容
- variables.tf に gcs_temp_mount_enabled 変数を追加（type: bool, default: false）
- storage.tf に google_storage_bucket リソースを追加し lifecycle_rule で age=1 を設定
- cloudrun.tf の template に execution_environment = "EXECUTION_ENVIRONMENT_GEN2" を追加
```

**✅ 良い例（考える余地がある）**:
```
## やりたいこと
- GCSFuse マウントの構成を Terraform で管理する
- 必要なテナントのみ有効化できるようにする（デフォルト無効）

## 想定される対応内容
大まかに以下のような変更が考えられるが、実装方法は担当者の判断に委ねる。
- **変数追加**: マウントの有効/無効を切り替えるフラグ
- **バケット作成**: 一時ファイル用 GCS バケット（残留ファイルの自動削除も考慮）
- **IAM**: 最小権限の原則に従った書き込み権限付与
- **Cloud Run**: GCSFuse に必要な設定の追加
```

### ポイント

- 「想定される対応内容」には「大まかに以下が考えられるが、実装方法は担当者の判断に委ねる」などの一文を添える
- 変数名・リソース名・設定値などの具体的な実装詳細は書かない
- 参考リンクや関連 issue は積極的に記載する（担当者の調査コストを下げる）
- スコープを限定・分割する場合（ファイル種別・段階など）は、その理由と順序の根拠を本文に記録する（「なぜこれだけ先行するか」を後から追えるようにする）

## Notes

- **Same Repository**: Parent and child issues must exist in the same repository
- **Template Priority**: Project templates (`.github/ISSUE_TEMPLATE/`) → Organization templates → No template
- **Assignee**: Do NOT auto-assign `@me` or any user unless the user explicitly requests it. Assignees should be set only when the user specifies who should handle the issue.
- **Confirmation**: Always confirm destructive operations (close, delete) using AskUserQuestion tool
