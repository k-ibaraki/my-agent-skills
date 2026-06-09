---
name: create-issue
description: >
  Use this skill for ANY GitHub issue operation: creating new issues, editing or rewriting existing
  issue body content, improving issue descriptions, adding sub-issues, or closing issues.
  IMPORTANT: Also use this skill when the user asks to "enrich", "improve", "rewrite", "update",
  or "充実させる" an existing issue — not just when creating new ones. This skill contains
  critical writing guidelines (the "Issue Body Writing Guidelines" section) that govern how
  issue body text should be written for BOTH new and existing issues. The guidelines ensure
  issues delegate implementation decisions to developers rather than prescribing exact steps.
  Automatically handles gh-sub-issue extension installation.
allowed-tools: Bash, AskUserQuestion
license: MIT
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

Create a new issue with the following command pattern:

```bash
gh issue create \
  --title "Issue title" \
  --body "Detailed description" \
  --label "label1,label2" \
  --milestone <number>
```

**Template Handling**:

Check for available templates and offer their use:

```bash
if [ -d ".github/ISSUE_TEMPLATE" ]; then
    TEMPLATES=$(find .github/ISSUE_TEMPLATE -name "*.md" -o -name "*.yml" 2>/dev/null)
    if [ -n "$TEMPLATES" ]; then
        # List available templates to user
        echo "Available templates:"
        echo "$TEMPLATES" | sed 's|.github/ISSUE_TEMPLATE/||g'
        # Use template if specified
        gh issue create --template <template-name>
    fi
fi
```

### Sub-Issue Creation

Create an issue and automatically link it as a sub-issue to a parent:

```bash
# Create the issue
ISSUE_URL=$(gh issue create --title "Sub-issue title" --body "Description")

# Extract issue number robustly
ISSUE_NUM=$(echo "$ISSUE_URL" | grep -oE '/([0-9]+)/?$' | grep -oE '[0-9]+')

# Verify extraction succeeded
if [ -z "$ISSUE_NUM" ]; then
    echo "✗ Error: Failed to extract issue number from URL: $ISSUE_URL"
    exit 1
fi

# Link as sub-issue
if gh sub-issue add <parent-number> "$ISSUE_NUM"; then
    echo "✓ Created issue #$ISSUE_NUM and linked as sub-issue of #<parent-number>"
else
    echo "✗ Error: Failed to link issue #$ISSUE_NUM as sub-issue"
    exit 1
fi
```

### Linking Existing Issue as Sub-Issue

Add an existing issue as a sub-issue to a parent:

```bash
if gh sub-issue add <parent-number> <child-number>; then
    echo "✓ Linked issue #<child-number> as sub-issue of #<parent-number>"
else
    echo "✗ Error: Failed to link sub-issue (check both issues exist in same repository)"
    exit 1
fi
```

### Removing Sub-Issue Link

Remove sub-issue relationship while keeping the issue open:

```bash
if gh sub-issue remove <parent-number> <child-number>; then
    echo "✓ Removed sub-issue link between #<parent-number> and #<child-number>"
else
    echo "✗ Error: Failed to remove sub-issue link"
    exit 1
fi
```

### Issue Editing

Modify existing issue properties:

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

Handle edit errors appropriately:

```bash
if gh issue edit <issue-number> --title "New title"; then
    echo "✓ Updated issue #<issue-number>"
else
    echo "✗ Error: Failed to edit issue (check issue exists and you have write access)"
    exit 1
fi
```

### Issue Closing

**Important**: Always confirm with user before closing issues using AskUserQuestion tool.

```bash
# Confirm before closing (use AskUserQuestion tool)
# After confirmation:

if gh issue close <issue-number> --comment "Closing reason"; then
    echo "✓ Closed issue #<issue-number>"
else
    echo "✗ Error: Failed to close issue"
    exit 1
fi
```

For simple close without comment:

```bash
gh issue close <issue-number>
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

Always wrap commands in error checks:

```bash
if ! <command>; then
    echo "✗ Error: <descriptive message>"
    exit 1
fi
```

## Output Format

Use consistent output messages:

**Success messages:**
```
✓ Created issue #XX: https://github.com/owner/repo/issues/XX
✓ Linked issue #YY as sub-issue of #XX
✓ Updated issue #XX
✓ Closed issue #XX
✓ Removed sub-issue link between #XX and #YY
```

**Error messages:**
```
✗ Error: <specific error description>
```

## Examples

### Example 1: Basic Issue Creation

```
User: Create an issue titled "Fix login bug"

Execute:
gh issue create --title "Fix login bug" --body "Users cannot log in with email"

Output:
✓ Created issue #123: https://github.com/owner/repo/issues/123
```

### Example 2: Sub-Issue Creation with Parent

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

### Example 3: Link Existing Issue as Sub-Issue

```
User: Make issue #47 a sub-issue of #38

Execute:
if ! gh extension list | grep -q "yahsan2/gh-sub-issue"; then
    gh extension install yahsan2/gh-sub-issue
fi

gh sub-issue add 38 47

Output:
✓ Linked issue #47 as sub-issue of #38
```

### Example 4: Edit Issue Title and Labels

```
User: Change issue #47 title to "Range expansion feature review" and add "enhancement" label

Execute:
gh issue edit 47 \
  --title "Range expansion feature review" \
  --add-label "enhancement"

Output:
✓ Updated issue #47
```

### Example 5: Close Issue with Confirmation

```
User: Close issue #47 as duplicate

Execute:
# Use AskUserQuestion tool to confirm
# After user confirms:

gh issue close 47 --comment "Closing as duplicate of #44"

Output:
✓ Closed issue #47
```

### Example 6: Remove Sub-Issue Link

```
User: Remove the sub-issue link between #38 and #47

Execute:
gh sub-issue remove 38 47

Output:
✓ Removed sub-issue link between #38 and #47
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

## Notes

- **GitHub CLI Required**: Must have `gh` CLI installed and authenticated (`gh auth login`)
- **Repository Context**: Commands must be run from within a Git repository directory
- **Sub-Issue Extension**: `yahsan2/gh-sub-issue` extension required for sub-issue operations (auto-installed)
- **Same Repository**: Parent and child issues must exist in the same repository
- **Permissions**: Write access required for issue creation/editing, read access sufficient for viewing
- **Template Priority**: Project templates (`.github/ISSUE_TEMPLATE/`) → Organization templates → No template
- **Assignee**: Do NOT auto-assign `@me` or any user unless the user explicitly requests it. Assignees should be set only when the user specifies who should handle the issue.
- **Confirmation**: Always confirm destructive operations (close, delete) using AskUserQuestion tool
- **Robust Parsing**: Use `grep -oE '/([0-9]+)/?$' | grep -oE '[0-9]+'` for extracting issue numbers from URLs
