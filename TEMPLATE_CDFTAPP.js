// TEMPLATE_CDFTAPP.js
// =====================
// 3Dmol.js を用いてCDFT(概念密度汎関数理論)解析結果を表示するビューアの雛形。
// Gen3Dviewer_CDFT.py が __LABEL__ / __XYZ_DATA__ / __CUBE_DATA__ を
// 実データに置換し、CDFT_app_{label}.js として出力する。

const LABEL = "__LABEL__";
const XYZ_DATA = __XYZ_DATA__;    // 文字列(XYZ形式の分子構造)
const CUBE_DATA = __CUBE_DATA__;  // { "ファイル名": "cubeファイルの内容(文字列)", ... }

function initCDFTViewer(elementId) {
  const viewer = $3Dmol.createViewer(elementId, { backgroundColor: "white" });

  // 分子構造の表示
  viewer.addModel(XYZ_DATA, "xyz");
  viewer.setStyle({}, { stick: {}, sphere: { scale: 0.25 } });

  // 各cube(Fukui関数・デュアル記述子等)の等値面をあらかじめ生成し、
  // 最初の1つだけ表示、残りは非表示にしておく
  const cubeNames = Object.keys(CUBE_DATA);
  const isoControls = [];

  cubeNames.forEach((name, idx) => {
    const cubeStr = CUBE_DATA[name];

    const volPos = viewer.addVolumetricData(cubeStr, "cube", {
      isoval: 0.02,
      color: "red",
      opacity: 0.6,
    });
    const volNeg = viewer.addVolumetricData(cubeStr, "cube", {
      isoval: -0.02,
      color: "blue",
      opacity: 0.6,
    });

    if (idx !== 0) {
      volPos.hide();
      volNeg.hide();
    }
    isoControls.push({ name, volPos, volNeg });
  });

  viewer.zoomTo();
  viewer.render();

  return { viewer, isoControls, label: LABEL, cubeNames };
}

document.addEventListener("DOMContentLoaded", function () {
  window.cdftViewer = initCDFTViewer("cdft-viewer");

  // cube切り替え用プルダウンの構築
  const selector = document.getElementById("cube-selector");
  if (selector) {
    window.cdftViewer.cubeNames.forEach((name) => {
      const opt = document.createElement("option");
      opt.value = name;
      opt.textContent = name;
      selector.appendChild(opt);
    });

    selector.addEventListener("change", (e) => {
      const chosen = e.target.value;
      window.cdftViewer.isoControls.forEach((c) => {
        if (c.name === chosen) {
          c.volPos.show();
          c.volNeg.show();
        } else {
          c.volPos.hide();
          c.volNeg.hide();
        }
      });
      window.cdftViewer.viewer.render();
    });
  }
});
