---
name: ddg-search
description: DuckDuckGo APIを使ってWeb検索を実行します。情報を調べたい、最新の技術情報を検索したい、特定のトピックについて調査したい場合に使用します。
license: MIT
---

# DuckDuckGo検索

## Instructions

1. ユーザーから検索キーワードを取得
2. DuckDuckGo Instant Answer APIを使用して検索を実行：
   ```bash
   curl -s "https://api.duckduckgo.com/?q=検索キーワード&format=json"
   ```
3. 結果を解析して以下の情報を提供：
   - **要約** (`AbstractText`): トピックの概要（Wikipediaなどから）
   - **ソースURL** (`AbstractURL`): より詳しい情報へのリンク
   - **関連トピック** (`RelatedTopics`): 関連する情報とURL

## 出力フォーマット

結果は以下のように整形して表示：

```bash
# 要約を表示
curl -s "https://api.duckduckgo.com/?q=検索キーワード&format=json" | jq -r '.AbstractText'

# 関連トピックを表示（jqが利用可能な場合）
curl -s "https://api.duckduckgo.com/?q=検索キーワード&format=json" | jq -r '.RelatedTopics[] | select(.Text) | "\(.Text)\n\(.FirstURL)\n"'
```

## 使用例

- `/ddg-search Python programming` - Pythonプログラミングについて検索
- `/ddg-search React hooks` - React hooksについて調査
- `/ddg-search curl tutorial` - curlのチュートリアルを探す

## 注意事項

- APIキー不要で使用可能
- インターネット接続が必要
- 検索クエリは英語の方が結果が充実している場合があります
- jqコマンドがインストールされていると結果の整形が便利
