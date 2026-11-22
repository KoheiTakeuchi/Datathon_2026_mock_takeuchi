"""抜管予報 — 3Dビュー（Streamlit アプリ）。

2Dビューは別アプリ（app_2d.py）。ヘッダーの「2Dビュー」ボタンで切り替えます。
接続先は .streamlit/secrets.toml の APP_2D_URL（または環境変数）で変更できます。
"""
import streamlit as st

import view_app as V

st.set_page_config(page_title="抜管予報（3D）", layout="wide",
                   initial_sidebar_state="collapsed")

# ヘッダーは「3Dビュー / 再生 / 倍速 / 時刻 / [2Dビュー] / テーマ / 時刻」の順。
# 隠した iframe 側の 2Dビュー ボタンの位置（右端から 107px・幅 75px）に実リンクを重ねる。
V.render_view("3d", "2Dビュー", V.app_2d_url(), slot_right=107, slot_width=78)
