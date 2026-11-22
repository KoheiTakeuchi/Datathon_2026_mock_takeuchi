"""抜管予報 — 3Dビュー（Streamlit アプリ）。

2D は別アプリ app_2d.py で、ヘッダーの「2Dビュー」ボタンから開きます。
接続先は .streamlit/secrets.toml の APP_2D_URL（または環境変数）で変更できます。
"""
import streamlit as st

import view_app as V

st.set_page_config(page_title="抜管予報（3D）", layout="wide", initial_sidebar_state="collapsed")

V.render_3d()
