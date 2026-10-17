---
name: pptx-ja
description: Use together with the `pptx` skill (never alone) for PowerPoint (.pptx/.potx) work. DEFAULT-ON — if the user's request is written in Japanese and a .pptx file is involved, always use this skill alongside the `pptx` skill, even when the slide content language is unspecified. Skip only when the user explicitly states the deck is English/non-Japanese or explicitly says not to use this skill. Also trigger on any .pptx work involving Japanese text; on symptoms described as "フォントが崩れる", "文字化け", "スペルチェックが英語になる", "日本語なのに英字フォントになる"; and on requests mentioning "パワポ", "スライド", "プレゼン資料", or a corporate master template (テンプレート).
license: MIT
---

# PPTX 日本語スキル

`pptx`スキル(展開・圧縮の手順、clean/add_slide/thumbnail/validate等の機構、デザインガイド)と**併用**する。`pptx`スキルの記載と矛盾する箇所では本書を優先する。`pptx`スキルは英語コンテンツ前提で書かれており、欧文フォントのみのTypography節に素直に従うと、日本語スライドで問題が起きる。

本書は2026年7月の改訂以降の`pptx`スキルを前提に書いている。`pptx`スキルのフォルダに`editing.md`がある場合は改訂前の版(以下、旧版)なので、本書とあわせて[legacy.md](legacy.md)の読み替えも参照する。

前提: Anthropic公式の`pptx`スキル(単体では使わない)、macOS + PowerPoint for Mac(QAレンダリング)、poppler(`pdftoppm`/`pdffonts`)

## 言語設定 — `lang`属性は実際の言語に合わせる

- 日本語を含むrunは`lang="ja-JP"`(付けるなら`altLang="en-US"`)
- 英数字のみのrunは`lang="en-US"`(`altLang="ja-JP"`)
- **日本語テキストに`lang="en-US"`を付けない**(PowerPointのスペルチェックが英語辞書で走り、赤線だらけになる)。新規段落を作る際はテキストの言語ごとにrunを分け、それぞれ適切な`lang`を付ける
- 既存資料の`lang`を後から直しても**赤波線が消えないことがある**。英語辞書時代の誤り判定が`<a:rPr err="1">`としてファイルに保存され、`dirty="0"`(校正済み)と併存するとPowerPointが再チェックせず古い波線を表示し続けるため。lang修正時は`err`属性も全削除する
- 編集後の機械チェックは「QA」節の**lang混入チェック**を実行する

## フォント — テンプレートに合わせ、無ければ游ゴシック

次の順で決める。「使える」かは作成環境で判定し、PowerPoint同梱フォント(`/Applications/Microsoft PowerPoint.app/Contents/Resources/DFonts`)とシステムフォント(`system_profiler SPFontsDataType`)の両方を見る。

1. **テンプレート・ベース資料がある場合**: テーマ(`ppt/theme/theme*.xml`の`<a:fontScheme>`)の見出し用(`majorFont`)・本文用(`minorFont`)に合わせる。欧文は`<a:latin>`、和文は`<a:ea>`を使い、`<a:ea>`が空欄なら`<a:font script="Jpan">`を使う。それも無ければ2に従う
   - そのフォントが作成環境に無ければ、作業を止めてユーザーに確認する
   - runへの書き方(フォント名の直書きか、`+mn-ea`等のテーマ参照か)は同じ図形・段落の既存runの書き方に合わせる
2. **無い場合**: **游ゴシック**、使えなければ**ＭＳ Ｐゴシック**(全角のＭＳ・Ｐ表記)。書体名は「游ゴシック」で統一し(Light・Mediumは使わない)、欧文(`<a:latin>`)も同じフォントにする

