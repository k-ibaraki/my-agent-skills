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

ユーザーが PR の作成を依頼したとき、または `gh pr create` を使うときに以下の手順を踏む。

## 0. stacked PR にすべきか見る

現ブランチの**分岐元が未マージ PR のブランチ**なら、その PR に重ねた stacked PR にできる。
この条件に当てはまらないときは何もせず手順1へ進む（PR の大きさなどで勝手に提案しない）。

```bash
cur=$(git branch --show-current)
gh pr list --state open --json number,headRefName --jq '.[] | [.number,.headRefName] | @tsv' |
  while IFS=$'\t' read -r num branch; do
    [ "$branch" = "$cur" ] && continue
    ref=$(git rev-parse -q --verify "origin/$branch" || git rev-parse -q --verify "$branch") || continue
    git merge-base --is-ancestor "$ref" HEAD && printf '#%s\t%s\n' "$num" "$branch"
  done || true
```

- **候補が複数出たら、一番上の層だけを選ぶ**。`a <- b <- c` と積まれていると祖先が全て並び、
  最初の行を取ると `--base` が最下層になって中間層の差分まで抱き込む。
  `git merge-base --is-ancestor <候補X> <候補Y>` が真なら Y が上。`--base` と `gh stack link` に渡すのは直近の親その一つだけ
- **親ブランチを rebase / amend した後は検出できない**（共通の commit が消えるため）。既に stack にしてあるなら `gh stack view --json` が正本
- 親の PR ブランチを HEAD に merge しただけでも検出される（偽陽性）。機械判定を鵜呑みにしない
- 該当したら**ユーザーに確認を取る**。承認を得るまで `gh stack` は実行しない（`gh stack link` は GitHub 上の PR のベースを書き換えうる外向き操作）
- 無関係な作業は重ねない。stack は一直線（親1・子1）で、積んだ上位は下位のマージ待ちに拘束される

承認が得られたら、**PR 本文は従来どおりこのスキルで組み**（手順2）、連結だけを `gh stack` に任せる。

```bash
gh pr create --base <下位のブランチ> --title "タイトル" --body-file <path>
gh stack link <下位PR番号> <このブランチ>   # 既存 PR を stack に繋ぐ。本文は書き換えられない
```

- **`gh stack submit --auto` に新規 PR を作らせない**。`gh stack` が作った PR はタイトルも本文も自動生成になり、テンプレートが当たらない（既存 PR の本文は触られない）
- `sync` / `rebase` / `merge` / コンフリクト復旧 / exit code など**以降の操作は gh-stack スキルに従う**（仕様が動くため写しを置かない）
- 使えないとき:
  - 拡張が無い → `gh extension install github/gh-stack` を提案し、承認を得てから入れる
  - exit 9（リポジトリが stacked PR 未対応）→ stack は諦め、`--base` を下位ブランチにした依存 PR として出し、本文に依存先の PR を明記する

## 1. テンプレートを探す

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
# 引数を省くと gh は fork 元を返す。PR の向き先リポジトリを明示すること
OWNER=$(gh repo view <owner>/<repo> --json owner --jq .owner.login)
for p in .github/pull_request_template.md .github/PULL_REQUEST_TEMPLATE.md; do
  body=$(gh api "repos/$OWNER/.github/contents/$p" --jq '.content' 2>/dev/null) || continue
  [ -n "$body" ] && echo "$body" | base64 -d && break
done
```

- `.github/PULL_REQUEST_TEMPLATE/` に複数ある場合は、どれを使うかユーザーに確認する
- **どちらにも無い場合のみ**、`## 概要` `## 変更内容` `## 確認したこと` の3節で簡潔に書く。勝手に長いテンプレートを創作しない

## 2. 本文を組み立てる

- 見つけたテンプレートの**見出し構成をそのまま維持する**。節を削らない・足さない・並べ替えない
- 説明用の HTML コメント（`<!-- 〜を記載してください -->`）は削ってよい。
  ただし**指示として機能しているコメント**（レビュー bot への依頼など）は残す
- チェックリストは項目文を書き換えない。満たせていない項目はチェックを付けず理由を1行併記する
  （該当しない項目は「（該当なし）」、該当するが未対応の項目は何が未対応かを明記する）
- issue を書く節がある場合は **`closes #番号`** と記載する（マージ時に自動 close される）
  - 関連 issue が無ければ `なし`。別リポジトリの issue は `owner/repo#番号` で参照する
  - **その PR だけで issue が完了しない場合や、close の可否が他者の判断による場合は
    `closes` を使わず `関連:` と記載する**（機構で勝手に閉じない）
  - **stack の中間層はこれに当たる**。最上位の層だけが `closes` を書き、下の層は `関連:` にする

## 3. PR を作成する

```bash
# 本文はファイルに書き出してから渡す（インラインのヒアドキュメントは
# クォートと長さの両面で壊れやすい）
gh pr create --base <ベースブランチ> --title "タイトル" --body-file <path>
```

- 本文ファイルの書き出しと `gh pr create` は別々のコマンドで実行する（承認フック等が呼び出しごとブロックすると、heredoc も一緒に失われるため）
- **`--base` は必ず明示する**。デフォルトブランチと開発用ブランチが異なるリポジトリがある。
  プロジェクトの運用ルールや直近のマージ履歴から向き先を確認する
  - **stack の中では `--base` は一つ下の層のブランチ**であって `main` ではない
- **フォークから出す場合は `--repo <owner>/<repo>` も明示する**。省略すると `gh` は親リポジトリを向き先の既定にするため、意図せず本家へ PR が飛ぶ
- ブランチが未プッシュなら先に `git push -u origin <branch>` する
- `gh pr create --template` は `--body` と併用できないため使わない。テンプレートは自分で読んで本文に展開する
