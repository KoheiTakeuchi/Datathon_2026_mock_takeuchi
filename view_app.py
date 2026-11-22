"""抜管予報 — モックの共通用。

2D（app_2d.py）と 3D（app_3d.py）は別々の Streamlit アプリとして動かし、
ヘッダーの「2Dビュー／3Dビュー」ボタンで互いの URL を開きます。

このモジュールが扱うのは、HTML の見た目を崩さずに Streamlit に載せるための
最小限の処理だけです。

1) iframe の高さ: height 引数（名目値）ではなく、親ページの CSS でコンポーネントの
   ラッパーと中の iframe を calc(100dvh - 余白) に固定する。iframe 内のビューポートが
   実画面の高さになり、HTML 側の「画面の高さ前提」レイアウトが間延びせず、
   二重スクロールも出ない。
2) 画面読み込み中: 時計の右に小さく「読み込み中」を出し、最初の描画で消す。
3) 2D は音声なし（Audio の生成・自動再生を止める）。
4) ビュー切替ボタン: iframe 内の a[data-view] は sandbox で親を遷移できないため隠し、
   同じ位置・同じ見た目で親側のリンク（実 URL）を重ねる。
"""
from __future__ import annotations

from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

HERE = Path(__file__).resolve().parent
PAGES = {
    "2d": "extubation_risk_mock.html",
    "3d": "extubation_risk_3d_mock.html",
}
NOMINAL_HEIGHT = 800          # 名目値。実際の高さは CSS が決める
CHROME_PX = 0                 # Streamlit 側で確保する余白

# もう一方のアプリの URL（Streamlit の .streamlit/secrets.toml か環境変数でも上書き可）
DEFAULT_APP_2D = "http://localhost:8501"
DEFAULT_APP_3D = "http://localhost:8502"


def _secret(name: str, default: str) -> str:
    try:
        value = st.secrets.get(name)          # type: ignore[union-attr]
        if value:
            return str(value)
    except Exception:
        pass
    import os
    return os.environ.get(name, default)


def base_css() -> None:
    st.markdown(
        f"""
        <style>
          /* Chrome（メニュー・フッター・ツールバー等）は出さない */
          #MainMenu, footer, header [data-testid="stToolbar"] {{visibility: hidden}}
          [data-testid="stToolbar"], [data-testid="stDecoration"],
          [data-testid="stStatusWidget"], [data-testid="stSidebar"],
          [data-testid="collapsedControl"], #stAppHeader {{display: none !important}}

          /* 余白を 0 に寄せる */
          [data-testid="stAppViewContainer"] > .main {{padding: 0 !important}}
          .block-container {{padding: 0 !important; max-width: 100% !important}}
          [data-testid="stMainBlockContainer"] {{padding: 0 !important; max-width: 100% !important}}
          [data-testid="stVerticalBlock"] {{gap: 0 !important}}
          [data-testid="stElementContainer"] {{margin: 0 !important}}
          iframe[title="st.iframe"], iframe.stIFrame {{width: 100% !important; border: 0 !important}}

          /* 本文の iframe（2D/3D の HTML）を実画面の高さに固定する */
          [data-testid="stElementContainer"]:has(> iframe[height="{NOMINAL_HEIGHT}"]) {{
            height: calc(100dvh - {CHROME_PX}px) !important;
            max-height: calc(100dvh - {CHROME_PX}px) !important;
            width: 100% !important;
            display: block;
          }}
          [data-testid="stElementContainer"]:has(> iframe[height="{NOMINAL_HEIGHT}"]) > iframe {{
            height: calc(100dvh - {CHROME_PX}px) !important;
            min-height: calc(100dvh - {CHROME_PX}px) !important;
          }}

          /* 縦スクロールは iframe 内だけに任せる */
          html, body {{overflow: hidden !important; height: 100%}}
          #root, [data-testid="stApp"], [data-testid="stAppViewContainer"] {{overflow: hidden !important}}

          /* フォールバック: dvh 非対応ブラウザ */
          @supports not (height: 100dvh) {{
            [data-testid="stElementContainer"]:has(> iframe[height="{NOMINAL_HEIGHT}"]) {{
              height: calc(100vh - {CHROME_PX}px) !important;
              max-height: calc(100vh - {CHROME_PX}px) !important;
            }}
            [data-testid="stElementContainer"]:has(> iframe[height="{NOMINAL_HEIGHT}"]) > iframe {{
              height: calc(100vh - {CHROME_PX}px) !important;
              min-height: calc(100vh - {CHROME_PX}px) !important;
            }}
          }}

          /* ===== もう一方のビューへのリンク（iframe 内のボタンの上に重ねる） ===== */
          .st-key-ei-switch [data-testid="stElementContainer"] {{
            height: auto !important; max-height: 48px !important;
          }}
          .st-key-ei-switch {{margin: 0 !important}}
        </style>
        """,
        unsafe_allow_html=True,
    )


