#!/usr/bin/env python3
"""
Zenn記事検索スクリプト
Zenn APIを使用して記事を検索し、結果を表示します。
"""

import argparse
import json
import sys
import urllib.request
import urllib.parse
from typing import Dict, Any


def search_zenn(query: str, order: str = "daily", page: int = 1) -> Dict[str, Any]:
    """
    Zenn APIで記事を検索

    Args:
        query: 検索クエリ
        order: 並び順 (daily, alltime, latest)
        page: ページ番号

    Returns:
        APIレスポンスのJSON
    """
    base_url = "https://zenn.dev/api/search"
    params = {
        "q": query,
        "order": order,
        "source": "articles",
        "page": str(page)
    }

    url = f"{base_url}?{urllib.parse.urlencode(params)}"

    try:
        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read().decode('utf-8'))
            return data
    except urllib.error.HTTPError as e:
        print(f"HTTPエラー: {e.code} - {e.reason}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"URLエラー: {e.reason}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"エラー: {str(e)}", file=sys.stderr)
        sys.exit(1)


def format_article(article: Dict[str, Any], index: int) -> str:
    """
    記事情報を整形

    Args:
        article: 記事データ
        index: 記事番号

    Returns:
        整形された記事情報
    """
    title = article.get('title', '(タイトルなし)')
    emoji = article.get('emoji', '📝')
    path = article.get('path', '')
    url = f"https://zenn.dev{path}" if path else "URL不明"

    # いいね数とコメント数
    liked_count = article.get('liked_count', 0)
    comments_count = article.get('comments_count', 0)

    # 公開日
    published_at = article.get('published_at', '')

    # ユーザー情報
    user = article.get('user', {})
    username = user.get('username', '不明')

    output = f"\n{index}. {emoji} {title}\n"
    output += f"   著者: @{username}\n"
    output += f"   URL: {url}\n"
    output += f"   💚 {liked_count} | 💬 {comments_count}"
    if published_at:
        output += f" | 📅 {published_at[:10]}"

    return output


def main():
    parser = argparse.ArgumentParser(
        description="Zenn記事検索ツール",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  %(prog)s "Next.js"
  %(prog)s "React hooks" --order latest --limit 10
  %(prog)s "TypeScript" --page 2
        """
    )

    parser.add_argument(
        'query',
        help='検索クエリ'
    )
    parser.add_argument(
        '--order',
        choices=['daily', 'alltime', 'latest'],
        default='daily',
        help='並び順 (default: daily)'
    )
    parser.add_argument(
        '--page',
        type=int,
        default=1,
        help='ページ番号 (default: 1)'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=5,
        help='表示件数 (default: 5)'
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='JSON形式で出力'
    )

    args = parser.parse_args()

    # 検索実行
    print(f"🔍 Zennで '{args.query}' を検索中...\n", file=sys.stderr)
    result = search_zenn(args.query, args.order, args.page)

    articles = result.get('articles', [])

    if not articles:
        print("検索結果が見つかりませんでした。", file=sys.stderr)
        sys.exit(0)

    # JSON形式での出力
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    # 通常の整形出力
    articles_count = len(articles)
    next_page = result.get('next_page')

    print(f"検索結果: {articles_count}件を表示 (ページ {args.page})\n")

    # 指定された件数まで表示
    for i, article in enumerate(articles[:args.limit], 1):
        print(format_article(article, i))

    # 次のページがある場合
    if next_page:
        print(f"\n\n💡 ヒント: --page {args.page + 1} で次のページを表示できます")


if __name__ == '__main__':
    main()
