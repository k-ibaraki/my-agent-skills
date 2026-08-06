---
name: "PR(プルリクエスト)テンプレート"
description: "プルリクエスト作成時に、リポジトリまたは組織のPRテンプレートを探して本文を組み立てます。ユーザーがプルリクエストの作成を依頼したときや、`gh pr create` コマンドを使用してPRを作成する際に使用してください。"
allowed-tools: Bash
license: MIT
---

# PR Template Skill

PR 本文はリポジトリ・組織が定めたテンプレートに従って組み立てる。
このスキルはテンプレート実体を持たない。プロジェクト側のテンプレートが唯一の正本であり、
スキル側に写しを置くと必ず陳腐化するため。

## 使用タイミング

- ユーザーがプルリクエストの作成を依頼したとき
- `gh pr create` コマンドを使用してPRを作成する際

## 手順

### 1. テンプレートを探す

上から順に探し、最初に見つかったものを使う。

```bash
# リポジトリ内（複数テンプレート形式が最優先）
find .github/PULL_REQUEST_TEMPLATE -name '*.md' 2>/dev/null
for p in .github/pull_request_template.md .github/PULL_REQUEST_TEMPLATE.md \
         pull_request_template.md PULL_REQUEST_TEMPLATE.md \
         docs/pull_request_template.md docs/PULL_REQUEST_TEMPLATE.md; do
  [ -f "$p" ] && echo "found: $p" && break
done
```

リポジトリに無ければ組織既定を見る。

```bash
OWNER=$(gh repo view --json owner --jq .owner.login)
for p in .github/pull_request_template.md .github/PULL_REQUEST_TEMPLATE.md; do
  body=$(gh api "repos/$OWNER/.github/contents/$p" --jq '.content' 2>/dev/null) || continue
  [ -n "$body" ] && echo "$body" | base64 -d && break
done
```

- `.github/PULL_REQUEST_TEMPLATE/` に複数ある場合は、どれを使うかユーザーに確認する
- **どちらにも無い場合のみ**、`## 概要` `## 変更内容` `## 確認したこと` の3節で簡潔に書く。
  勝手に長いテンプレートを創作しない

### 2. 本文を組み立てる

- 見つけたテンプレートの**見出し構成をそのまま維持する**。節を削らない・足さない・並べ替えない
- 説明用の HTML コメント（`<!-- 〜を記載してください -->`）は削ってよい。
  ただし**指示として機能しているコメント**（レビュー bot への依頼など）は残す
- チェックリストは項目文を書き換えない。満たせていない項目はチェックを付けず、
  理由を1行併記する（該当しない項目は「（該当なし）」、
  該当するが未対応の項目は何が未対応かを明記する）
- issue を書く節がある場合は **`closes #番号`** と記載する（マージ時に自動 close される）
  - 関連 issue が無ければ `なし`
  - 別リポジトリの issue は `owner/repo#番号` で参照する
  - **その PR だけで issue が完了しない場合や、close の可否が他者の判断による場合は
    `closes` を使わず `関連:` と記載する**（機構で勝手に閉じない）

### 3. PR を作成する

```bash
gh pr create --base <ベースブランチ> --title "タイトル" --body "$(cat <<'EOF'
（組み立てた本文）
EOF
)"
```

- **`--base` は必ず明示する**。デフォルトブランチと開発用ブランチが異なるリポジトリがある。
  プロジェクトの運用ルールや直近のマージ履歴から向き先を確認する
- ブランチが未プッシュなら先に `git push -u origin <branch>` する
- `gh pr create --template` は `--body` と併用できないため使わない。
  テンプレートは自分で読んで本文に展開する
