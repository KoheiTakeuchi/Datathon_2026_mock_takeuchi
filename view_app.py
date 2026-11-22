"""抜管予報 — 2D と 3D で共通に使う処理。

- 2D（app_2d.py）: streamlit_app.py と同じネイティブ実装（view_2d.py）。
  ヘッダーの「3Dビュー」ボタンだけ、もう一方のアプリへのリンクに差し替える。
- 3D（app_3d.py）: static/extubation_risk_3d_mock.html を 1 画面に表示する。

どちらも相手のアプリは別 URL で動かす。接続先は .streamlit/secrets.toml の
APP_2D_URL / APP_3D_URL（または環境変数）で決まる。
"""
from __future__ import annotations

import os
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

HERE = Path(__file__).resolve().parent
PAGES = {
    "2d": "extubation_risk_mock.html",
    "3d": "static/extubation_risk_3d_mock.html",
}
NOMINAL_HEIGHT = 800          # 名目値。実際の高さは CSS が決める

DEFAULT_APP_2D = "http://localhost:8501"
DEFAULT_APP_3D = "http://localhost:8502"


def _config(name: str, default: str) -> str:
    try:
        value = st.secrets.get(name)          # type: ignore[union-attr]
        if value:
            return str(value)
    except Exception:
        pass
    return os.environ.get(name, default)


def app_2d_url() -> str:
    return _config("APP_2D_URL", DEFAULT_APP_2D)


def app_3d_url() -> str:
    return _config("APP_3D_URL", DEFAULT_APP_3D)


