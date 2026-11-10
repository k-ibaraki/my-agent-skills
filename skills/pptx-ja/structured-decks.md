# Structured decksのテーマを和文フォントに揃えるスクリプト

[SKILL.md](SKILL.md)の「フォント」節から参照する。`pptx`スキルの「Structured decks」で作った資料は、`applyTheme()`の後にこのスクリプトでテーマの`<a:ea>`とJpanを書き換える(runにはフォントを書かず、テーマから継承させる)。

```js
// async 関数の中で実行する(await を使うため)
const fs = require("fs");
const path = require("path");
// jszip は pptxgenjs の依存として入っている。pptxgenjs が共有の場所に入っている環境(Claude のクラウド環境等)でも動くよう、pptxgenjs 経由で探す
const JSZip = require(require.resolve("jszip", { paths: [path.dirname(require.resolve("pptxgenjs"))] }));
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
