# 旧版`pptx`スキルでの読み替え

`pptx`スキルのフォルダに`editing.md`・`pptxgenjs.md`・`scripts/office/unpack.py`・`pack.py`がある版(2026年7月の改訂より前。以下、旧版)を使う場合に、[SKILL.md](SKILL.md)とあわせて読む。左列の箇所は、右列のとおり読み替える。

| SKILL.mdの箇所 | 旧版での読み替え |
|---|---|
| 冒頭(`pptx`スキルの問題点) | 旧版では、欧文フォントのみのタイポグラフィ表に加え、`lang="en-US"`を直書きした`editing.md`のXML例にも素直に従わない |
| 言語設定「日本語テキストに`lang="en-US"`を付けない」 | `pptx`スキルの`editing.md`のXML例をそのまま真似て、日本語テキストに`lang="en-US"`を付けない |
| フォント「Typography節に挙がるもの」 | 旧版ではタイポグラフィ表に挙がるもの |
| フォント「Structured decks」の手順 | 旧版にはStructured decksが無いため不要。pptxgenjsの使い方は`pptxgenjs.md`を参照する |
| フォントサイズ「Typography節のCaptions 10-12ptとAvoid節の下限」 | 旧版ではタイポグラフィ表の「Captions 10-12pt」をこのルールで上書きする(Avoid節の下限の記載は無い) |
| テンプレート「Editing existing decks and templates節の手順」 | `pptx`スキルの`editing.md`の手順(複製・レイアウトからの追加)で組む。展開は`unpack.py`、圧縮は`pack.py`で行う |
| `.potx`「展開は`.potx`のままでよい」 | 拡張子を`.pptx`にしたコピーを展開する。`unpack.py`は`.potx`を受け付けない |
| `.potx`「Content-Typeの不備は`validate.py`では検出されない」 | この不備は`pack.py`の検証では検出されない |
| `.potx`「出力も`.potx`拡張子のままにする」 | 旧版にこの記載は無い。資料は`.pptx`で書き出す |
| テンプレート「vary the layouts」 | `editing.md`の「USE VARIED LAYOUTS」は、テンプレート内のレイアウトを使い分けることで満たす |
| QA「ファイル検証」(`validate.py`) | `pack.py unpacked/ output.pptx --original 元ファイル`の検証で代える。検出されないものは新版と同じ |
| QA「単語割れチェック」 | 旧版のVisual QAには単語割れの項目が無い。本書のチェックだけで行う |