def overlay_css(slot_right: int, slot_width: int, narrow_hidden: bool) -> None:
    """親側のリンクを、iframe のヘッダーにある 2D/3D ボタンの位置に重ねる CSS。"""
    hide_narrow = ".st-key-ei-switch{display:none !important}" if narrow_hidden else ""
    st.markdown(
        f"""
        <style>
          .st-key-ei-switch {{
            position: fixed; top: 0; right: {slot_right}px; z-index: 2147483000;
            width: {slot_width}px; height: 48px !important;
            display: flex; align-items: center; margin: 0 !important;
            overflow: visible !important;
          }}
          .st-key-ei-switch [data-testid="stVerticalBlock"],
          .st-key-ei-switch [data-testid="stVerticalBlockBorderWrapper"] {{
            margin: 0 !important; gap: 0 !important; width: 100%;
          }}
          .st-key-ei-switch .stLinkButton,
          .st-key-ei-switch .stLinkButton > div,
          .st-key-ei-switch [data-testid="stLinkButton"],
          .st-key-ei-switch [data-testid="stLinkButton"] > div {{
            margin: 0 !important; width: 100%;
          }}
          .st-key-ei-switch a,
          .st-key-ei-switch [data-testid="stLinkButton"] a {{
            display: flex !important; align-items: center; justify-content: center;
            width: 100%; height: 29px; min-height: 29px;
            padding: 0 11px !important; border-radius: 8px;
            border: 1px solid var(--line, rgba(127,127,127,.3));
            background: var(--panel, rgba(127,127,127,.08));
            color: transparent !important; font-size: 12px !important; line-height: 1;
            text-decoration: none !important; box-shadow: none !important;
          }}
          .st-key-ei-switch a:hover,
          .st-key-ei-switch [data-testid="stLinkButton"] a:hover {{
            filter: brightness(1.1); color: transparent !important;
          }}
          .st-key-ei-switch a * {{
            color: transparent !important; font-size: 0 !important;
          }}
          @media (max-width: 900px) {{
            .st-key-ei-switch {{
              right: {max(8, slot_right - 30)}px !important; width: 92px !important;
            }}
            {hide_narrow}
          }}
        </style>
        """,
        unsafe_allow_html=True,
    )


# HTML の末尾に足す小さなブリッジ
RUNTIME = """
<style>
  .ei-loading{display:inline-flex;align-items:center;gap:5px;margin-left:6px;
    font-size:10.5px;color:var(--sub,#8d9cb2);vertical-align:middle;white-space:nowrap}
  .ei-loading .dot{width:10px;height:10px;border-radius:50%;
    border:2px solid color-mix(in srgb,currentColor 30%,transparent);
    border-top-color:#1f6feb;animation:eiSpin .8s linear infinite}
  .ei-loading.done{display:none}
  @keyframes eiSpin{to{transform:rotate(360deg)}}
</style>
<script>
(function(){
  // ---- 読み込み中の表示（2D / 3D 共通） ----
  function settle(){
    var el = document.querySelector('.ei-loading');
    if (el) el.classList.add('done');
  }
  function ready(){
    try {
      var host = document.querySelector('#hdrClock') || document.querySelector('.clock');
      if (!host || document.querySelector('.ei-loading')) return;
      var el = document.createElement('span');
      el.className = 'clock-loading ei-loading';
      el.innerHTML = '<span class="dot"></span><span>読み込み中</span>';
      host.appendChild(el);
      setTimeout(settle, 300);
    } catch(e){}
  }
  ready();
  if (document.readyState === 'complete') setTimeout(settle, 300);
  else window.addEventListener('load', function(){ setTimeout(settle, 300); });
  setTimeout(settle, 2500);

  // ---- 2D は音声なし ----
  var is3D = !!document.getElementById('scene');
  if (!is3D) {
    try {
      window.Audio = function(){
        return { play: function(){ return Promise.reject(); }, pause: function(){},
          addEventListener: function(){}, removeEventListener: function(){},
          load: function(){}, currentTime: 0, volume: 0 };
      };
    } catch(e){}
  }

  // ---- 2D/3D の切替ボタン ----
  // iframe は sandbox のため親を遷移できない。ヘッダーの同じ位置に親側の実リンクを
  // 重ねているので、iframe 内の同じボタンは隠すだけでよい。
  document.addEventListener('click', function(ev){
    try {
      var a = ev.target && ev.target.closest && ev.target.closest('a[data-view]');
      if (!a) return;
      ev.preventDefault();
    } catch(e){}
  }, true);
  try {
    var hide = document.createElement('style');
    hide.textContent = '#demoBar a[data-view]{visibility:hidden !important;pointer-events:none !important}';
    (document.head || document.documentElement).appendChild(hide);
  } catch(e){}
})();
</script>
"""


def render_view(view: str, switch_label: str, switch_url: str,
                slot_right: int, slot_width: int, narrow_hidden: bool = False) -> None:
    """HTML を 1 枚だけ表示し、そのヘッダーの 2D/3D ボタン位置に実リンクを重ねる。"""
    base_css()
    overlay_css(slot_right, slot_width, narrow_hidden)

    with st.container(key="ei-switch"):
        st.link_button(switch_label, switch_url, help=None)

    html = (HERE / PAGES[view]).read_text(encoding="utf-8") + RUNTIME
    components.html(html, height=NOMINAL_HEIGHT, scrolling=False)


def app_2d_url() -> str:
    return _secret("APP_2D_URL", DEFAULT_APP_2D)


def app_3d_url() -> str:
    return _secret("APP_3D_URL", DEFAULT_APP_3D)
