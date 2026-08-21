#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gen_CDFT_inp.py
================
Conceptual DFT (CDFT) 解析用の Gaussian 一点計算入力ファイル(.gjf)を自動生成する。

処理の流れ
----------
1. カレントディレクトリ内の EQ / TS 構造の .fchk ファイルからラベルを取得する。
   （ファイル名に "EQ" または "TS" を含む *.fchk が対象。ラベル = 拡張子を除いたファイル名）
2. 各ラベルについて cclib で .fchk から原子座標と計算レベル(汎関数/基底関数)を取得する。
3. settings（電荷・多重度の組）ごとに CDFT 用一点計算の .gjf を作成する。
   ファイル名: f"{計算レベル}_CDFT_{電荷}_{多重度}_{label}.gjf"
4. 作成した全ジョブを実行する run_CDFT.sh を作成する。

前提
----
- Gaussian16 (g16) を利用する。
- cclib がインストールされていること。
"""

import os
import re
import glob
import cclib
from cclib.parser.utils import PeriodicTable

# ---------------------------------------------------------------------------
# 電荷・多重度の設定
# ---------------------------------------------------------------------------
# CDFT解析(Fukui関数・求電子性指数など)には、中性種(N電子系)に加えて
# カチオン(N-1電子系)・アニオン(N+1電子系)のエネルギー/波動関数が必要になる。
# 開殻種では基底スピン状態が自明でないことがあるため、同じ電荷について
# 複数の多重度を計算しておき、後段の Compare_Energy.py で最安定な多重度を選ぶ。
#
# 必要に応じて系に合わせて追加・変更すること。
settings = [
    [0, 1],   # 中性種：一重項
    [0, 3],   # 中性種：三重項（開殻の可能性を考慮）
    [1, 2],   # カチオン(N-1電子)：二重項
    [1, 4],   # カチオン(N-1電子)：四重項
    [-1, 2],  # アニオン(N+1電子)：二重項
    [-1, 4],  # アニオン(N+1電子)：四重項
]

NPROC = 16
MEM = "24GB"

pt = PeriodicTable()


def sanitize_level(level: str) -> str:
    """'B3LYP/6-31G(d)' のような計算レベル文字列をファイル名に使える形式にする"""
    return re.sub(r"[\/\\\(\)\*,]", "_", level)


def get_labels(fchk_dir="."):
    """EQ/TSラベルを、カレント(指定)ディレクトリの.fchkファイル名から取得する"""
    labels = []
    for f in glob.glob(os.path.join(fchk_dir, "*.fchk")):
        base = os.path.splitext(os.path.basename(f))[0]
        if re.search(r"(EQ|TS)", base, re.IGNORECASE):
            labels.append(base)
    return sorted(set(labels))


def get_level_of_theory(data) -> str:
    """cclibのパース結果から 'functional/basis' 形式の計算レベル文字列を作る"""
    metadata = getattr(data, "metadata", {}) or {}
    functional = metadata.get("functional") or "UNK"
    basis = metadata.get("basis_set") or "UNK"
    return f"{functional}/{basis}"


def build_gjf(label, level, charge, mult, atomnos, last_coords, out_path):
    """CDFT用一点計算(SP)のGaussian入力ファイルを書き出す"""
    functional, _, basis = level.partition("/")
    chk_name = os.path.splitext(out_path)[0] + ".chk"

    lines = [
        f"%chk={chk_name}",
        f"%nprocshared={NPROC}",
        f"%mem={MEM}",
        f"# {functional}/{basis} SP nosymm",
        "",
        f"{label} CDFT single point charge={charge} mult={mult}",
        "",
        f"{charge} {mult}",
    ]
    for num, xyz in zip(atomnos, last_coords):
        sym = pt.element[num]
        lines.append(f"{sym:2s} {xyz[0]:14.8f} {xyz[1]:14.8f} {xyz[2]:14.8f}")
    lines.append("")
    lines.append("")

    with open(out_path, "w") as fh:
        fh.write("\n".join(lines))


def write_run_script(gjf_files, script_name="run_CDFT.sh"):
    with open(script_name, "w") as fh:
        fh.write("#!/bin/bash\n")
        fh.write("# CDFT用一点計算を一括実行する\n")
        fh.write("set -e\n\n")
        for gjf in gjf_files:
            log = gjf.replace(".gjf", ".log")
            fh.write(f'echo "Running {gjf}"\n')
            fh.write(f"g16 < {gjf} > {log}\n")
    os.chmod(script_name, 0o755)
    print(f"[Gen_CDFT_inp] {script_name} を作成しました（{len(gjf_files)}ジョブ）")


def main():
    labels = get_labels(".")
    if not labels:
        print("EQ/TSラベルを持つ.fchkファイルが見つかりませんでした。")
        return

    gjf_files = []
    for label in labels:
        fchk_path = f"{label}.fchk"
        print(f"[Gen_CDFT_inp] 読み込み中: {fchk_path}")
        data = cclib.io.ccread(fchk_path)
        level = sanitize_level(get_level_of_theory(data))
        last_coords = data.atomcoords[-1]

        for charge, mult in settings:
            out_name = f"{level}_CDFT_{charge}_{mult}_{label}.gjf"
            build_gjf(label, level, charge, mult, data.atomnos, last_coords, out_name)
            gjf_files.append(out_name)
            print(f"  -> {out_name} を作成しました")

    write_run_script(gjf_files)


if __name__ == "__main__":
    main()
