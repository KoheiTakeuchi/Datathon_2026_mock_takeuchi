"""Datathon Japan 2026 Team 3 — 抜管失敗の確率モック。

このフォルダ内の静的HTML（2D / 3D）を表示するだけの Streamlit アプリ。
Streamlit のサイドバーは使わず、画面の切り替えは HTML 側のリンクで行う。
localStorage を使って「3Dを見ている」状態を HTML と共有する。
"""
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

HERE = Path(__file__).resolve().parent
PAGES = {
    "2d": "extubation_risk_mock.html",
    "3d": "extubation_risk_3d_mock.html",
}
HEIGHT = 1500

st.set_page_config(page_title="抜管失敗の確率 — Team 3", layout="wide")

st.markdown(
    "<style>"
    "#MainMenu, footer, header {visibility:hidden}"
    "[data-testid='collapsedControl'], [data-testid='stSidebar'], "
    "[data-testid='stToolbar'], [data-testid='stDecoration'] {display:none !important}"
    ".block-container{padding-top:.6rem;padding-bottom:.4rem;max-width:100%}"
    "iframe{border:0}"
    "</style>",
    unsafe_allow_html=True,
)

# HTML 側でナビゲーションしたら、query パラメータを書き換えて Streamlit を再実行させる
components.html(
    """
    <script>
    (function(){
      const url = new URL(window.parent.location.href);
      const q = url.searchParams.get("view");
      const saved = localStorage.getItem("ei-view");
      if (!q && saved) {
        url.searchParams.set("view", saved);
        window.parent.history.replaceState({}, "", url);
        window.parent.location.reload();
      }
      window.addEventListener("storage", e => {
        if (e.key !== "ei-view" || !e.newValue) return;
        const u = new URL(window.parent.location.href);
        if (u.searchParams.get("view") === e.newValue) return;
        u.searchParams.set("view", e.newValue);
        window.parent.location.href = u.toString();
      });
    })();
    </script>
    """,
    height=0,
)

view = st.query_params.get("view", "2d")
if view not in PAGES:
    view = "2d"

case_q = st.query_params.get("case", "")
url_q = PAGES[view] + (f"?case={case_q}" if case_q else "")
html = (HERE / PAGES[view]).read_text(encoding="utf-8")
st.components.v1.html(html, height=HEIGHT, scrolling=True)
