#!/bin/bash
# run_Multiwfn_CDFT.sh
# =====================
# 1. CDFT一点計算の .chk -> .fchk へ変換する (formchk)
# 2. CDFT_trios.json から各ラベルの最安定な(電荷0/+1/-1)の組を読み込み、
#    Multiwfn の Conceptual DFT 解析 (メインメニュー22) を自動実行するマクロを作成・実行する
# 3. Multiwfn が出力するデフォルト名の .cub ファイルを
#    f"{計算レベル}_CDFT_{label}.cube" 相当の名前にリネームする
#
# 前提: Multiwfn, formchk (Gaussianユーティリティ), python3 が PATH 上で利用可能なこと。
# 注意: Multiwfnの対話メニュー番号はバージョンによって変わることがあるため、
#       実際にMultiwfnを対話実行して "Conceptual DFT analysis" メニューの
#       選択肢番号を確認し、下記マクロ内の番号を必要に応じて調整すること。

set -e

JSON="CDFT_trios.json"
if [ ! -f "$JSON" ]; then
    echo "エラー: $JSON が見つかりません。先に Compare_Energy.py を実行してください。"
    exit 1
fi

# --- 1. chk -> fchk 変換 ---------------------------------------------------
echo "=== chk -> fchk 変換 ==="
for chk in *_CDFT_*.chk; do
    [ -e "$chk" ] || continue
    fchk="${chk%.chk}.fchk"
    if [ ! -f "$fchk" ]; then
        echo "formchk: $chk -> $fchk"
        formchk "$chk" "$fchk"
    fi
done

# --- 2. CDFT_trios.json からラベル一覧・組情報を取得して解析 ---------------
labels=$(python3 -c "import json;print('\n'.join(json.load(open('$JSON')).keys()))")

for label in $labels; do
    echo "=== ${label} のCDFT解析 ==="

    level=$(python3 -c "import json; print(json.load(open('$JSON'))['$label']['level'])")
    fchk0=$(python3 -c "import json; print(json.load(open('$JSON'))['$label']['0']['fchk'])")
    fchkP=$(python3 -c "import json; print(json.load(open('$JSON'))['$label']['1']['fchk'])")
    fchkM=$(python3 -c "import json; print(json.load(open('$JSON'))['$label']['-1']['fchk'])")

    macro="Multiwfn_CDFT_${label}.mwfn"

    # Multiwfn メインメニュー "22 Conceptual DFT analysis" の対話をマクロ化。
    # 起点の波動関数(中性N電子系)を引数に渡し、続けてN+1電子系・N-1電子系の
    # fchkパスを入力、各種CDFT記述子(Fukui関数f+/f-/f0, デュアル記述子等)の
    # cube出力までを自動化する想定。
    cat > "$macro" << EOF
22
-1
${fchkP}
${fchkM}
2
3
4
5
0
q
EOF

    Multiwfn "$fchk0" < "$macro" > "Multiwfn_CDFT_${label}.log" 2>&1

    # --- 3. 出力cubeファイルのリネーム --------------------------------
    for cube in *.cub; do
        [ -e "$cube" ] || continue
        base=$(basename "$cube" .cub)
        mv "$cube" "${level}_CDFT_${label}_${base}.cube"
        echo "  -> ${level}_CDFT_${label}_${base}.cube"
    done
done

echo "=== run_Multiwfn_CDFT.sh 完了 ==="