- ＭＳ Ｐゴシックを採用した場合、真の太字は無く合成表示になる。見出しの強調は太字だけに頼らず、サイズ・色も併用する
- Latin限定フォント(Arial, Calibri, Cambria, Times New Roman, Courier New, Bookman Old Style, Century Schoolbook, Georgia, Arial Black, Trebuchet MS, Impact, Palatino, Garamond, Consolas等、`pptx`スキルのTypography節に挙がるもの)は日本語グリフを持たないため、日本語テキストに使わない
- フォントは**`<a:latin>`だけでなく`<a:ea>`(East Asian)も必ずペアで明示**する(テーマ参照でもよい)。`<a:ea typeface=""/>`のような空欄や`<a:ea>`省略のまま`<a:latin>`だけ変更するのは事故の元(和文が未定義のまま残り、環境依存の代替フォントで表示される)
- pptxgenjsで新規作成すると、全runが`lang="en-US"`になり、`<a:ea>`に中国語簡体字の`charset="-122"`が付く。生成後に、和文を含むrunを`lang="ja-JP"`に直し、`<a:latin>`/`<a:ea>`/`<a:cs>`の`pitchFamily`・`charset`属性を削除する。pptxgenjsでは和欧混在の文を1run(`ja-JP`)にしてよい
- `pptx`スキルの「Structured decks」で作る場合、`pres.theme`に渡したフォントはテーマの`<a:latin>`にしか入らない。`<a:ea>`は空欄のまま残り、見出し用(`majorFont`)の`<a:font script="Jpan">`は游ゴシック Lightになる。`applyTheme()`の後に、テーマの`<a:ea>`とJpanを採用した和文フォントに書き換える(runにはフォントを書かず、テーマから継承させる):

```js
const fs = require("fs");
const JSZip = require("jszip"); // pptxgenjsに同梱
const FONT = "游ゴシック";
const zip = await JSZip.loadAsync(fs.readFileSync("deck.pptx"));
for (const p of Object.keys(zip.files).filter(n => /^ppt\/theme\/theme\d+\.xml$/.test(n))) {
  const xml = (await zip.file(p).async("string"))
    .replace(/<a:ea typeface="[^"]*"\/>/g, `<a:ea typeface="${FONT}"/>`)
    .replace(/<a:font script="Jpan" typeface="[^"]*"\/>/g, `<a:font script="Jpan" typeface="${FONT}"/>`);
  zip.file(p, xml);
}
fs.writeFileSync("deck.pptx", await zip.generateAsync({ type: "nodebuffer", compression: "DEFLATE" }));
```
- python-pptxの`run.font.name`は`<a:latin>`しか変更しない。和文を制御するには`<a:ea>`要素を別途明示する(XML直接編集が確実)
- 記号の一部は、PowerPointが`<a:latin>`のフォントで描こうとし、そこに字形がないと代替フォント(ＭＳ ゴシック等)で表示される。書き出したPDFを`pdffonts`で調べ、意図しないフォントがあれば原因の文字を特定し(PyMuPDFの`get_text("dict")`でspanごとのフォントが分かる)、その文字だけ別runにして`<a:latin>`も採用した和文フォントにする。空のセルや文字のない図形も`<a:endParaRPr>`にフォントを明示する。箇条書きの記号も`<a:buFont>`のフォントで描かれるため、意図しないフォントの原因になる

## フォントサイズ — 本文は原則16pt、階段を守る

- **本文は原則16pt。文章量が多い時のみ14ptを許容**。12ptは注釈・出典・図中ラベルなど「細かくても問題ないもの」専用の下限
- **すべてのテキストは12pt以上**(本文・キャプション・出典・図中ラベル・ページ番号含む)。`pptx`スキルのTypography節の「Captions 10-12pt」と、Avoid節の下限(captions 10pt)はこのルールで上書きする
- 例外: テンプレートのプレースホルダー・部品が定めるサイズや、既存資料の確立済み部品(タグ・バッジ等)を複製・踏襲して追加する場合は、資料内の統一を優先して既存サイズのままとする(この節の「サイズの階段」の表や「箇条書きのレベル別サイズ」にも合わせ直さない。新規デザインには適用しない)
- サイズの階段(用途と差を明確に保つ):

| サイズ | 用途 |
|---|---|
| 12pt | 下限。注釈・出典・図中ラベル・ページ番号など、細かくても問題ないもの専用 |
| 14pt | 文章量が多い場合に限り許容する本文 |
| 16pt | 原則の本文・リード文 |
| 18pt | 小見出し |
| 20pt〜 | 見出し・統計数字などの強調 |

