"""抜管予報 — 2Dビュー（Streamlit アプリ）。

画面は streamlit_app.py（ネイティブ実装）と同じ。3D は別アプリ app_3d.py で、
ヘッダーの「3Dビュー」ボタンから開きます。接続先は .streamlit/secrets.toml の
APP_3D_URL（または環境変数）で変更できます。
"""
import streamlit as st

import view_app as V

st.set_page_config(page_title="抜管予報", layout="wide", initial_sidebar_state="collapsed")

V.render_3d_link()

import view_2d  # noqa: E402  (set_page_config の後に読み込む)

view_2d.run()
