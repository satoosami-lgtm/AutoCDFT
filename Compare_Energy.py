#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Compare_Energy.py
==================
Gen_CDFT_inp.py が作成した一点計算ジョブを実行・formchk変換した後の .fchk 群から、
同じラベル・同じ電荷について、どの多重度が最安定(エネルギー最小)かを判定し、
結果を CDFT_trios.json に保存する。

対象ファイル名の形式:
    f"{計算レベル}_CDFT_{電荷}_{多重度}_{label}.fchk"

CDFT_trios.json の形式:
{
  "EQ1": {
      "level": "B3LYP_6-31Gd",
      "0":  {"multiplicity": 1, "energy": -13612.34, "fchk": "..."},
      "1":  {"multiplicity": 2, "energy": -13598.11, "fchk": "..."},
      "-1": {"multiplicity": 2, "energy": -13620.02, "fchk": "..."}
  },
  ...
}
（energyはcclibの単位＝eV, SCFエネルギーの最終値）
"""

import os
import re
import glob
import json
import cclib

FNAME_RE = re.compile(
    r"^(?P<level>.+)_CDFT_(?P<charge>-?\d+)_(?P<mult>\d+)_(?P<label>.+)\.fchk$"
)


def collect_results(fchk_dir="."):
    """label -> level -> charge -> [候補(dict)] の形で結果を集計する"""
    results = {}
    for f in glob.glob(os.path.join(fchk_dir, "*_CDFT_*.fchk")):
        base = os.path.basename(f)
        m = FNAME_RE.match(base)
        if not m:
            continue
        level = m.group("level")
        charge = m.group("charge")
        mult = int(m.group("mult"))
        label = m.group("label")

        try:
            data = cclib.io.ccread(f)
            energies = getattr(data, "scfenergies", None)
            if energies is None or len(energies) == 0:
                raise ValueError("scfenergies not found")
            energy = float(energies[-1])
        except Exception as e:
            print(f"[警告] {f} からエネルギーを取得できませんでした ({e})。スキップします。")
            continue

        (
            results.setdefault(label, {})
            .setdefault(level, {})
            .setdefault(charge, [])
            .append({"multiplicity": mult, "energy": energy, "fchk": base})
        )
    return results


def pick_lowest(results):
    """各(label, level, charge)についてエネルギー最小の候補を選ぶ"""
    trios = {}
    for label, levels in results.items():
        for level, charges in levels.items():
            entry = trios.setdefault(label, {"level": level})
            for charge, candidates in charges.items():
                best = min(candidates, key=lambda c: c["energy"])
                entry[charge] = best
                others = [c["multiplicity"] for c in candidates if c is not best]
                if others:
                    print(
                        f"[{label}] charge={charge}: 多重度{best['multiplicity']}が最安定 "
                        f"(比較した他の多重度: {others})"
                    )
    return trios


def main():
    results = collect_results(".")
    if not results:
        print("CDFT一点計算の.fchkファイルが見つかりませんでした。")
        return

    trios = pick_lowest(results)

    with open("CDFT_trios.json", "w", encoding="utf-8") as fh:
        json.dump(trios, fh, ensure_ascii=False, indent=2)
    print(f"[Compare_Energy] CDFT_trios.json を作成しました（{len(trios)}構造）")


if __name__ == "__main__":
    main()
