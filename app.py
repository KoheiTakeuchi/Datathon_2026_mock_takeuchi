"""Datathon Japan 2026 Team 3 — 抜管失敗の確率モック。

このフォルダ内の静的HTML（2D / 3D）を Streamlit に埋め込むだけの薄いアプリ。
HTML/JS 本体は変更せず、単体で開いたときと同じ画面構成になるよう次の3点だけを扱う。

1) iframe の高さ: height 引数（名目値）ではなく、親ページの CSS でコンポーネントの
   ラッパーと中の iframe を calc(100dvh - 余白) に固定する。これで iframe 内の
   ビューポートが実画面の高さになり、HTML 側の「画面の高さ前提」レイアウトが間延びせず、
   二重スクロールも出ない。
2) 画面読み込み中: 2D / 3D で同じ「読み込み中」表示（時計の右に小さく出す）を出す。
3) 2D / 3D の切り替え: HTML の末尾に「a[data-view] のクリックを親へ postMessage する」
   小さなブリッジだけを追記し、親側で ?view= を書き換える。切替中は画面全体に
   splash.html の内容を重ねる。2D は音声なし。
"""
from __future__ import annotations

import json
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
SPLASH_MIN_MS = 500
SPLASH_MAX_MS = 6000


def normalize_view(value: str | None) -> str:
    return value if value in PAGES else "2d"


def read_splash_body() -> str:
    """splash.html の <body> 中身（見た目は splash.html に合わせる）。"""
    try:
        src = (HERE / "splash.html").read_text(encoding="utf-8")
        return src.split("<body>", 1)[1].split("</body>", 1)[0]
    except Exception:
        return "<div style='padding:24px;font-family:sans-serif'>読み込み中…</div>"


st.set_page_config(page_title="抜管予報", layout="wide",
                   initial_sidebar_state="collapsed")

