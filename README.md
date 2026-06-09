# my-agent-skills

個人的に作った or よく使っている Claude Code / AI エージェント向けスキル集です。  
勝手に参照・使用してください。

## スキル一覧

| スキル | 説明 | インストール |
|---|---|---|
| [code-review](skills/code-review/) | PRのコードレビューを実施 | `gh skill install k-ibaraki/my-agent-skills code-review` |
| [create-issue](skills/create-issue/) | GitHub Issueの作成・編集・改善 | `gh skill install k-ibaraki/my-agent-skills create-issue` |
| [ddg-search](skills/ddg-search/) | DuckDuckGo APIでWeb検索 | `gh skill install k-ibaraki/my-agent-skills ddg-search` |
| [github-activity-report](skills/github-activity-report/) | GitHub活動レポート生成（スタンドアップ等に） | `gh skill install k-ibaraki/my-agent-skills github-activity-report` |
| [grill-me](skills/grill-me/) | 設計・計画を深掘りインタビュー | `gh skill install k-ibaraki/my-agent-skills grill-me` |
| [kiro-delegate](skills/kiro-delegate/) | kiro-cli にタスクを委譲 | `gh skill install k-ibaraki/my-agent-skills kiro-delegate` |
| [pr-template](skills/pr-template/) | PRテンプレートを使ったPR作成 | `gh skill install k-ibaraki/my-agent-skills pr-template` |
| [self-review](skills/self-review/) | PR前のセルフコードレビュー | `gh skill install k-ibaraki/my-agent-skills self-review` |
| [zenn-search](skills/zenn-search/) | Zennの技術記事を検索 | `gh skill install k-ibaraki/my-agent-skills zenn-search` |

---

## gh skill コマンドの使い方

`gh skill` は GitHub CLI の拡張機能で、AI エージェントスキルを管理するコマンドです。  
Claude Code, GitHub Copilot, Cursor, Codex, Gemini CLI など複数のエージェントに対応しています。

### 前提条件

```bash
# GitHub CLI のインストール（未導入の場合）
brew install gh

# gh skill 拡張機能のインストール
gh extension install github/gh-skill
```

### スキルのインストール

```bash
# インタラクティブにスキルとエージェントを選んでインストール
gh skill install k-ibaraki/my-agent-skills
```

```bash
# 特定のスキルをインストール（Claude Code、ユーザースコープ）
gh skill install k-ibaraki/my-agent-skills code-review --agent claude-code --scope user

# プロジェクトスコープでインストール（リポジトリ内の .claude/skills/ に配置）
gh skill install k-ibaraki/my-agent-skills code-review --agent claude-code --scope project

# 複数スキルを続けてインストール
gh skill install k-ibaraki/my-agent-skills create-issue --agent claude-code --scope user
gh skill install k-ibaraki/my-agent-skills self-review --agent claude-code --scope user
```

**スコープの違い：**

| スコープ | 配置先 | 有効範囲 |
|---|---|---|
| `user`（推奨） | `~/.claude/skills/` | すべてのプロジェクト |
| `project` | `.claude/skills/` | そのリポジトリのみ |

### インストール済みスキルの確認・更新

```bash
# インストール前にスキル内容をプレビュー
gh skill preview k-ibaraki/my-agent-skills code-review

# インストール済みスキルをすべて最新版に更新
gh skill update --all

# 特定のスキルだけ更新
gh skill update code-review
```

### スキルの検索

```bash
# GitHub 上のスキルを検索
gh skill search "code review"
gh skill search "zenn"
```

### バージョン固定

```bash
# タグを指定してインストール（安定版に固定したい場合）
gh skill install k-ibaraki/my-agent-skills code-review@v1.0.0 --agent claude-code --scope user
```

### ローカルからインストール

```bash
# このリポジトリをクローンしてローカルからインストール
git clone https://github.com/k-ibaraki/my-agent-skills.git
gh skill install ./my-agent-skills code-review --from-local --agent claude-code --scope user
```

---

## ライセンス

[MIT](LICENSE)