- 箇条書きのレベル別サイズ(必須): 第1〜5レベル = 24/22/20/18/14pt
- OOXMLでは`sz="1200"`が12pt。編集後に「QA」節の`check.py`で、スライドの`sz`の最小値が1200以上であることを確認する
- 収まらない場合はフォントを小さくするのではなく、**まずテキストを刈り込む(文章をフレーズ化して密度を下げる)か、枠を広げる**。密度の高い解説パネルでどうしても収まらない場合のみ、行間(`<a:lnSpc><a:spcPct>`)を締める(90%程度まで)。12pt未満への縮小は不可。既存資料を作り直す場合など、文章を刈り込めずにページを分ける必要があり、元資料より枚数が大きく増える見込みのときは、着手前にユーザーに確認する

## 改行位置 — 単語の途中で行を割らない

PowerPointは日本語を文字単位(禁則のみ)で折り返すため、単語・固有名詞の途中で表示上の改行が入ることがある。`pptx`スキルのVisual QAにも単語割れの確認があるが、日本語では次のように対象と直し方を絞る。

- 対象は**概ね3行以内に収まる短文**(見出し・リード文・図中/オブジェクト内の短文説明・表のセル。表は見出し行だけでなく本文セルも含む)のみ。長い本文の自然折返しは調整しない
- レンダリング確認で**実際に単語の途中で割れている行に限り**、文節の切れ目に明示改行(`<a:br/>`)を入れる。割れていない行に予防的に入れない(目安: 1テキスト2箇所程度)

## 文体 — 顧客向けの資料は書き言葉で書く

スライドの文言を書く・書き換えるときは、話し言葉を避けてビジネス文書の書き言葉にする。既存資料やユーザーが文体を指定している場合はそちらに合わせる。特に次の型が混じりやすい。

- 口語の動詞：直す→修正する、確かめる→確認する
- 口語の接続・助詞：〜たら／〜れば→〜した場合は、〜だけ→〜のみ、〜けど→〜が
- 社内の言い回し：詰める、〜感、ざっくり→具体化する、想定〜、概算
- 書き手の都合で頼む言い方：〜いただけると助かります→〜いただけますでしょうか

## 使う文字 — CP932で表せる文字に限る

スライドに書く文字は、ユーザーから明示的な指示がある場合を除き、CP932(WindowsのShift_JIS)の文字集合に含まれるものだけを使う。髙など、範囲内の漢字は使ってよい。①・㈱のような記号は範囲内でも積極的には使わない。絵文字(✅ 🚀等)、JIS第3・第4水準の漢字(𠮷等)、簡体字などは使わず、範囲内の文字や言い換えで表す。これは使う文字の制限であり、ファイルの文字コードの指定ではない(pptx内のXMLはUTF-8のまま扱う)。編集後は「QA」節の**範囲外文字チェック**を実行する。

## テンプレート — 指定されたら、テンプレートの部品とページ構成で組む

ここでいうテンプレートは、ユーザーが「テンプレート」「マスター」「この書式で作って」などと、書式の土台として明示したファイルに限る。`.potx`ファイルが指定された場合は、明示が無くてもテンプレートとみなす。「参考に」「こんな感じで」と渡された資料は雰囲気や構成の参考にとどめ、本節の優先順・ページ構成の踏襲・自作の制限は適用しない。判断がつかなければユーザーに確認する。

テンプレートが指定された場合は、**pptxgenjsでゼロから作らず**、`pptx`スキルの「Editing existing decks and templates」節の手順(`add_slide.py`での複製・レイアウトからの追加)で組む。デザインはテンプレートを最優先し、`pptx`スキルのデザインガイド(配色・レイアウト案)は使わない。テンプレートの所在はユーザーの指定に従い、不明な場合は決め打ちせずユーザーに確認する。案件の作業フォルダにコピーしてから編集し、マスター自体には触らない。

