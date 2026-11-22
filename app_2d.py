"""抜管予報 — 2Dビュー（Streamlit アプリ）。

3Dビューは別アプリ（app_3d.py）。ヘッダーの「3Dビュー」ボタンで切り替えます。
接続先は .streamlit/secrets.toml の APP_3D_URL（または環境変数）で変更できます。
"""
import streamlit as st

import view_app as V

st.set_page_config(page_title="抜管予報（2D）", layout="wide",
                   initial_sidebar_state="collapsed")

# ヘッダーは「2Dビュー / 再生 / 倍速 / 時刻 / [3Dビュー] / テーマ / 時刻」の順。
# 隠した iframe 側の 3Dビュー ボタンの位置（右端から 96px・幅 73px）に実リンクを重ねる。
V.render_view("2d", "3Dビュー", V.app_3d_url(), slot_right=96, slot_width=76)
