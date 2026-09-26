---
name: create-issue
description: >
  Use this skill when creating a new GitHub issue, editing or rewriting an existing issue's
  body, improving issue descriptions, adding sub-issues, or closing issues. IMPORTANT: also
  use it when the user asks to "enrich", "improve", "rewrite", "update", or "充実させる" an
  existing issue — the "Issue Body Writing Guidelines" section governs body text for BOTH new
  and existing issues, ensuring issues delegate implementation decisions to developers rather
  than prescribing exact steps. Closing includes the case where `gh issue close` is an embedded
  step of a larger task (e.g. recording a decision on an issue) — consult the "Issue Closing"
  rules before any close. Scope is the issue body only: posting issue comments needs no special
  handling, so do not invoke this skill for that. Handles gh-sub-issue extension installation
  when sub-issues are involved.
allowed-tools: Bash, AskUserQuestion
license: MIT
---

# GitHub Issue Management

Any issue body you write — a new issue, or rewriting/improving/enriching an existing one — must apply the **Issue Body Writing Guidelines** (last section) while drafting it. A template dictates structure; the guidelines dictate what goes under each heading.

## Prerequisites

Only when the task actually involves sub-issues (linking, unlinking, creating children):

```bash
if ! gh extension list | grep -q "yahsan2/gh-sub-issue"; then
    gh extension install yahsan2/gh-sub-issue
fi
```

## Issue Creation

```bash
gh issue create \
  --title "Issue title" \
  --body "Detailed description" \
  --label "label1,label2" \
  --milestone <number>
```

**Template handling**: Project templates (`.github/ISSUE_TEMPLATE/`) → organization templates → no template. If templates exist, list them (`.md` / `.yml`) and offer their use.

**`.yml` (issue form) templates:** `gh issue create --template <name>` only works non-interactively for plain `.md` templates; for `.yml` issue forms it opens an interactive/browser prompt instead of composing with `--title`/`--body`. For a `.yml` template:

1. Read the file (`cat .github/ISSUE_TEMPLATE/<name>.yml`) to learn its section structure (the `body:` list's `attributes.label` values and any `attributes.value` placeholders).
2. Construct `--body` yourself, mirroring those headings, via a heredoc passed to `gh issue create --title ... --body "$(cat <<'EOF' ... EOF)"`.
3. Decide whether to apply the template's `title:` prefix (eg. `[タスク]: `) by matching how comparable existing issues — same nature, same tracking method — are titled. Ask the user if the repo is inconsistent.
4. Fill each section's content per the **Issue Body Writing Guidelines**.
5. Check the template's own `labels:` values against the rule below before passing them — forms routinely name labels (eg. `triage`) that were never created in the repo.

**Verify labels before using them.** `gh issue create --label "a,b"` fails the entire command (including title/body) if *any* named label doesn't exist — there's no partial success. Run `gh label list` first, or catch the `not found` error and retry without the offending label (see Error Handling).

## Sub-Issues

```bash
ISSUE_URL=$(gh issue create --title "Sub-issue title" --body "Description")
ISSUE_NUM=$(echo "$ISSUE_URL" | grep -oE '/([0-9]+)/?$' | grep -oE '[0-9]+')
gh sub-issue add <parent-number> "$ISSUE_NUM"

# Link or unlink an existing issue
gh sub-issue add <parent-number> <child-number>
gh sub-issue remove <parent-number> <child-number>
```

Parent and child must live in the same repository.

## Issue Editing

```bash
gh issue edit <issue-number> \
  --title "New title" \
  --body "New description" \
  --add-label "new-label1,new-label2" \
  --remove-label "old-label" \
  --add-assignee "@username" \
  --milestone <number>
```

Do NOT auto-assign `@me` or anyone else unless the user explicitly says who should handle the issue.

## Issue Closing

**Important**: Always confirm with the user (AskUserQuestion) before closing. Judge closability by whether the completion condition is met:

- issue の完了がリポジトリへの変更（コード・ドキュメント・規約化など）を伴う場合、その変更がマージされる前に手動クローズしない。PR 本文に `closes #N` と書き、マージによる自動クローズに委ねる（決定をコメントに記録した時点でのクローズは早計）
- 手動クローズしてよいのは、変更を伴わず issue 上の記録だけで完結する場合（重複・見送り・調査のみ 等）

```bash
gh issue close <issue-number> --comment "Closing reason"
```

## Error Handling

| Error | Cause | Solution |
|-------|-------|----------|
| `gh: command not found` | GitHub CLI not installed | Install gh CLI |
| `failed to run prompt` | Not authenticated | Run `gh auth login` |
| `GraphQL: Resource not accessible` | No repository access | Check repository permissions |
| `Not Found (HTTP 404)` | Issue doesn't exist | Verify issue number |
| `sub-issue must belong to same repository` | Cross-repo attempt | Both issues must be in same repo |
| `could not add label: '<name>' not found` | Label doesn't exist (whole command aborts) | Run `gh label list`, drop/replace the label, retry |

## Output Format

Report each operation in one line: `✓ <action> #XX: <URL>` on success, `✗ Error: <specific description>` on failure.

## Issue Body Writing Guidelines

issue の本文は、開発者が単なる作業者にならないよう、**何を達成したいか（What）** と **どう実装するかの示唆（How）** を意識的に分けて書く。実装に着手する頃には issue 作成時より詳細な情報が実施者に見えており、実装方法はその時点の情報をもとに担当者が判断したほうが精度が高いため。

### 構成の原則

| セクション | 必須度 | 書き方 |
|---|---|---|
| **背景・やりたいこと** | 必須 | 目的・課題・制約を明確に。達成したいゴールを書く |
| **想定される対応内容** | 実質必須 | 実装の方向性をぼかして示す。箇条書きで What レベルに留める。方針自体が固まっていない場合は無理に埋めず、未確定である旨を書いて省略してよい |
| **対象外・やらないこと** | 任意 | スコープ外を明示し、意図と異なる実装が進むのを防ぐ。隣接範囲との混同が起きうる場合のみ書く |
| **受け入れ条件** | 任意 | 満たすべき状態・振る舞いを書く。特定の実装手段を指定しない |
| **実装の詳細** | 原則として書かない | 担当者が判断する領域 |

### 良い例と悪い例

**❌ 悪い例（作業指示になっている）**:
```
## 対応内容
- config.py に JOB_QUEUE_ENABLED 変数を追加（type: bool, default: false）
- queue.py に JobQueue クラスを追加し max_retries=3 を設定
- worker.py の起動処理に queue.start_consumer() の呼び出しを追加
```

**✅ 良い例（考える余地がある）**:
```
## やりたいこと
- 重い処理を非同期ジョブキューに逃がし、リクエストの応答時間を短縮する
- 既存の同期処理から段階的に移行できるようにする（デフォルト無効）

## 想定される対応内容
大まかに以下のような変更が考えられるが、実装方法は担当者の判断に委ねる。
- **フラグ追加**: 非同期化の有効/無効を切り替える設定
- **キューの導入**: リトライ・失敗時の扱いも含めた設計
- **権限**: 最小権限の原則に従ったアクセス権付与
- **呼び出し側の変更**: 既存の同期処理からの移行方法

## 対象外
- 既存の同期 API のインターフェース変更は行わない

## 受け入れ条件
- [ ] 対象の重い処理が非同期ジョブキュー経由で実行される
- [ ] 移行前の同期処理と比較して、リクエストの応答時間が短縮されている
```

### ポイント

- 参考リンクや関連 issue は積極的に記載する（担当者の調査コストを下げる）
- 1つの箇条書きに複数の事実を詰め込まない（1行1情報）。長くなる項目は小見出し＋短い箇条書きに分解する
- `#N` 形式の issue/PR 参照はタイトル付きリンクに展開され行が膨らむため、文中に埋め込まず参照専用の行（1行1リンク）に分ける
- スコープを限定・分割する場合（ファイル種別・段階など）は、その理由と順序の根拠を本文に記録する（「なぜこれだけ先行するか」を後から追えるようにする）

### 簡潔さ

本文の目安は 35 行程度（対象外・受け入れ条件まで含めた実例ベース）。大きく超える場合は、参考リンクへの切り出しや issue 分割を検討する。以下は書かない:

- 変数名・リソース名・設定値・実装コード例などの具体的な実装詳細（担当者が判断する領域）
- 実装手順のステップ書き（スコープ分割時の順序記録とは別）
- 設計案・調査結果の全文転載（要点のみ書き、詳細は参考リンクに委ねる）
