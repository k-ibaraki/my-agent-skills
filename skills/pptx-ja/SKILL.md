---
name: pptx-ja
description: Use together with the `pptx` skill (never alone) for PowerPoint (.pptx) work. DEFAULT-ON — if the user's request is written in Japanese and a .pptx file is involved, always use this skill alongside the `pptx` skill, even when the slide content language is unspecified. Skip only when the user explicitly states the deck is English/non-Japanese or explicitly says not to use this skill. Also trigger on any .pptx work involving Japanese text; on symptoms described as "フォントが崩れる", "文字化け", "スペルチェックが英語になる", "日本語なのに英字フォントになる"; and on requests mentioning "パワポ", "スライド", "プレゼン資料", or a corporate master template (テンプレート).
license: MIT
---

# PPTX 日本語スキル

`pptx`スキル(unpack/pack/clean/add_slide/thumbnail等の機構、デザインガイド)と**併用**する。`pptx`スキルの記載と矛盾する箇所では本書を優先する。`pptx`スキルは英語コンテンツ前提で書かれており、欧文フォントのみのタイポグラフィ表や、`lang="en-US"`を直書きした`editing.md`のXML例に素直に従うと、日本語スライドで問題が起きる。

前提: Anthropic公式の`pptx`スキル(単体では使わない)、macOS + PowerPoint for Mac(QAレンダリング)、poppler(`pdftoppm`/`pdffonts`)

## 言語設定 — `lang`属性は実際の言語に合わせる

- 日本語を含むrunは`lang="ja-JP"`(付けるなら`altLang="en-US"`)
- 英数字のみのrunは`lang="en-US"`(`altLang="ja-JP"`)
- **`pptx`スキルのXML例をそのまま真似て日本語テキストに`lang="en-US"`を付けない**(PowerPointのスペルチェックが英語辞書で走り、赤線だらけになる)。新規段落を作る際はテキストの言語ごとにrunを分け、それぞれ適切な`lang`を付ける
- 既存資料の`lang`を後から直しても**赤波線が消えないことがある**。英語辞書時代の誤り判定が`<a:rPr err="1">`としてファイルに保存され、`dirty="0"`(校正済み)と併存するとPowerPointが再チェックせず古い波線を表示し続けるため。lang修正時は`err`属性も全削除する
- 編集後の機械チェックは「QA」節の**lang混入チェック**を実行する

## フォント — テンプレートに合わせ、無ければ游ゴシック

次の順で決める。「使える」かは作成環境で判定し、PowerPoint同梱フォント(`/Applications/Microsoft PowerPoint.app/Contents/Resources/DFonts`)とシステムフォント(`system_profiler SPFontsDataType`)の両方を見る。

1. **テンプレート・ベース資料がある場合**: テーマ(`ppt/theme/theme*.xml`の`<a:fontScheme>`)の見出し用(`majorFont`)・本文用(`minorFont`)に合わせる。欧文は`<a:latin>`、和文は`<a:ea>`を使い、`<a:ea>`が空欄なら`<a:font script="Jpan">`を使う。それも無ければ2に従う
   - そのフォントが作成環境に無ければ、作業を止めてユーザーに確認する
   - runへの書き方(フォント名の直書きか、`+mn-ea`等のテーマ参照か)は同じ図形・段落の既存runの書き方に合わせる
2. **無い場合**: **游ゴシック**、使えなければ**ＭＳ Ｐゴシック**(全角のＭＳ・Ｐ表記)。書体名は「游ゴシック」で統一し(Light・Mediumは使わない)、欧文(`<a:latin>`)も同じフォントにする

