---
name: "Zenn記事検索"
description: "Zennの技術記事を検索して参照します。ユーザーがZennの記事、Zennで検索、技術記事を探す、日本語の技術情報を調べる、などを依頼した際に使用してください。"
allowed-tools: Bash, WebSearch
license: MIT
---

# Zenn記事検索

Zenn (zenn.dev) の日本語技術記事を検索して参照する。

## 検索方法

### 1. Zenn API検索スクリプト（推奨）

Zenn公式API（`https://zenn.dev/api/search`）を直接叩くため、正確なメタデータ（いいね数・コメント数・公開日）が得られる。

```bash
python3 ~/.claude/skills/zenn-search/scripts/search_zenn.py "検索キーワード" [オプション]
```

| オプション | 既定 | 説明 |
|---|---|---|
| `--order {daily\|alltime\|latest}` | `daily` | `daily`=今日話題／`alltime`=全期間の人気（殿堂入り）／`latest`=最新順 |
| `--page N` | 1 | ページ番号 |
| `--limit N` | 5 | 表示件数 |
| `--json` | — | JSON形式で出力 |

### 2. WebSearch（代替手段）

スクリプトが使えないときや、より広範に探したいときは WebSearch を `allowed_domains: ["zenn.dev"]` で使う。

## 検索のコツ

- **複合キーワードに注意**: 複数語のクエリ（例:「ADR 技術負債」）は0件になりやすい。単語を分けて複数回検索する
- 日本語と英語のキーワードを組み合わせると当たりやすい

## 検索結果の提示

タイトル・著者名・URL・いいね数・コメント数・公開日を整理し、関連性の高い記事を3〜5件ピックアップする。必要に応じて追加検索のキーワードを提案し、詳細を確認できることを伝える。
