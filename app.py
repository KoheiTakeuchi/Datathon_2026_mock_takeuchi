"""Datathon Japan 2026 Team 3 — 抜管失敗の確率モック。

このフォルダ内の静的HTML（2D / 3D）をそのまま表示するだけの Streamlit アプリ。
HTML・CSS・JS・音声がフォルダ内で完結しているのでビルドは不要。
"""
from pathlib import Path

import streamlit as st

HERE = Path(__file__).resolve().parent
PAGES = {
    "2Dビュー（患者を選ぶ・確率と推移）": "extubation_risk_mock.html",
    "3Dビュー（確率の変動・関西弁ボイス）": "extubation_risk_3d_mock.html",
}
HEIGHT = 1500

st.set_page_config(page_title="抜管失敗の確率 — Team 3", layout="wide")

st.markdown(
    "<style>#MainMenu, footer {visibility:hidden}"
    ".block-container{padding-top:1rem;padding-bottom:.5rem;max-width:100%}</style>",
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown("### Team 3 / Datathon Japan 2026")
    page = st.radio("画面", list(PAGES))
    case = st.text_input("患者ID（任意）", placeholder="例: I20384")
    st.caption("時刻は画面内の帯（再生・倍率・スライダー）で操作できます。")
    st.caption("合成データ・仮ロジック。診療判断には使用しないでください。")

url = PAGES[page] + (f"?case={case.strip()}" if case.strip() else "")
st.caption(f"表示中: {url}")
st.components.v1.html((HERE / PAGES[page]).read_text(encoding="utf-8"), height=HEIGHT, scrolling=True)