- ＭＳ Ｐゴシックを採用した場合、真の太字は無く合成表示になる。見出しの強調は太字だけに頼らず、サイズ・色も併用する
- Latin限定フォント(Georgia, Calibri, Arial Black, Cambria, Trebuchet MS, Impact, Palatino, Garamond, Consolas等、`pptx`スキルのタイポグラフィ表にあるもの)は日本語グリフを持たないため、日本語テキストに使わない
- フォントは**`<a:latin>`だけでなく`<a:ea>`(East Asian)も必ずペアで明示**する(テーマ参照でもよい)。`<a:ea typeface=""/>`のような空欄や`<a:ea>`省略のまま`<a:latin>`だけ変更するのは事故の元(和文が未定義のまま残り、環境依存の代替フォントで表示される)
- pptxgenjsで新規作成すると、全runが`lang="en-US"`になり、`<a:ea>`に中国語簡体字の`charset="-122"`が付く。生成後に、和文を含むrunを`lang="ja-JP"`に直し、`<a:latin>`/`<a:ea>`/`<a:cs>`の`pitchFamily`・`charset`属性を削除する。pptxgenjsでは和欧混在の文を1run(`ja-JP`)にしてよい
- python-pptxの`run.font.name`は`<a:latin>`しか変更しない。和文を制御するには`<a:ea>`要素を別途明示する(XML直接編集が確実)
- 記号の一部は、PowerPointが`<a:latin>`のフォントで描こうとし、そこに字形がないと代替フォント(ＭＳ ゴシック等)で表示される。書き出したPDFを`pdffonts`で調べ、意図しないフォントがあれば原因の文字を特定し(PyMuPDFの`get_text("dict")`でspanごとのフォントが分かる)、その文字だけ別runにして`<a:latin>`も採用した和文フォントにする。空のセルや文字のない図形も`<a:endParaRPr>`にフォントを明示する

## フォントサイズ — 本文は原則16pt、階段を守る

- **本文は原則16pt。文章量が多い時のみ14ptを許容**。12ptは注釈・出典・図中ラベルなど「細かくても問題ないもの」専用の下限
- **すべてのテキストは12pt以上**(本文・キャプション・出典・図中ラベル・ページ番号含む)。`pptx`スキルの「Captions 10-12pt」はこのルールで上書きする
- 例外: 既存資料の確立済み部品(タグ・バッジ等)を複製・踏襲して追加する場合は、資料内の統一を優先して既存サイズのままとする(新規デザインには適用しない)
- サイズの階段(用途と差を明確に保つ):

| サイズ | 用途 |
|---|---|
| 12pt | 下限。注釈・出典・図中ラベル・ページ番号など、細かくても問題ないもの専用 |
| 14pt | 文章量が多い場合に限り許容する本文 |
| 16pt | 原則の本文・リード文 |
| 18pt | 小見出し |
| 20pt〜 | 見出し・統計数字などの強調 |

- 箇条書きのレベル別サイズ(必須): 第1〜5レベル = 24/22/20/18/14pt
- OOXMLでは`sz="1200"`が12pt。編集後に `grep -ohE 'sz="[0-9]+"' ppt/slides/*.xml | grep -oE '[0-9]+' | sort -n | head -1` の結果(最小値)が1200以上であることを確認する
- 収まらない場合はフォントを小さくするのではなく、**まずテキストを刈り込む(文章をフレーズ化して密度を下げる)か、枠を広げる**。密度の高い解説パネルでどうしても収まらない場合のみ、行間(`<a:lnSpc><a:spcPct>`)を締める(90%程度まで)。12pt未満への縮小は不可

## 改行位置 — 単語の途中で行を割らない

PowerPointは日本語を文字単位(禁則のみ)で折り返すため、単語・固有名詞の途中で表示上の改行が入ることがある。

- 対象は**概ね3行以内に収まる短文**(見出し・リード文・図中/オブジェクト内の短文説明)のみ。長い本文の自然折返しは調整しない
- レンダリング確認で**実際に単語の途中で割れている行に限り**、文節の切れ目に明示改行(`<a:br/>`)を入れる。割れていない行に予防的に入れない(目安: 1テキスト2箇所程度)

## テンプレート

マスターテンプレートから新規資料を作る場合は、案件の作業フォルダにテンプレートをコピーしてから編集し、マスター自体には触らない。テンプレートの所在はユーザーの指定に従い、不明な場合は決め打ちせずユーザーに確認する。

- テンプレートに部品集(コンポーネント集)ページ群がある場合、**部品集のスライドを複製して実コンテンツに使うときは、標準のコンテンツ用レイアウトに載せ替える**こと。部品集専用レイアウトのまま使うと見出し様式やページ番号プレースホルダーがズレる

## 既存ファイルへの追記時の運用