- `.potx`を土台にする場合は、次を守る
  - 展開は`.potx`のままでよい。`thumbnail.py`は`.potx`を受け付けないため、拡張子を`.pptx`にしたコピーで実行する。markitdownで読むときは、拡張子だけでなく`[Content_Types].xml`も下記のとおりpresentationに書き換えたコピーを使う(拡張子だけ変えたものは読めない)
  - 資料として書き出すときは拡張子を`.pptx`にし、`[Content_Types].xml`の`presentationml.template.main+xml`を`presentationml.presentation.main+xml`に書き換える。書き換えないとPowerPointで開けない。この不備は`validate.py`では検出されない
  - `pptx`スキルの「出力も`.potx`拡張子のままにする」は、テンプレート自体を修正する場合に限って従う
- **着手前に棚卸しする**: テンプレートに設計書(Design.md等)やテンプレート内のガイドラインのページがあれば先に読む。サンプルスライドと部品集は`thumbnail.py`とmarkitdownで、レイアウトは`ppt/slideLayouts/*.xml`のレイアウト名(`<p:cSld name>`)とプレースホルダーで、配色はテーマの`<a:clrScheme>`で把握する
- **ページ構成を踏襲する**: テンプレートが示す構成(表紙→目次→中扉→本文→裏表紙など)の順序と各ページの役割に沿って組み、それぞれ対応するスライド・レイアウトを使う
- **各スライドは次の優先順で作る**:
  1. 内容に合うサンプルスライド・部品集のスライドを複製する(`add_slide.py slideN.xml`)
  2. 合うものが無ければ、テンプレートのレイアウトから作る(`add_slide.py slideLayoutN.xml`)
  3. それでも足りない部分だけ自作する。その場合もテンプレートにある部品(枠・矢印・表・アイコン等)をコピーして流用し、色はテーマ色(`<a:schemeClr>`)、フォントはテーマ参照にする。`<a:srgbClr>`の直書きや、テンプレートに無い装飾は足さない
- **プレースホルダーを使う**: タイトル・本文・ページ番号などはレイアウトのプレースホルダーに入れ、同じ位置にテキストボックスを重ねない。位置・サイズ・箇条書きの書式は直書きせず、レイアウトから継承させる
- `pptx`スキルの「vary the layouts」(Editing existing decks and templates節)とAvoid節の「Don't repeat the same layout」は、テンプレート内のレイアウトを使い分けることで満たす。変化をつけるためにテンプレート外のデザインを持ち込まない
- テンプレートに部品集(コンポーネント集)ページ群がある場合、**部品集のスライドを複製して実コンテンツに使うときは、標準のコンテンツ用レイアウトに載せ替える**こと。部品集専用レイアウトのまま使うと見出し様式やページ番号プレースホルダーがズレる
- 使わなかったサンプルスライド・部品集のページは削除する(`<p:sldIdLst>`から外して`clean.py`)
- 構成上のページ(目次・中扉等)を省いた場合や、3で自作した箇所がある場合は、最終報告で「どのスライドの・何を・なぜ」を伝える

## 既存ファイルへの追記時の運用

- ユーザーが既にPowerPointで手動修正している場合は**その現行ファイルをそのまま母体にして**作業する(ゼロから再生成しない)
- ファイルを直接上書きする前に、`backup/`配下にタイムスタンプ付きでコピーを控える
- 波ダッシュ(〜 U+301C)と全角チルダ(～ U+FF5E)など見分けにくい文字は、既存資料内の文字をプログラムで抽出して再利用し、これらを含む文字列を置換のアンカーにしない
- 別の顧客向けの資料を母体にするときは、スライド本文のほかに`docProps/app.xml`(旧スライドの題名)・`docProps/thumbnail.jpeg`(旧表紙の縮小画像)・`ppt/commentAuthors.xml`(コメント作成者の個人名・ID)にも前の案件の情報が残るため、差し替えるか削除する
- `add_slide.py`で追加したスライドにはノート(notesSlide)が付かない。スピーカーノートを足すときは、`ppt/notesSlides/notesSlideN.xml`とその`_rels`(notesMasterと対象スライドを指す)を作り、`ppt/slides/_rels/slideN.xml.rels`から参照して、`[Content_Types].xml`に登録する

## QA

### レンダリング — `pptx`スキルのLibreOffice手順を置き換え、実PowerPointで行う(Mac)