# ===== 画面を埋め尽くすための CSS =====
CHART_IFRAME = '[data-testid="stElementContainer"]:has(> iframe[title="st.iframe"])'
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

      /*
        本文の iframe（2D/3D の HTML）を実画面の高さに固定する。
        計測（Streamlit 1.67 / Edge）では
          [data-testid="stElementContainer"] > iframe.stIFrame(title="st.iframe")
        補助用の小さい iframe は高さ指定を持たないので object では除外される。
      */
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
    </style>
    """,
    unsafe_allow_html=True,
)

# ===== 表示するビュー =====
#  iframe（HTML）は sandbox で親を遷移できず、postMessage も Streamlit 側に
#  横取りされる。そこでヘッダーの 2D/3D ボタンだけは、同じ位置・同じ見た目の
#  Streamlit のリンクボタン（st.query_params をリンク先にする）で置き換える。
#  見た目は CSS で HTML のボタンに合わせ、元のボタンは透明にして隠す。

# 直前のクリックで要求されたビュー（?view= がまだ追いついていない場合に使う）
try:
    query_view = normalize_view(st.query_params.get("view"))
except Exception:
    query_view = "2d"
base = query_view
pending = st.session_state.pop("_pending_view", None)
if pending and pending == base:
    pending = None

view = pending or base
html = (HERE / PAGES[view]).read_text(encoding="utf-8")

# ===== HTML 末尾に足す小さなブリッジ =====
#  - a[data-view] のクリックを親へ postMessage
#  - 2D / 3D 共通の「読み込み中」表示（時計の右に小さく出し、読み込み後に消える）
#  - 2D は音声を使わない（自動再生の要求や Audio の生成を抑止）
RUNTIME = """
<style>
  .ei-loading{display:inline-flex;align-items:center;gap:6px;margin-left:8px;
    font-size:11px;color:var(--sub,#8d9cb2);vertical-align:middle;white-space:nowrap}
  .ei-loading .dot{width:12px;height:12px;border-radius:50%;
    border:2px solid rgba(127,127,127,.28);border-top-color:#1f6feb;
    animation:eiSpin .8s linear infinite}
  .ei-loading.done{display:none}
  @keyframes eiSpin{to{transform:rotate(360deg)}}
  @media (prefers-reduced-motion: reduce){.ei-loading .dot{animation:none;border-top-color:#1f6feb}}
</style>
<script>
(function(){
  // ---- 読み込み中の表示（2D / 3D 共通） ----
  // ヘッダーの時計の右に小さく出し、最初の描画が済んだら消す（読み込み中は動き続ける）
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
  var is3D = !!document.getElementById('scene') || location.search.indexOf('3d') >= 0;
  if (!is3D) {
    try {
      var noop = function(){ return { play: function(){ return Promise.reject(); },
        pause: function(){}, addEventListener: function(){}, removeEventListener: function(){} }; };
      window.Audio = noop;
    } catch(e){}
  }

  // ---- 2D / 3D の切替 ----
  // ヘッダーの 2D/3D ボタンは、親の Streamlit リンクボタン（?view= を切り替える
  // 実リンク）が同じ位置に重なる。iframe 内の同じボタンは重なりを避けて隠す。
  if (!document.getElementById('ei-hide-view-btn')) {
    var css = document.createElement('style');
    css.id = 'ei-hide-view-btn';
    css.textContent = '#demoBar a[data-view]{visibility:hidden !important;pointer-events:none !important}';
    (document.head || document.documentElement).appendChild(css);
  }
  document.addEventListener('click', function(ev){
    try {
      var a = ev.target && ev.target.closest && ev.target.closest('a[data-view]');
      if (!a) return;
      ev.preventDefault();
    } catch(e){}
  }, true);
})();
</script>
"""
html = html + RUNTIME

# ===== 親側の制御スクリプト（切替・読み込み中の全画面表示） =====
splash_body = read_splash_body()
KICK = """
<script>
(function(){
  var WANT = __WANT__;        // 切り替え先（無ければ null）
  var DO_NAV = __DO_NAV__;    // この描画で親 URL を ?view= に合わせるか
  var MIN = __MIN__, MAX = __MAX__;
  var doc;
  try { doc = window.parent.document; } catch (e) { doc = document; }

  function splash(){
    var el = doc.getElementById("ei-splash");
    if (el) { el.style.display = "flex"; el.style.opacity = "1"; return el; }
    if (!doc.body) return null;
    var stl = doc.createElement("style");
    stl.textContent = [
      "#ei-splash{position:fixed;inset:0;z-index:2147483000;display:flex;align-items:center;justify-content:center;",
      "background:#f4f6f9;color:#101826;font-family:Inter,Hiragino Sans,'Noto Sans JP',system-ui,sans-serif}",
      "@media (prefers-color-scheme: dark){#ei-splash{background:#0b1017;color:#e9eff7}}",
      "#ei-splash .wrap{width:min(360px,82vw);text-align:center}",
      "#ei-splash .spinner{width:28px;height:28px;margin:0 auto 14px;border-radius:50%;",
      "border:3px solid rgba(127,127,127,.25);border-top-color:#1f6feb;animation:eiSpin .9s linear infinite}",
      "#ei-splash .bar{height:6px;border-radius:999px;background:rgba(127,127,127,.22);overflow:hidden;margin-top:26px}",
      "#ei-splash .bar i{display:block;height:100%;width:38%;border-radius:999px;background:#1f6feb;",
      "animation:eiSlide 1.15s cubic-bezier(.45,.05,.35,1) infinite}",
      "#ei-splash .brand{font-size:19px;font-weight:700}",
      "#ei-splash .sub{font-size:12px;opacity:.7;margin-top:2px}",
      "#ei-splash .msg{font-size:12px;opacity:.7;margin-top:12px}",
      "#ei-splash .skip{margin-top:18px;font-size:12px;opacity:.7;text-decoration:underline;",
      "cursor:pointer;background:none;border:none;font-family:inherit;color:inherit}",
      "@keyframes eiSpin{to{transform:rotate(360deg)}}",
      "@keyframes eiSlide{0%{transform:translateX(-110%)}100%{transform:translateX(300%)}}",
      "@media (prefers-reduced-motion: reduce){#ei-splash .spinner,#ei-splash .bar i{animation:none}#ei-splash .bar i{width:100%}}"
    ].join("");
    doc.head.appendChild(stl);
    el = doc.createElement("div");
    el.id = "ei-splash";
    el.innerHTML = __BODY__;
    doc.body.appendChild(el);
    return el;
  }
  function hide(){
    var el = doc.getElementById("ei-splash");
    if (!el) return;
    el.style.transition = "opacity .28s ease";
    el.style.opacity = "0";
    setTimeout(function(){ if (el && el.parentNode) el.parentNode.removeChild(el); }, 300);
  }
  function currentView(){
    try { return new URL(doc.location.href).searchParams.get("view") || "2d"; } catch (e) { return WANT; }
  }
  function navigate(view){
    try {
      var u = new URL(doc.location.href);
      if (u.searchParams.get("view") === view) return true;
      u.searchParams.set("view", view);
      doc.location.href = u.toString();
      return true;
    } catch (e) { return false; }
  }

  window.addEventListener("message", function(e){
    try {
      if (!e || !e.data || e.data.type !== "ei-view") return;
      var v = e.data.view;
      if (v !== "2d" && v !== "3d") return;
      splash();
      try { localStorage.setItem("ei-pending-view", v); } catch (err) {}
    } catch (err) {}
  });

  if (WANT) {
    splash();
    var t0 = Date.now();
    (function watch(){
      var cur = currentView();
      var dt = Date.now() - t0;
      if ((cur === WANT && dt > MIN) || dt > MAX) { hide(); return; }
      setTimeout(watch, 150);
    })();
  }
  if (DO_NAV && WANT) navigate(WANT);
  if (!WANT) {
    var pv = null;
    try { pv = localStorage.getItem("ei-pending-view"); } catch (e) {}
    if (pv === "2d" || pv === "3d") {
      try { localStorage.removeItem("ei-pending-view"); } catch (e) {}
      if (pv !== __BASE__) navigate(pv);
    }
  }
})();
</script>
""".replace("__WANT__", json.dumps(pending)) \
   .replace("__DO_NAV__", "true" if (pending and base != pending) else "false") \
   .replace("__MIN__", str(SPLASH_MIN_MS)) \
   .replace("__MAX__", str(SPLASH_MAX_MS)) \
   .replace("__BASE__", json.dumps(base)) \
   .replace("__BODY__", json.dumps(splash_body))

# ===== 本体（HTML を srcDoc で流し込む） =====
components.html(html, height=NOMINAL_HEIGHT, scrolling=False)

# 親側の制御は高さを確保して、本文の 100dvh 指定に巻き込まれないようにする
components.html(KICK, height=60)