- ユーザーが既にPowerPointで手動修正している場合は**その現行ファイルをそのまま母体にして**作業する(ゼロから再生成しない)
- ファイルを直接上書きする前に、`backup/`配下にタイムスタンプ付きでコピーを控える
- 波ダッシュ(〜 U+301C)と全角チルダ(～ U+FF5E)など見分けにくい文字は、既存資料内の文字をプログラムで抽出して再利用し、これらを含む文字列を置換のアンカーにしない
- 別の顧客向けの資料を母体にするときは、スライド本文のほかに`docProps/app.xml`(旧スライドの題名)・`docProps/thumbnail.jpeg`(旧表紙の縮小画像)・`ppt/commentAuthors.xml`(コメント作成者の個人名・ID)にも前の案件の情報が残るため、差し替えるか削除する

## QA

### レンダリング — `pptx`スキルのLibreOffice手順を置き換え、実PowerPointで行う(Mac)

`pptx`スキル標準のLibreOffice(`soffice.py`)レンダリングは**日本語資料のQAには使わない**。游ゴシック・ＭＳ Ｐゴシック等のOffice付属フォントはLibreOfficeから参照できず代替フォントで描画されるため、折返し・重なりの誤検知/見逃しが起きる(実際に「LibreOfficeでは重なって見えるが実PowerPointでは正常」という誤検知の実績あり)。代わりにAppleScriptでPowerPoint本体からPDFを書き出す:

```bash
# PowerPointはサンドボックス化されているため、対象pptxも出力先もPowerPointのコンテナ内に置く
DIR=~/Library/Containers/com.microsoft.Powerpoint/Data/tmp_render
mkdir -p "$DIR" qa && rm -f "$DIR/render.pdf" && cp /absolute/path/to/target.pptx "$DIR/deck.pptx"
osascript - "$DIR/deck.pptx" "$DIR/render.pdf" <<'EOF'
on run argv
	set target to item 1 of argv
	set outPath to POSIX file (item 2 of argv)
	tell application "Microsoft PowerPoint"
		launch
		open (POSIX file target)
		delay 3
		set found to missing value
		repeat with i from 1 to (count of presentations)
			if (full name of presentation i) is target then set found to presentation i
		end repeat
		if found is missing value then error "対象を開けなかった(他の資料には触れない)"
		save found in outPath as save as PDF
		close found saving no
	end tell
end run
EOF
cp "$DIR/render.pdf" qa/ && pdftoppm -jpeg -r 100 qa/render.pdf qa/slide
```

- `save as PNG`は無音で失敗するので**PDF一択**
- **`active presentation`で対象を取らない**。コンテナ外のpptxは開けないことがあり(エラーも出ない)、そのとき前面にあるユーザーの別資料を保存せずに閉じてしまう(実際に起きた)。開いたプレゼンは必ず`full name`で特定し、見つからなければ止める
- 初回実行時にmacOSのオートメーション許可ダイアログが出ることがある
- `pdffonts render.pdf` で採用したフォント(PDF上は英語名。例: MS-PGothic)だけが埋め込まれているか確認すると、フォント指定漏れを機械的に検出できる

### チェック項目(`pptx`スキルのQA項目に追加)

- プレースホルダー残存チェックに日本語のダミー文言も含める: `grep -iE "xxxx|lorem|ipsum|^タイトル$|サンプル|YYYY.*MM.*DD|親譲りの無鉄砲"`
- **lang混入チェック**: `lang="en-US"`指定のrunに英数字以外の文字(和文・全角記号・「〜」など)が混じっていないか、runとテキストを対にして検査する:

```bash
python3 -c "
import re, glob
ng = 0
for f in glob.glob('ppt/slides/slide*.xml'):
    for m in re.finditer(r'<a:r>(.*?)</a:r>', open(f, encoding='utf-8').read(), re.S):
        lang = re.search(r'lang=\"([\w-]+)\"', m.group(1))
        text = re.search(r'<a:t[^>]*>(.*?)</a:t>', m.group(1), re.S)
        if lang and text and lang.group(1) == 'en-US' and re.search(r'[^\x00-\x7F]', text.group(1)):
            print(f, repr(text.group(1)[:30])); ng += 1
print('NG:', ng, '件(0であること)')
"
```
- **単語割れチェック**: レンダリング画像で、「改行位置」節の対象(短文)が単語の途中で折り返されていないか確認する。明示改行で修正した場合は、自然折返しとの二段重ねで新たな崩れが出ていないか**必ず再レンダリングして確認**する
- 最終確認として、ユーザーにも実機PowerPointでの目視確認を依頼してから完了とする。游ゴシックはOffice側の仕様変更やフォントのバージョン差で表示が崩れた実績があるため、採用時は特に念入りに確認してもらう
