#!/bin/bash
# 実 PowerPoint（Mac）で pptx を PDF に書き出し、スライドごとの画像にする。
# 使い方: render.sh 対象.pptx [出力先フォルダ（既定: ./qa）]
# 出力: <出力先>/render.pdf と <出力先>/slide-NN.jpg
set -euo pipefail

SRC="${1:?対象の pptx を指定する}"
OUT="${2:-qa}"
[ -f "$SRC" ] || { echo "見つからない: $SRC" >&2; exit 1; }

# PowerPoint はサンドボックス化されているため、対象 pptx も出力先もコンテナ内に置く。
# 複製は毎回別名にする。こうすると、コピーに失敗したときは前回の複製を描画せず、開く段階でエラーになる。
DIR=~/Library/Containers/com.microsoft.Powerpoint/Data/tmp_render
TS=$(date +%H%M%S)
mkdir -p "$DIR" "$OUT"
cp "$SRC" "$DIR/deck-$TS.pptx"

# 対象は full name で特定する。active presentation で取ると、開けなかったときに
# 前面にあるユーザーの別資料を保存せずに閉じてしまう（実際に起きた）。
osascript - "$DIR/deck-$TS.pptx" "$DIR/render-$TS.pdf" <<'EOF'
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

# 前回の画像を消してから書き出す（枚数や番号の桁数が変わると古い画像が混ざるため）
cp "$DIR/render-$TS.pdf" "$OUT/render.pdf"
find "$OUT" -maxdepth 1 -name 'slide-*.jpg' -delete
pdftoppm -jpeg -r 100 "$OUT/render.pdf" "$OUT/slide"
echo "$OUT/render.pdf: $(ls "$OUT"/slide-*.jpg | wc -l | tr -d ' ') 枚"