`pptx`スキル標準のLibreOffice(`soffice.py`)レンダリングは**日本語資料のQAには使わない**。游ゴシック・ＭＳ Ｐゴシック等のOffice付属フォントはLibreOfficeから参照できず代替フォントで描画されるため、折返し・重なりの誤検知/見逃しが起きる(実際に「LibreOfficeでは重なって見えるが実PowerPointでは正常」という誤検知の実績あり)。代わりに本スキルの`scripts/render.sh`で、AppleScriptを使ってPowerPoint本体からPDFを書き出し、スライドごとの画像にする:

```bash
<本スキルのフォルダ>/scripts/render.sh 対象.pptx [出力先(既定: qa)]   # → qa/render.pdf と qa/slide-NN.jpg
```

- 初回実行時にmacOSのオートメーション許可ダイアログが出ることがある
- スクリプトを書き換えるときは次を崩さない。**PDFで書き出す**(`save as PNG`は無音で失敗する)。**対象は`full name`で特定し、`active presentation`で取らない**(コンテナ外のpptxは開けないことがあり、エラーも出ない。そのとき前面にあるユーザーの別資料を保存せずに閉じてしまう。実際に起きた)
- `pdffonts qa/render.pdf` で採用したフォント(PDF上は英語名。例: MS-PGothic)だけが埋め込まれているか確認すると、フォント指定漏れを機械的に検出できる。テンプレートの部品が意図して使っている記号フォント(箇条書きの行頭文字のWingdings等)は除く

### チェック項目(`pptx`スキルのQA項目に追加)

- **ファイル検証**: `pptx`スキルの`scripts/office/validate.py`を実行し、すべて通ること(テンプレート・ベース資料から作った場合は`--original 元ファイル`を付ける)。ただし`.potx`由来のContent-Typeの不備、`lang`の誤り、フォント指定の漏れは検出されないため、以下のチェックも省かない

- **機械チェック**: 本スキルの`scripts/check.py`で次をまとめて検査する。pptxファイルと展開済みフォルダのどちらも渡せる。NGが1件でもあれば終了コード1になる

```bash
python3 <本スキルのフォルダ>/scripts/check.py 出力.pptx [--source 元資料.pptx] [--replace "旧=新"] [--allow "①"]
```

  - **lang混入チェック**: `lang="en-US"`指定のrunに英数字以外の文字(和文・全角記号・「〜」など)が混じっていないか、runとテキストを対にして検査する
  - **範囲外文字チェック**: スライドのテキストに、CP932で表せない文字が無いか検査する。ユーザーが使用を指示した文字は`--allow`で除く
  - **最小サイズ**: スライドの`sz`の最小値が1200(12pt)以上か
  - **ダミー文言**: `pptx`スキルのプレースホルダー残存チェックの文言に、日本語のダミー文言(「タイトル」「サンプル」「YYYY/MM/DD」「親譲りの無鉄砲」など)を加えて検査する
  - **内容の突き合わせ**(既存資料を作り直す場合、`--source`を付ける): 元資料と新資料の段落のテキストと表の行(セルの並び)を突き合わせ、欠けや改変が無いことを確認する。一致しないものは、意図した変更かどうかを1件ずつ確かめる。範囲外文字の置き換えなど、意図して一括で変えた文字は`--replace "旧=新"`で元資料側を置き換えてから比べる
- **テンプレート準拠チェック**(テンプレート使用時): レンダリング画像をテンプレートのサンプルスライドと見比べ、見出し・ページ番号・ロゴの位置や配色がずれていないか確認する
- **単語割れチェック**(`pptx`スキルのVisual QAの同項目を、本書の「改行位置」節に沿って行う): レンダリング画像で、「改行位置」節の対象(短文)が単語の途中で折り返されていないか確認する。明示改行で修正した場合は、自然折返しとの二段重ねで新たな崩れが出ていないか**必ず再レンダリングして確認**する
- 最終確認として、ユーザーにも実機PowerPointでの目視確認を依頼してから完了とする。游ゴシックはOffice側の仕様変更やフォントのバージョン差で表示が崩れた実績があるため、採用時は特に念入りに確認してもらう
