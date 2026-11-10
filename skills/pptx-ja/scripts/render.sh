#!/bin/bash
# 実 PowerPoint（Mac）で pptx を PDF に書き出し、スライドごとの画像にする。
# 使い方: render.sh 対象.pptx [出力先フォルダ（既定: ./qa）]
# 出力: <出力先>/render.pdf と <出力先>/slide-NN.jpg
set -euo pipefail

SRC="${1:?対象の pptx を指定する}"
OUT="${2:-qa}"
[ -f "$SRC" ] || { echo "見つからない: $SRC" >&2; exit 1; }
mkdir -p "$OUT"
OUT="$(cd "$OUT" && pwd)"

# 複製は出力先に置き、open -a で PowerPoint に開かせる。PowerPoint のコンテナ
# （~/Library/Containers/com.microsoft.Powerpoint/...）へのコピーは OS の権限で拒否されることがある。
# 複製は毎回別名にする。開いたままの古い複製と取り違えず、コピーに失敗したときは開く段階でエラーになる。
find "$OUT" -maxdepth 1 -name 'deck-*.pptx' -delete
TS=$(date +%H%M%S)
DECK="$OUT/deck-$TS.pptx"
PDF="$OUT/render.pdf"
cp "$SRC" "$DECK"
rm -f "$PDF"
open -a "Microsoft PowerPoint" "$DECK"
sleep 6

# 対象は full name で特定する。active presentation で取ると、開けなかったときに
# 前面にあるユーザーの別資料を保存せずに閉じてしまう（実際に起きた）。
osascript - "$DECK" "$PDF" <<'EOF'
on run argv
	set target to item 1 of argv
	set outPath to POSIX file (item 2 of argv)
	tell application "Microsoft PowerPoint"
		set found to missing value
		repeat with i from 1 to (count of presentations)
			if (full name of presentation i) is target then set found to presentation i
		end repeat
		if found is missing value then error "対象を開けなかった(他の資料には触れない)"
		with timeout of 120 seconds
			save found in outPath as save as PDF
		end timeout
		close found saving no
	end tell
end run
EOF

[ -f "$PDF" ] || { echo "PDF が作られなかった: $PDF" >&2; exit 1; }
# 前回の画像を消してから書き出す（枚数や番号の桁数が変わると古い画像が混ざるため）
find "$OUT" -maxdepth 1 -name 'slide-*.jpg' -delete
pdftoppm -jpeg -r 100 "$PDF" "$OUT/slide"
echo "$PDF: $(ls "$OUT"/slide-*.jpg | wc -l | tr -d ' ') 枚"