def render_3d_link() -> None:
    """2D のヘッダーにある「3Dビュー」ボタンを、3D アプリへの実リンクで置き換える。

    ヘッダーは Streamlit の部品で組まれているので、ボタンは CSS で隠し、
    その位置にリンクを重ねる。見た目は元のボタンに合わせる。
    """
    st.markdown(
        f"""
        <style>
          /* 元の「3Dビュー」ボタンは透明にして隠す（位置は確保したまま） */
          .st-key-to_3d button, .st-key-to_3d_mini button {{
            color: transparent !important; background: transparent !important;
            border-color: transparent !important; pointer-events: none !important;
            box-shadow: none !important;
          }}
          .st-key-to_3d button *, .st-key-to_3d_mini button * {{ color: transparent !important }}

          /* リンクをボタンの上に重ねる */
          .ei-view-link {{ position: relative; height: 0; }}
          .ei-view-link a {{
            position: absolute; left: 0; right: 0; top: 4px; height: 34px;
            display: flex; align-items: center; justify-content: center;
            border-radius: 8px; border: 1px solid var(--line);
            background: var(--panel); color: var(--ink) !important;
            font-size: 12px; font-weight: 600; text-decoration: none !important;
            white-space: nowrap;
          }}
          .ei-view-link a:hover {{ border-color: var(--blue); color: var(--blue) !important; }}

          /* Streamlit のツールバーは使わない（ヘッダーのボタンだけ残す） */
          #MainMenu, footer, [data-testid="stToolbar"], [data-testid="stDecoration"],
          [data-testid="stStatusWidget"], [data-testid="stSidebar"] {{display: none !important}}
          [data-testid="stHeader"] {{background: transparent; height: 0}}
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(f'<div class="ei-view-link"><a href="{app_3d_url()}" target="_self">3Dビュー</a></div>',
                unsafe_allow_html=True)


# ===== 3D ビュー（HTML を実画面の高さで 1 枚だけ表示） =====

THREE_D_CSS = f"""
<style>
  #MainMenu, footer, header [data-testid="stToolbar"] {{visibility: hidden}}
  [data-testid="stToolbar"], [data-testid="stDecoration"], [data-testid="stStatusWidget"],
  [data-testid="stSidebar"], [data-testid="collapsedControl"], #stAppHeader {{display: none !important}}
  [data-testid="stAppViewContainer"] > .main {{padding: 0 !important}}
  .block-container {{padding: 0 !important; max-width: 100% !important}}
  [data-testid="stMainBlockContainer"] {{padding: 0 !important; max-width: 100% !important}}
  [data-testid="stVerticalBlock"] {{gap: 0 !important}}
  [data-testid="stElementContainer"] {{margin: 0 !important}}
  html, body {{overflow: hidden !important; height: 100%}}
  #root, [data-testid="stApp"], [data-testid="stAppViewContainer"] {{overflow: hidden !important}}

  /* 本文の iframe を実画面の高さに固定する */
  [data-testid="stElementContainer"]:has(> iframe[height="{NOMINAL_HEIGHT}"]) {{
    height: 100dvh !important; max-height: 100dvh !important; width: 100% !important; display: block;
  }}
  [data-testid="stElementContainer"]:has(> iframe[height="{NOMINAL_HEIGHT}"]) > iframe {{
    height: 100dvh !important; min-height: 100dvh !important; width: 100% !important; border: 0 !important;
  }}
</style>
"""

# 3D HTML の末尾に足す小さなブリッジ（読み込み中表示と、2D へのリンク位置の調整）
THREE_D_RUNTIME = """
<style>
  .ei-loading{display:inline-flex;align-items:center;gap:5px;margin-left:6px;
    font-size:10.5px;color:var(--sub,#8d9cb2);white-space:nowrap}
  .ei-loading .dot{width:10px;height:10px;border-radius:50%;
    border:2px solid var(--track,rgba(127,127,127,.25));border-top-color:var(--cyan,#4fd1ff);
    animation:eiSpin .8s linear infinite}
  .ei-loading.done{display:none}
  @keyframes eiSpin{to{transform:rotate(360deg)}}
</style>
<script>
(function(){
  function settle(){ var el = document.querySelector('.ei-loading'); if (el) el.classList.add('done'); }
  try {
    var host = document.querySelector('#hdrClock') || document.querySelector('.clock');
    if (host && !document.querySelector('.ei-loading')) {
      var el = document.createElement('span');
      el.className = 'clock-loading ei-loading';
      el.innerHTML = '<span class="dot"></span><span>読み込み中</span>';
      host.appendChild(el);
    }
  } catch(e){}
  setTimeout(settle, 600);
  window.addEventListener('load', function(){ setTimeout(settle, 300); });
})();
</script>
"""


def render_3d() -> None:
    """3D ビュー（1 ページに 3D だけ）。2D のボタンは上のリンクで差し替える。"""
    st.markdown(THREE_D_CSS, unsafe_allow_html=True)
    # 自分のヘッダー（3D 側）に重ねる 2D へのリンク
    st.markdown(
        """
        <style>
          .st-key-ei-switch a {
            color: transparent !important;
            background: var(--panel, rgba(127,127,127,.08)) !important;
            border: 1px solid var(--line, rgba(127,127,127,.3)) !important;
            border-radius: 8px !important; text-decoration: none !important;
          }
          .st-key-ei-switch a * { color: transparent !important; font-size: 0 !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )
    with st.container(key="ei-switch"):
        st.link_button("2Dビュー", app_2d_url(), help=None)
    st.markdown(
        """
        <style>
          .st-key-ei-switch {
            position: fixed; top: 0; right: 107px; z-index: 2147483000;
            width: 78px; height: 48px !important; margin: 0 !important;
            display: flex; align-items: center;
          }
          .st-key-ei-switch [data-testid="stVerticalBlock"] { margin: 0 !important; gap: 0 !important; }
          .st-key-ei-switch .stLinkButton, .st-key-ei-switch a { margin: 0 !important; width: 100%; }
          .st-key-ei-switch a {
            height: 29px !important; min-height: 29px !important; padding: 0 11px !important;
            display: flex; align-items: center; justify-content: center;
          }
          @media (max-width: 900px) {
            .st-key-ei-switch { right: 8px !important; width: 92px !important; }
          }
        </style>
        """,
        unsafe_allow_html=True,
    )

    html = (HERE / PAGES["3d"]).read_text(encoding="utf-8")
    # 自動回転は止め、ドラッグしたときだけ回るようにする
    html = html.replace(
        "if (state.autoRotate !== false && !dragging) state.yaw += dt*0.18;",
        "// 自動回転なし（手動ドラッグのみ）",
    )
    components.html(html + THREE_D_RUNTIME, height=NOMINAL_HEIGHT, scrolling=False)
