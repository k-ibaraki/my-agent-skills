---
name: ddg-search
description: DuckDuckGo APIを使ってWeb検索を実行します。情報を調べたい、最新の技術情報を検索したい、特定のトピックについて調査したい場合に使用します。
license: MIT
---

# DuckDuckGo検索

DuckDuckGo Instant Answer API（APIキー不要）で検索する。

```bash
Q="検索キーワード"
curl -s "https://api.duckduckgo.com/?q=$Q&format=json" | jq -r '.AbstractText, .AbstractURL'
curl -s "https://api.duckduckgo.com/?q=$Q&format=json" | jq -r '.RelatedTopics[] | select(.Text) | "\(.Text)\n\(.FirstURL)\n"'
```

- `AbstractText` / `AbstractURL`: トピックの概要（Wikipedia等）とその出典
- `RelatedTopics`: 関連情報とURL

## 注意事項

- **Instant Answer APIは百科事典型クエリ（用語・人物・概念）向け**で、技術記事の調査など一般的なWeb検索はほぼ空振りする。結果が空ならWebSearchツールにフォールバックする
- 検索クエリは英語の方が結果が充実している場合がある
- 結果の整形には jq が必要
