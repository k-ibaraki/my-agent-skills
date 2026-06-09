---
name: "Zenn記事検索"
description: "Zennの技術記事を検索して参照します。ユーザーがZennの記事、Zennで検索、技術記事を探す、日本語の技術情報を調べる、などを依頼した際に使用してください。"
allowed-tools: Bash, WebSearch
license: MIT
---

# Zenn記事検索

このスキルは、Zenn (zenn.dev) に投稿された日本語技術記事を効率的に検索し、参照するために使用します。

## Instructions

### 推奨される検索方法

**1. Zenn API検索スクリプトの使用（推奨）**

このスキルには、Zenn公式APIを直接使用する専用スクリプトが含まれています。

スクリプトの実行方法：
```bash
python3 ~/.claude/skills/zenn-search/scripts/search_zenn.py "検索キーワード" [オプション]
```

利用可能なオプション：
- `--order {daily|alltime|latest}`: 並び順を指定（デフォルト: daily）
  - `daily`: 本日の人気順
  - `alltime`: 全期間の人気順
  - `latest`: 最新順
- `--page N`: ページ番号を指定（デフォルト: 1）
- `--limit N`: 表示件数を指定（デフォルト: 5）
- `--json`: JSON形式で出力

スクリプトの使用例：
```bash
# 基本的な検索
python3 ~/.claude/skills/zenn-search/scripts/search_zenn.py "Next.js"

# 全期間人気順で10件表示
python3 ~/.claude/skills/zenn-search/scripts/search_zenn.py "React hooks" --order alltime --limit 10

# 2ページ目を表示
python3 ~/.claude/skills/zenn-search/scripts/search_zenn.py "TypeScript" --page 2
```

スクリプトを使用する利点：
- Zenn公式APIを直接利用するため、正確で最新の結果を取得
- いいね数、コメント数、公開日などの詳細情報を表示
- ページネーション対応で大量の結果も効率的に閲覧可能

**2. WebSearchツールの使用（代替手段）**

スクリプトが使用できない場合や、より広範な検索が必要な場合：
- WebSearchツールを使用して検索を実行
- `allowed_domains: ["zenn.dev"]` パラメータでZennドメインに限定
- 検索クエリの例：
  - 「Next.js App Router 2025 site:zenn.dev」
  - 「React Server Components zenn.dev」

### 検索結果の提示

検索結果について、以下の情報を整理して提示します：
- タイトル（絵文字付き）
- 著者名
- URL
- いいね数とコメント数
- 公開日

ユーザーに対して：
- 最も関連性の高い記事を3〜5件ピックアップ
- 必要に応じて追加検索のキーワードを提案
- より詳しく知りたい記事があれば、その記事の詳細を確認可能であることを伝える

## Examples

### 例1：基本的な検索（APIスクリプト使用）
```
ユーザー: Next.jsのApp Routerについて、最新のZenn記事を探して
Claude: Zenn API検索スクリプトを使用して、Next.js App Routerに関する記事を検索します。

実行コマンド:
python3 ~/.claude/skills/zenn-search/scripts/search_zenn.py "Next.js App Router" --order latest

結果を解析して、上位5件の記事を紹介します。
```

### 例2：全期間人気記事の検索
```
ユーザー: Reactのパフォーマンス最適化について、人気のある日本語記事を読みたい
Claude: 全期間人気順でReactパフォーマンス最適化の記事を検索します。

実行コマンド:
python3 ~/.claude/skills/zenn-search/scripts/search_zenn.py "React パフォーマンス最適化" --order alltime --limit 10

人気の記事トップ10を表示します。
```

### 例3：特定トピックの深掘り
```
ユーザー: TypeScript 5.5の新機能について詳しく知りたい
Claude: TypeScript 5.5の記事を検索し、さらに2ページ目も確認します。

実行コマンド1:
python3 ~/.claude/skills/zenn-search/scripts/search_zenn.py "TypeScript 5.5 新機能"

実行コマンド2（さらに多くの記事が必要な場合）:
python3 ~/.claude/skills/zenn-search/scripts/search_zenn.py "TypeScript 5.5" --page 2
```

## Notes

- **Zenn API利用**: このスキルは `https://zenn.dev/api/search` エンドポイントを使用します
- **日本語コンテンツ**: Zennは日本語の技術記事が中心のプラットフォームです
- **検索のコツ**: 日本語と英語のキーワードを適切に組み合わせると効果的です
- **実践的な情報**: 開発者コミュニティによる投稿のため、実践的な知見が豊富です
- **並び順の選択**:
  - `daily`: 今日話題になっている記事を探す
  - `alltime`: 全期間で人気の記事を探す（殿堂入り記事など）
  - `latest`: 最新の情報を優先する
- **結果の精度**: API直接利用により、いいね数やコメント数などの正確なメタデータが取得できます
