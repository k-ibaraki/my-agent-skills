#!/usr/bin/env python3
"""pptx-ja の機械チェックをまとめて行う。

使い方:
  python3 check.py deck.pptx                      # 展開済みフォルダも指定できる
  python3 check.py deck.pptx --source 元資料.pptx  # 既存資料を作り直した場合の突き合わせも行う
  python3 check.py deck.pptx --allow ①㈱          # ユーザーが使用を指示した文字は範囲外文字チェックから除く
  python3 check.py deck.pptx --source 元資料.pptx --replace "–=－"  # 意図して置き換えた文字は、元資料側を置き換えてから比べる

検査項目（NG が1件でもあれば終了コード 1）:
  lang 混入     lang="en-US" の run に英数字以外の文字が混じっていないか
  範囲外文字    CP932 で表せない文字が無いか
  最小サイズ    スライドの sz の最小値が 1200（12pt）以上か
  ダミー文言    テンプレートのダミー文言・プレースホルダーの文言が残っていないか
  突き合わせ    --source を付けた場合、元資料の段落・表の行が新資料に揃っているか
"""
import argparse
import html
import re
import sys
import zipfile
from pathlib import Path

DUMMY = re.compile(r"\bx{3,}\b|lorem|ipsum|\bTODO|\[insert|this.*(page|slide).*layout"
                   r"|^タイトル$|サンプル|YYYY.*MM.*DD|親譲りの無鉄砲", re.I)


def slides(path):
    """(名前, XML) をスライド番号順に返す。pptx/potx ファイルと展開済みフォルダの両方を受け付ける。"""
    p = Path(path)
    if p.is_dir():
        items = [(f.name, f.read_text(encoding="utf-8")) for f in (p / "ppt/slides").glob("slide*.xml")]
    else:
        z = zipfile.ZipFile(p)
        items = [(n.split("/")[-1], z.read(n).decode("utf-8")) for n in z.namelist()
                 if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)]
    return sorted(items, key=lambda t: int(re.search(r"\d+", t[0]).group()))


def text_of(xml):
    return html.unescape("".join(re.findall(r"<a:t(?:\s[^>]*)?>([^<]*)</a:t>", xml)))


def paragraphs(items):
    return [t for _, x in items for p in re.findall(r"<a:p>.*?</a:p>", x, re.S) if (t := text_of(p)).strip()]


def table_rows(items):
    rows = []
    for _, x in items:
        for tr in re.findall(r"<a:tr\b.*?</a:tr>", x, re.S):
            cells = [re.sub(r"\s+", "", text_of(tc)) for tc in re.findall(r"<a:tc\b[^>]*>.*?</a:tc>", tr, re.S)
                     if 'hMerge="1"' not in tc[:30] and 'vMerge="1"' not in tc[:30]]
            rows.append(tuple(cells))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("deck")
    ap.add_argument("--source")
    ap.add_argument("--allow", default="")
    ap.add_argument("--replace", action="append", default=[], help="旧=新。突き合わせの前に元資料側の文字列を置き換える")
    a = ap.parse_args()
    items = slides(a.deck)
    ng = 0

    def report(title, found):
        nonlocal ng
        print(f"[{'OK' if not found else 'NG'}] {title}: {len(found)}件")
        uniq = {}
        for f in found:  # 同じ指摘はまとめて件数で出す
            uniq[f] = uniq.get(f, 0) + 1
        for f, n in list(uniq.items())[:30]:
            print("   ", f, f"（×{n}）" if n > 1 else "")
        if len(uniq) > 30:
            print(f"    ほか{len(uniq) - 30}種類")
        ng += len(found)

    lang = []
    for name, x in items:
        for r in re.findall(r"<a:r>(.*?)</a:r>", x, re.S):
            m = re.search(r'lang="([\w-]+)"', r)
            t = text_of(r)
            if m and m.group(1) == "en-US" and re.search(r"[^\x00-\x7F]", t):
                lang.append(f"{name} {t[:30]!r}")
    report("lang 混入", lang)

    bad = []
    for name, x in items:
        for t in re.findall(r"<a:t(?:\s[^>]*)?>([^<]*)</a:t>", x):
            t = html.unescape(t)
            out = []
            for c in t:
                if c in a.allow:
                    continue
                try:
                    c.encode("cp932")
                except UnicodeEncodeError:
                    out.append(c)
            if out:
                bad.append(f"{name} {t[:30]!r} {out}")
    report("範囲外文字", bad)

    small = []
    for name, x in items:
        for v in re.findall(r'\ssz="(\d+)"', x):
            if int(v) < 1200:
                small.append(f"{name} sz={v}")
    report("最小サイズ（12pt 未満）", small)

    dummy = [f"{name} {p[:40]!r}" for name, x in items
             for p in (text_of(q) for q in re.findall(r"<a:p>.*?</a:p>", x, re.S)) if p.strip() and DUMMY.search(p)]
    report("ダミー文言", dummy)

    if a.source:
        src = slides(a.source)
        for rule in a.replace:
            old, new = rule.split("=", 1)
            src = [(n, x.replace(old, new)) for n, x in src]
        norm = lambda s: re.sub(r"\s+", "", s)
        blob = norm("".join(paragraphs(items)))
        miss = [p[:60] for p in paragraphs(src) if norm(p) not in blob and not re.fullmatch(r"\d+", p.strip())]
        report("突き合わせ：元資料にあって新資料に無い段落（意図した変更か1件ずつ確かめる）", miss)
        have = set(table_rows(items))
        rmiss = [str(r) for r in table_rows(src) if r not in have]
        report("突き合わせ：元資料にあって新資料に無い表の行", rmiss)

    print("NG 合計:", ng)
    sys.exit(1 if ng else 0)


main()
