#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gen3Dviewer_CDFT.py
====================
CDFT解析結果(cubeファイル)と分子構造(xyz)を 3Dmol.js で可視化するページを
ラベルごとに生成する。

入力テンプレート:
    TEMPLATE_CDFTAPP.js : 3Dmol.jsビューアの雛形（xyz/cubeデータのプレースホルダを含む）
    TEMPLATE.html        : TEMPLATE_CDFTAPP.jsを読み込むHTMLの雛形

出力:
    CDFT_app_{label}.js  : ラベル固有のデータを埋め込んだビューアスクリプト
    CDFT_{label}.html    : 上記jsを読み込む単体ページ
    CDFT_VIEWALL.html    : 全ラベルの一覧ページ
"""

import os
import json
import glob
import cclib
from cclib.parser.utils import PeriodicTable

TEMPLATE_JS = "TEMPLATE_CDFTAPP.js"
TEMPLATE_HTML = "TEMPLATE.html"
TRIOS_JSON = "CDFT_trios.json"

pt = PeriodicTable()


def load_xyz_block(fchk_path):
    """中性種(電荷0)のfchkから XYZ形式の文字列を作る"""
    data = cclib.io.ccread(fchk_path)
    natom = data.natom
    coords = data.atomcoords[-1]
    lines = [str(natom), os.path.basename(fchk_path)]
    for num, xyz in zip(data.atomnos, coords):
        sym = pt.element[num]
        lines.append(f"{sym} {xyz[0]:.6f} {xyz[1]:.6f} {xyz[2]:.6f}")
    return "\n".join(lines)


def find_cubes(level, label):
    """run_Multiwfn_CDFT.sh が出力した '{level}_CDFT_{label}_*.cube' を集める"""
    return sorted(glob.glob(f"{level}_CDFT_{label}_*.cube"))


def render(template, replacements):
    out = template
    for key, val in replacements.items():
        out = out.replace(key, val)
    return out


def main():
    with open(TRIOS_JSON, encoding="utf-8") as fh:
        trios = json.load(fh)
    with open(TEMPLATE_JS, encoding="utf-8") as fh:
        template_js = fh.read()
    with open(TEMPLATE_HTML, encoding="utf-8") as fh:
        template_html = fh.read()

    pages = []
    for label, info in trios.items():
        level = info["level"]
        fchk0 = info["0"]["fchk"]

        xyz_block = load_xyz_block(fchk0)
        cube_files = find_cubes(level, label)
        if not cube_files:
            print(f"[警告] {label}: cubeファイルが見つかりません（run_Multiwfn_CDFT.shは実行済みですか？）")

        cubes_data = {}
        for cube in cube_files:
            with open(cube, encoding="utf-8") as fh:
                cubes_data[os.path.basename(cube)] = fh.read()

        js_out = render(
            template_js,
            {
                "__LABEL__": label,
                "__XYZ_DATA__": json.dumps(xyz_block),
                "__CUBE_DATA__": json.dumps(cubes_data),
            },
        )
        js_name = f"CDFT_app_{label}.js"
        with open(js_name, "w", encoding="utf-8") as fh:
            fh.write(js_out)

        html_out = render(
            template_html,
            {
                "__LABEL__": label,
                "__APP_JS__": js_name,
            },
        )
        html_name = f"CDFT_{label}.html"
        with open(html_name, "w", encoding="utf-8") as fh:
            fh.write(html_out)

        pages.append((label, html_name))
        print(f"[Gen3Dviewer_CDFT] {html_name} / {js_name} を作成しました")

    write_index(pages)


def write_index(pages, out_name="CDFT_VIEWALL.html"):
    items = "\n".join(
        f'      <li><a href="{html_name}" target="_blank">{label}</a></li>'
        for label, html_name in sorted(pages)
    )
    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <title>CDFT Viewer 一覧</title>
  <style>
    body {{ font-family: sans-serif; padding: 16px; }}
    li {{ margin: 4px 0; }}
  </style>
</head>
<body>
  <h1>CDFT解析結果一覧</h1>
  <ul>
{items}
  </ul>
</body>
</html>
"""
    with open(out_name, "w", encoding="utf-8") as fh:
        fh.write(html)
    print(f"[Gen3Dviewer_CDFT] {out_name} を作成しました（{len(pages)}件）")


if __name__ == "__main__":
    main()
