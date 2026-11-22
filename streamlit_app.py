"""抜管予報 — Streamlit 版

構成は HTML モック（extubation_risk_mock.html）と同じ:
  左: 患者一覧（検索・確率つきカード）
  右: 患者情報 / 見込み（成功率トレンド or 失敗確率を計算） / 推移チャート・原因 / バイタル
  上: デモ帯（倍速・時刻スライダー・時刻表示）
配色は HTML モックと同じ 2 パターンをもち、既定は端末のダークモード設定に従う。
"""
from __future__ import annotations

import html as H
import time
from pathlib import Path

import streamlit as st

import mock_data as M

st.set_page_config(page_title="抜管予報", layout="wide", initial_sidebar_state="collapsed")

# ===== スプラッシュ（起動時と、患者を選んでいるときの画面更新に表示） =====
_SPLASH_FILE = Path(__file__).with_name("splash.html")


@st.cache_resource
def splash_template() -> str:
    html = _SPLASH_FILE.read_text(encoding="utf-8")
    return html.split("<body>", 1)[1].split("</body>", 1)[0]


def _kick_boot():
    """当セッションで最初の描画なら、スプラッシュを出してから本体を描く。"""
    if st.session_state.get("_booted"):
        return
    st.session_state["_booted"] = True
    st.markdown(
        "<style>html,body{overflow:hidden !important}"
        "#ei-splash{position:fixed;inset:0;z-index:99999;display:flex;align-items:center;"
        "justify-content:center;background:#f4f6f9;color:#101826;"
        'font-family:"Inter","Hiragino Sans","Noto Sans JP",system-ui,sans-serif}'
        "#ei-splash .wrap{text-align:center}"
        "#ei-splash .spinner{width:30px;height:30px;margin:0 auto 14px;border-radius:50%;"
        "border:3px solid #eef1f6;border-top-color:#1f6feb;animation:eis 0.9s linear infinite}"
        "#ei-splash .brand{font-size:19px;font-weight:700}"
        "#ei-splash .sub{font-size:12px;color:#5b6b80;margin-top:2px}"
        "@keyframes eis{to{transform:rotate(360deg)}}"
        "@media (prefers-color-scheme:dark){#ei-splash{background:#0b1017;color:#e9eff7}"
        "#ei-splash .spinner{border-color:#1b2737;border-top-color:#61a8ff}"
        "#ei-splash .sub{color:#8d9cb2}"
        "html,body{background:#0b1017 !important}}"
        "</style>"
        f'<div id="ei-splash">{splash_template()}</div>',
        unsafe_allow_html=True,
    )
    time.sleep(0.5)
    st.markdown(
        '<script>(function(){var s=document.getElementById("ei-splash");if(!s)return;'
        'var d=document.getElementById("ei-data");'
        'if(d&&(d.innerText||"").indexOf("ei-ready")>=0){s.parentNode.removeChild(s);return;}'
        's.style.transition="opacity .3s ease";s.style.opacity="0";'
        'setTimeout(function(){s.parentNode.removeChild(s);},320);})();</script>'
        '<span id="ei-data" style="display:none">ei-ready</span>',
        unsafe_allow_html=True,
    )

# ===== 配色（HTML モックの :root / html[data-theme="dark"] と同じ値） =====
CSS = """
<style>
:root{
  --bg:#f4f6f9; --panel:#ffffff; --panel-2:#f9fafc; --ink:#101826; --sub:#5b6b80;
  --line:#e3e8ef; --blue:#1f6feb; --blue-soft:#eaf1fe; --green:#0f8a5f;
  --green-soft:#e6f6ee; --amber:#a8770a; --amber-soft:#fff3e2; --red:#c93747;
  --red-soft:#fdecee; --strip:#ffffff; --track:#eef1f6;
  --shadow:0 1px 2px rgba(16,24,38,.06),0 8px 24px rgba(16,24,38,.06); --radius:14px;
}
@media (prefers-color-scheme: dark){
  :root{
    --bg:#0b1017; --panel:#121926; --panel-2:#0f1622; --ink:#e9eff7; --sub:#8d9cb2;
    --line:#223044; --blue:#61a8ff; --blue-soft:#13263f; --green:#3fd39b;
    --green-soft:#0f2b23; --amber:#ffcc8d; --amber-soft:#33260f; --red:#ff7d8e;
    --red-soft:#301620; --strip:#0e1622; --track:#1b2737;
    --shadow:0 1px 2px rgba(0,0,0,.4),0 10px 30px rgba(0,0,0,.35);
  }
}
/* テーマ切替ボタン: 選んだテーマを強制する（既定は端末設定に従う） */
html.ei-light{
  --bg:#f4f6f9; --panel:#ffffff; --panel-2:#f9fafc; --ink:#101826; --sub:#5b6b80;
  --line:#e3e8ef; --blue:#1f6feb; --blue-soft:#eaf1fe; --green:#0f8a5f;
  --green-soft:#e6f6ee; --amber:#a8770a; --amber-soft:#fff3e2; --red:#c93747;
  --red-soft:#fdecee; --strip:#ffffff; --track:#eef1f6;
  --shadow:0 1px 2px rgba(16,24,38,.06),0 8px 24px rgba(16,24,38,.06);
}
html.ei-dark{
  --bg:#0b1017; --panel:#121926; --panel-2:#0f1622; --ink:#e9eff7; --sub:#8d9cb2;
  --line:#223044; --blue:#61a8ff; --blue-soft:#13263f; --green:#3fd39b;
  --green-soft:#0f2b23; --amber:#ffcc8d; --amber-soft:#33260f; --red:#ff7d8e;
  --red-soft:#301620; --strip:#0e1622; --track:#1b2737;
  --shadow:0 1px 2px rgba(0,0,0,.4),0 10px 30px rgba(0,0,0,.35);
}
/* Streamlit 既定の配色も同じ変数から引く */
.stApp, [data-testid="stAppViewContainer"]{background:var(--bg) !important;color:var(--ink)}
.block-container{padding-top:.7rem;padding-bottom:1rem;max-width:1520px}
#MainMenu, footer, header{visibility:hidden}
[data-testid="stSidebar"]{display:none}
[data-testid="stDecoration"]{display:none}
[data-testid="stToolbar"]{right:8px}
h1,h2,h3,h4,p,label,span{color:inherit}
.stMarkdown p{margin:0}

/* Streamlit 部品の見た目をモックに寄せる */
div[data-testid="stTextInput"] input,
div[data-testid="stNumberInput"] input{
  background:var(--panel) !important;color:var(--ink) !important;
  border:1px solid var(--line) !important;border-radius:11px !important}
div[data-testid="stTextInput"] input::placeholder{color:var(--sub)}
button[kind="secondary"], button[kind="primary"],
div[data-testid="stBaseButton-secondary"], div[data-testid="stBaseButton-primary"],
div[data-testid="stBaseButton-secondaryFormSubmit"]{
  border-radius:10px !important;font-weight:600 !important}
button[kind="secondary"], div[data-testid="stBaseButton-secondary"]{
  background:var(--panel-2) !important;color:var(--ink) !important;border:1px solid var(--line) !important}
button[kind="primary"], div[data-testid="stBaseButton-primary"]{
  background:var(--blue) !important;color:#fff !important;border:1px solid var(--blue) !important}
button[disabled], button:disabled{
  background:var(--track) !important;color:var(--sub) !important;border-color:var(--line) !important;opacity:1 !important}
div[data-testid="stVerticalBlockBorderWrapper"]{
  background:var(--panel);border:1px solid var(--line) !important;border-radius:var(--radius) !important;
  box-shadow:var(--shadow)}
div[data-testid="stVerticalBlockBorderWrapper"] > div{border:none !important}
[data-testid="stSlider"] [data-baseweb="slider"] div[role="slider"]{background:var(--blue) !important}
[data-testid="stSlider"] [data-testid="stTickBar"]{display:none}
div[data-testid="stSelectbox"] > div{
  background:var(--panel) !important;border:1px solid var(--line) !important;border-radius:10px !important;color:var(--ink) !important}
div[data-testid="stSelectbox"] svg{fill:var(--sub)}
/* Streamlit 既定の赤（テーマ色）を青に寄せる */
[data-testid="stSlider"] [data-baseweb="slider"] div[role="slider"] ~ div,
[data-testid="stSlider"] [data-baseweb="slider"] > div > div{background:var(--blue) !important}
div[data-testid="stToggle"] [data-baseweb="checkbox"] div[data-checked="true"],
label[data-baseweb="checkbox"] span[aria-checked="true"]{background:var(--blue) !important;border-color:var(--blue) !important}
[data-testid="stSlider"] [data-testid="stThumbValue"]{display:none}
[data-testid="stSlider"] p{font-size:11px;color:var(--sub)}

/* 見出し・小見出し */
.ei-title{font-size:22px;font-weight:700;letter-spacing:.01em;margin:2px 0 0}
.ei-sub{font-size:12.5px;color:var(--sub);margin:0 0 10px}
.ei-card-title{font-size:11.5px;font-weight:650;letter-spacing:.04em;color:var(--sub);
  display:flex;justify-content:space-between;align-items:baseline;margin-bottom:8px}
.ei-quiet{font-size:11.5px;color:var(--sub)}

/* デモ帯 */
.ei-bar{display:flex;align-items:center;gap:10px;font-size:12px;color:var(--sub);
  background:var(--strip);border:1px solid var(--line);border-radius:12px;padding:4px 12px;margin-bottom:6px;min-height:44px}
.ei-clock{display:flex;align-items:baseline;gap:8px;justify-content:space-between;
  background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:6px 14px;box-shadow:var(--shadow);
  min-height:52px}
.ei-clock b{font-size:20px;font-variant-numeric:tabular-nums;letter-spacing:.02em}

/* 患者カード */
.ei-pcard{border:1px solid var(--line);background:var(--panel);border-radius:12px;padding:10px 12px 9px;
  box-shadow:var(--shadow)}
.ei-pcard.active{border-color:var(--blue);box-shadow:0 0 0 2px var(--blue-soft),var(--shadow)}
.ei-pcard.off{background:var(--panel-2);box-shadow:none}
.ei-pcard.off .nm, .ei-pcard.off .meta{color:var(--sub)}
.ei-pcard .top{display:flex;justify-content:space-between;align-items:baseline;gap:8px}
.ei-pcard .nm{font-size:14.5px;font-weight:700}
.ei-pcard .pc{font-size:23px;font-weight:700;font-variant-numeric:tabular-nums;line-height:1}
.ei-pcard .pc small{font-size:11px;color:var(--sub);margin-left:1px}
.ei-pcard .meta{font-size:11.5px;color:var(--sub);margin-top:2px}
.ei-pcard .foot{display:flex;justify-content:space-between;margin-top:5px;font-size:11px;font-weight:650}
.ei-pcard .bar{height:4px;border-radius:999px;background:var(--track);margin-top:5px;overflow:hidden}
.ei-pcard .bar i{display:block;height:100%;border-radius:999px}
.ei-pcard .off-tag{display:inline-block;border:1px solid var(--line);border-radius:999px;
  padding:1px 9px;font-size:10.5px;color:var(--sub);background:var(--track)}
/* 患者カード: ボックス全体をクリック可能に（中の透明ボタンを重ねる） */
div[class*="st-key-pcard-"]{position:relative;
  border-radius:12px;margin-bottom:8px;transition:box-shadow .15s}
div[class*="st-key-pcard-"]:hover{box-shadow:0 0 0 2px var(--blue-soft)}
div[class*="st-key-pcard-"] .ei-pcard{margin:0}
div[class*="st-key-pcard-"] div[data-testid="stElementContainer"]:has(.stButton){position:absolute;inset:0;z-index:4;margin:0}
div[class*="st-key-pcard-"] .stButton{height:100%;margin:0}
div[class*="st-key-pcard-"] .stButton button{width:100%;height:100%;min-height:0;
  opacity:0;cursor:pointer;background:transparent;border:none}
div[class*="st-key-pcard-"] .stButton button:focus-visible{opacity:0;
  box-shadow:inset 0 0 0 2px var(--blue)}
/* カーソルはポインタで選択できることを示す */
div[class*="st-key-pcard-"] .ei-pcard{cursor:pointer}

/* デモ帯（HTML モックの #demoBar） */
.ei-flag{font-size:11.5px;color:var(--sub);padding-top:8px;white-space:nowrap}
.ei-flag b{color:var(--blue);margin-right:4px}
.ei-pslabel{font-size:11.5px;color:var(--sub);padding-top:8px;text-align:center}
.ei-theme-toggle{display:flex;gap:2px;border:1px solid var(--line);border-radius:999px;
  padding:2px;background:var(--panel);width:fit-content;margin-top:4px}
/* 実際の 2 つのボタン（☀ / ☾）だけを丸く並べる */
div[class*="st-key-demobar"] .st-key-theme_light,
div[class*="st-key-demobar"] .st-key-theme_dark{display:inline-block;vertical-align:middle}

/* 患者情報 */
.ei-pat h2{margin:0;font-size:22px}
.ei-pat .sub{font-size:12.5px;color:var(--sub);margin-top:2px}
.ei-tags{display:flex;gap:6px;flex-wrap:wrap;margin-top:8px}
.ei-tag{font-size:11px;border:1px solid var(--line);border-radius:999px;padding:2px 10px;color:var(--sub)}

/* 見込みヒーロー */
.ei-hero-label{font-size:12px;font-weight:600;color:var(--sub)}
.ei-hero-num{font-size:clamp(56px,7vw,96px);font-weight:800;line-height:.98;letter-spacing:-.045em;
  font-variant-numeric:tabular-nums}
.ei-hero-num small{font-size:.36em;font-weight:700;margin-left:2px;color:var(--sub);letter-spacing:0}
.ei-good{color:var(--green)} .ei-mid{color:var(--amber)} .ei-bad{color:var(--red)}
.ei-pending{color:var(--sub);opacity:.6}
.ei-cat{display:inline-flex;align-items:center;gap:6px;border-radius:8px;padding:4px 11px;
  font-size:12.5px;font-weight:700}
.ei-cat::before{content:"";width:7px;height:7px;border-radius:50%;background:currentColor}
.ei-cat.good{background:var(--green-soft);color:var(--green)}
.ei-cat.mid{background:var(--amber-soft);color:var(--amber)}
.ei-cat.bad{background:var(--red-soft);color:var(--red)}
.ei-cat.neutral{background:var(--track);color:var(--sub)}
.ei-note{font-size:12px;color:var(--sub);line-height:1.75;margin-top:10px}
.ei-note b{color:var(--ink)}

/* 危険度ゲージ */
.ei-gauge{position:relative;height:7px;border-radius:999px;margin:12px 0 2px;
  background:linear-gradient(90deg,var(--green) 0%,var(--green) 25%,var(--amber) 25%,var(--amber) 50%,var(--red) 50%,var(--red) 100%);
  opacity:.9}
.ei-gauge i{position:absolute;top:-4px;width:15px;height:15px;border-radius:50%;
  background:var(--panel);border:3px solid var(--ink);transform:translateX(-50%)}
.ei-gauge-legend{display:flex;font-size:10.5px;color:var(--sub);margin-top:5px}
.ei-gauge-legend span{flex:1}
.ei-gauge-legend span:not(:first-child):not(:last-child){text-align:center}
.ei-gauge-legend span:last-child{text-align:right}

/* チャート */
.ei-chart-meta{display:flex;gap:16px;align-items:baseline;flex-wrap:wrap;font-size:11.5px;color:var(--sub);margin:6px 0 2px}
.ei-chart-meta b{color:var(--ink);font-size:15px;font-variant-numeric:tabular-nums}
.ei-axis{display:flex;justify-content:space-between;font-size:10.5px;color:var(--sub);margin-top:2px}
.ei-legend{display:flex;gap:12px;align-items:center;justify-content:flex-end;font-size:11px;color:var(--sub)}
.ei-legend i{display:inline-block;width:14px;height:0;border-top:2.5px solid var(--blue);margin-right:5px;
  vertical-align:middle}
.ei-legend i.tgt{border-top:2px dashed var(--green)}

/* チャートの拡大縮小（ホイール / ドラッグ。虫眼鏡マークを出す） */
div[class*="st-key-chartcard"]{position:relative}
div[class*="st-key-chartcard"] .stPlotlyChart,
div[class*="st-key-chartcard"] [data-testid="stVegaLiteChart"],
div[class*="st-key-chartcard"] [data-testid="stArrowVegaLiteChart"],
div[class*="st-key-chartcard"] canvas{cursor:zoom-in}
div[class*="st-key-chartcard"] .ei-zoom{position:absolute;right:10px;top:38px;z-index:3;
  display:none;align-items:center;gap:5px;background:var(--panel);border:1px solid var(--line);
  border-radius:999px;padding:3px 9px;font-size:11px;color:var(--sub);
  box-shadow:var(--shadow);pointer-events:none}
div[class*="st-key-chartcard"]:hover .ei-zoom{display:inline-flex}
.ei-zoom b{color:var(--ink)}
.ei-zoom svg{width:13px;height:13px;fill:none;stroke:currentColor;stroke-width:1.6}

/* 原因 */
.ei-cause{display:flex;flex-direction:column;gap:11px}
.ei-cause-row{display:grid;grid-template-columns:1fr auto;gap:3px 8px;font-size:13px}
.ei-cause-row .pt{color:var(--red);font-weight:700;font-size:12.5px;font-variant-numeric:tabular-nums}
.ei-cause-bar{grid-column:1/-1;height:4px;border-radius:999px;background:var(--track);overflow:hidden}
.ei-cause-bar i{display:block;height:100%;background:var(--red);border-radius:999px}

/* バイタル */
.ei-vitals{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}
.ei-vital{border:1px solid var(--line);border-radius:12px;padding:10px 13px;background:var(--panel-2)}
.ei-vital .k{display:flex;justify-content:space-between;font-size:11.5px;color:var(--sub)}
.ei-vital .v{font-size:30px;font-weight:700;margin-top:2px;font-variant-numeric:tabular-nums;line-height:1.1}
.ei-vital .v small{font-size:12px;color:var(--sub);margin-left:2px;font-weight:600}
.ei-vital .d{font-weight:700}
.ei-vital .d.bad{color:var(--red)} .ei-vital .d.good{color:var(--green)}
@media(max-width:900px){ .ei-vitals{grid-template-columns:repeat(1,1fr)} }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


# ===== 状態 =====
def init_state():
    ss = st.session_state
    ss.setdefault("case_id", None)
    ss.setdefault("t", 0)               # 再生位置（秒）。0 = 24時間前、86400 = 現在
    ss.setdefault("playing", True)
    ss.setdefault("speed", 1)
    ss.setdefault("mode", "trend")      # trend = 成功率トレンド / calc = ボタンで失敗確率
    ss.setdefault("calc_t", None)
    ss.setdefault("calc_for", None)
    ss.setdefault("span_min", M.ZOOM_MAX)
    ss.setdefault("view", "2d")
    ss.setdefault("theme", "auto")
    ss.setdefault("bar_collapsed", False)

init_state()
ss = st.session_state


def current_case():
    return next((c for c in M.CASES if c["id"] == ss.case_id), None)


def back_minutes() -> float:
    return max(0.0, (M.WINDOW_SEC - ss.t) / 60)


def cat_color(cat: str) -> str:
    return {"good": "var(--green)", "mid": "var(--amber)", "bad": "var(--red)"}[cat]


def render_header():
    """タイトルと時刻（HTML モックの見出し行と同じ並び）。"""
    t1, t2 = st.columns([2.2, 1])
    with t1:
        st.markdown('<div class="ei-title">抜管予報</div>'
                    '<p class="ei-sub">抜管後48時間以内の再挿管または死亡 — Team 3 / Datathon Japan 2026</p>',
                    unsafe_allow_html=True)
    with t2:
        state = ("再生中 ×%d" % ss.speed) if ss.playing else M.ago_text(back_minutes())
        st.markdown(f'<div class="ei-clock"><b>{"❚❚" if ss.playing else "▶"} {M.clock_at(ss.t)}</b>'
                    f'<span class="ei-quiet">{state}</span></div>', unsafe_allow_html=True)


def _apply_theme():
    """選んだテーマを CSS で強制し、ボタンの見た目も合わせる。"""
    theme = st.session_state.get("theme", "auto")
    light_sel = ".stApp, [data-testid=\"stAppViewContainer\"]"
    st.markdown(
        f'<style>{light_sel}{{background:var(--bg) !important;color:var(--ink)}}'
        f'.st-key-theme_light button, .st-key-theme_dark button{{border-radius:999px !important;'
        f'padding:2px 0 !important;font-size:15px !important;min-height:36px;'
        f'background:var(--panel) !important;color:var(--sub) !important;'
        f'border:1px solid var(--line) !important;box-shadow:none !important}}'
        f'</style>',
        unsafe_allow_html=True,
    )
    if theme not in ("light", "dark"):
        return
    if theme == "dark":
        vars_now = ("--bg:#0b1017;--panel:#121926;--panel-2:#0f1622;--ink:#e9eff7;--sub:#8d9cb2;"
                    "--line:#223044;--blue:#61a8ff;--blue-soft:#13263f;--green:#3fd39b;"
                    "--green-soft:#0f2b23;--amber:#ffcc8d;--amber-soft:#33260f;--red:#ff7d8e;"
                    "--red-soft:#301620;--strip:#0e1622;--track:#1b2737;"
                    "--shadow:0 1px 2px rgba(0,0,0,.4),0 10px 30px rgba(0,0,0,.35);"
                    "color-scheme:dark;background:#0b1017;color:#e9eff7")
        bg = "#0b1017"
    else:
        vars_now = ("--bg:#f4f6f9;--panel:#ffffff;--panel-2:#f9fafc;--ink:#101826;--sub:#5b6b80;"
                    "--line:#e3e8ef;--blue:#1f6feb;--blue-soft:#eaf1fe;--green:#0f8a5f;"
                    "--green-soft:#e6f6ee;--amber:#a8770a;--amber-soft:#fff3e2;--red:#c93747;"
                    "--red-soft:#fdecee;--strip:#ffffff;--track:#eef1f6;"
                    "--shadow:0 1px 2px rgba(16,24,38,.06),0 8px 24px rgba(16,24,38,.06);"
                    "color-scheme:light;background:#f4f6f9;color:#101826")
        bg = "#f4f6f9"
    # 配色は <style> で確定させる（テーマクラスが付いていない状態でも効くようにする）
    st.markdown(
        f'<style>:root{{{vars_now}}}'
        f'.stApp, [data-testid="stAppViewContainer"]{{background:{bg} !important;color:var(--ink)}}</style>',
        unsafe_allow_html=True,
    )


def render_demo_bar():
    """デモ帯（非表示切替・倍速・時刻・再生・3Dビュー・テーマ）。HTML モックの #demoBar に相当。"""
    _apply_theme()
    with st.container(key="demobar"):
        _demo_bar_inner()


def _demo_bar_inner():
    collapsed = bool(ss.get("bar_collapsed"))
    if collapsed:
        c1, c2, c3 = st.columns([0.85, 3.35, 2.4], gap="small")
        with c1:
            st.markdown('<div class="ei-flag"><b>デモ</b> 合成データ・仮ロジック</div>',
                        unsafe_allow_html=True)
        with c2:
            st.markdown(f'<div class="ei-quiet" style="padding-top:8px">'
                        f'{"❚❚" if ss.playing else "▶"} {M.clock_at(ss.t)}</div>',
                        unsafe_allow_html=True)
        with c3:
            t1, t2, t3, t4 = st.columns([1.25, 0.55, 0.55, 0.55])
            with t1:
                if st.button("表示", key="bar_toggle", use_container_width=True):
                    ss.bar_collapsed = False
                    st.rerun()
            with t2:
                if st.button("3D", key="to_3d_mini", use_container_width=True):
                    ss.view = "3d"
                    st.rerun()
            with t3:
                if st.button("☀", key="theme_light", help="ライト表示", use_container_width=True):
                    ss.theme = "light"
                    st.rerun()
            with t4:
                if st.button("☾", key="theme_dark", help="ダーク表示", use_container_width=True):
                    ss.theme = "dark"
                    st.rerun()
        return

    c1, c2, c3, c4, c5, c6, c7 = st.columns([1.6, 0.62, 1.0, 0.42, 2.0, 0.95, 1.0], gap="small")
    with c1:
        st.markdown('<div class="ei-flag"><b>デモ</b> 合成データ・仮ロジック</div>',
                    unsafe_allow_html=True)
        if st.button("非表示", key="bar_toggle", use_container_width=True):
            ss.bar_collapsed = True
            st.rerun()
    with c2:
        st.markdown('<div class="ei-pslabel">倍速</div>', unsafe_allow_html=True)
    with c3:
        speed = st.selectbox("倍速", [1, 100, 10000], index=[1, 100, 10000].index(ss.speed),
                             format_func=lambda v: f"×{v}" + ("（実時間）" if v == 1 else ""),
                             label_visibility="collapsed", key="speed_sel")
        if speed != ss.speed:
            ss.speed = speed
            st.rerun()
    with c4:
        if st.button("▶❚❚", key="play_btn", use_container_width=True, help="再生 / 一時停止"):
            ss.playing = not ss.playing
            st.rerun()
    with c5:
        st.markdown('<div class="ei-pslabel">時刻</div>', unsafe_allow_html=True)
        val = st.slider("時刻", 0, M.WINDOW_SEC, int(ss.t), step=60,
                        label_visibility="collapsed", key="t_slider", format="%d 秒")
        if abs(val - ss.t) >= 30 and val != st.session_state.get("_last_slider"):
            ss.t = float(val)
            ss._last_slider = val
            st.rerun()
    with c6:
        if st.button("3Dビュー", key="to_3d", use_container_width=True):
            ss.view = "3d"
            st.rerun()
    with c7:
        _theme_buttons()


@st.fragment
def _theme_buttons():
    """元モックと同じ「丸い枠に 2 つのアイコン」の切替。"""
    cur = ss.get("theme", "auto")
    a, b = st.columns([1, 1], gap="small")
    with a:
        if st.button("☀", key="theme_light", help="ライト表示", use_container_width=True):
            ss.theme = "light"
            st.rerun()
    with b:
        if st.button("☾", key="theme_dark", help="ダーク表示", use_container_width=True):
            ss.theme = "dark"
            st.rerun()
    st.markdown(
        f'<style>'
        f'.st-key-to_3d button{{border-radius:8px !important;background:var(--panel) !important;'
        f'color:var(--ink) !important;border:1px solid var(--line) !important;font-size:12px !important;'
        f'min-height:34px;height:34px}}'
        f'.st-key-bar_toggle button{{border-radius:8px !important;background:var(--panel) !important;'
        f'color:var(--ink) !important;border:1px solid var(--line) !important;font-size:12px !important;'
        f'min-height:30px;height:30px;padding:0 10px !important;margin-top:4px}}'
        f'.st-key-play_btn button{{border-radius:8px !important;background:var(--panel) !important;'
        f'color:var(--ink) !important;border:1px solid var(--line) !important;'
        f'min-height:34px;height:34px;margin-top:4px}}'
        f'.st-key-theme_light, .st-key-theme_dark{{margin-top:4px}}'
        f'.st-key-theme_light button, .st-key-theme_dark button{{'
        f'border-radius:999px !important;width:26px !important;height:26px !important;'
        f'min-height:26px !important;padding:0 !important;font-size:14px !important;'
        f'box-shadow:none !important;background:transparent !important;'
        f'border:1px solid var(--line) !important;'
        f'color:{("var(--blue)" if cur == "light" else "var(--sub)")} !important;'
        f'{"background:var(--blue-soft)" if cur == "light" else ""} !important}}'
        f'.st-key-theme_dark button{{'
        f'color:{("var(--blue)" if cur == "dark" else "var(--sub)")} !important;'
        f'{"background:var(--blue-soft)" if cur == "dark" else ""} !important}}'
        f'</style>',
        unsafe_allow_html=True,
    )


def render_3d():
    """3D ビュー（既存の 3D モックをそのまま 1 画面に表示する）。"""
    import streamlit.components.v1 as components

    html = (Path(__file__).with_name("static") / "extubation_risk_3d_mock.html").read_text(encoding="utf-8")
    # 自動回転は止め、ドラッグしたときだけ回るようにする
    html = html.replace(
        "if (state.autoRotate !== false && !dragging) state.yaw += dt*0.18;",
        "// 自動回転なし（手動ドラッグのみ）",
    )
    st.markdown('<style>[data-testid="stToolbar"]{display:none}'
                '.block-container{padding:0 !important;max-width:100% !important}'
                'header{display:none !important}</style>',
                unsafe_allow_html=True)
    components.html(html, height=980, scrolling=True)


def render_patient_list(now_min: float):
    n_on = sum(1 for c in M.CASES if M.is_intubated(c))
    st.markdown(f'<div class="ei-card-title"><span>患者</span><span>{len(M.CASES)}件・装着中 {n_on}件</span></div>',
                unsafe_allow_html=True)
    q = st.text_input("患者を検索", placeholder="ID・病名・年齢で検索",
                      label_visibility="collapsed", key="search")
    terms = [t for t in str(q or "").lower().split() if t]
    rows = []
    for c in M.CASES:
        hay = f"{c['id']} {c['name']} {c['primary']} {c['age']}歳 {c['sex']}".lower()
        if all(t in hay for t in terms):
            rows.append(c)
    if not rows:
        st.caption("該当する患者がありません")
        return

    for c in rows:
        on = M.is_intubated(c)
        active = c["id"] == ss.case_id
        if on:
            r = M.predict_risk(c, now_min / 60)
            cat, label, _, _ = M.fail_cat(r)
            color = cat_color(cat)
            head = f'<span class="pc" style="color:{color}">{r*100:.0f}<small>%</small></span>'
            foot = (f'<div class="foot"><span style="color:{color}">{label}</span>'
                    f'<span style="color:var(--sub);font-weight:600">失敗確率</span></div>'
                    f'<div class="bar"><i style="width:{max(3, min(100, r*100)):.0f}%;background:{color}"></i></div>')
            card_html = (
                f'<div class="top"><span class="nm">{H.escape(c["name"])}</span>{head}</div>'
                f'<div class="meta">{c["id"]}・{c["age"]}歳 {c["sex"]}・{H.escape(c["primary"])}</div>'
                f'{foot}'
            )
            # 患者カード全体をクリックして選択（カードの上に透明なボタンを重ねる）
            with st.container(key=f"pcard-{c['id']}"):
                st.markdown(f'<div class="ei-pcard{" active" if active else ""}">{card_html}</div>',
                            unsafe_allow_html=True)
                if st.button("選択", key=f"pick-{c['id']}", use_container_width=True):
                    ss.case_id = c["id"]
                    ss.calc_t = None
                    ss.calc_for = None
                    st.rerun()
        else:
            # 人工呼吸器を装着していない患者は、グレーアウトして選択できない
            foot = (f'<div class="foot"><span style="color:var(--sub)">{H.escape(c.get("phase", ""))}</span>'
                    f'<span style="color:var(--sub);font-weight:500">人工呼吸器なし</span></div>'
                    f'<div class="bar"><i style="width:100%;background:var(--line)"></i></div>')
            st.markdown(
                f'<div class="ei-pcard off">'
                f'<div class="top"><span class="nm">{H.escape(c["name"])}</span>'
                f'<span class="off-tag">対象外</span></div>'
                f'<div class="meta">{c["id"]}・{c["age"]}歳 {c["sex"]}・{H.escape(c["primary"])}</div>'
                f'{foot}</div>',
                unsafe_allow_html=True,
            )


def hero_view(c):
    if ss.mode == "trend":
        r = M.predict_risk(c, back_minutes() / 60)
        cat = M.fail_cat(r)
        return {"pending": False, "risk": r, "value": 1 - r, "bar": r,
                "label": "抜管成功率",
                "cat": f"成功率 {1-r*100:.1f}% ・ 危険度 {cat[1]}",
                "note": (f'最新の記録（{M.clock_at(ss.t)}）から自動計算<br>'
                         f'失敗確率 <b>{r*100:.1f}%</b> ・ 記録は再生に合わせて更新')}
    if ss.calc_t is None or ss.calc_for != c["id"]:
        return {"pending": True, "risk": 0.0, "value": 0.0, "bar": 0.0,
                "label": "抜管失敗の確率",
                "cat": "計算ボタンを押してください",
                "note": "このモードでは、計算ボタンを押した時刻の失敗確率を表示します。<br>押すまで値は更新されません。"}
    d = (M.WINDOW_SEC - ss.calc_t) / 60
    r = M.predict_risk(c, d / 60)
    cat = M.fail_cat(r)
    ago = max(0, round((ss.t - ss.calc_t) / 60))
    ago_txt = f' ・ 現在より{M.ago_text(ago)}' if ago else ""
    return {"pending": False, "risk": r, "value": r, "bar": r,
            "label": "抜管失敗の確率",
            "cat": f"危険度 {cat[1]}（失敗の確率 {r*100:.1f}%）",
            "note": f'{cat[2]}<br>{M.clock_at(ss.calc_t)} 時点の記録で計算'
                    f'（成功率 <b>{(1-r)*100:.1f}%</b>）{ago_txt}'}


def render_hero(c):
    v = hero_view(c)
    cat = M.fail_cat(v["risk"])
    cls = "ei-pending" if v["pending"] else {"good": "ei-good", "mid": "ei-mid", "bad": "ei-bad"}[cat[0]]
    cat_cls = "neutral" if v["pending"] else cat[0]
    num = "--" if v["pending"] else f'{v["value"]*100:.1f}'

    left, right = st.columns([1.05, 1], gap="large")
    with left:
        st.markdown(
            f'<div class="ei-hero-label">{v["label"]}</div>'
            f'<div class="ei-hero-num {cls}">{num}<small>%</small></div>'
            f'<div class="ei-cat {cat_cls}">{H.escape(v["cat"])}</div>',
            unsafe_allow_html=True,
        )
    with right:
        if not v["pending"]:
            pos = max(0.0, min(100.0, v["bar"] * 100))
            st.markdown(
                f'<div style="height:12px"></div>'
                f'<div class="ei-gauge"><i style="left:{pos:.1f}%"></i></div>'
                f'<div class="ei-gauge-legend"><span>0% 低い</span><span>25% 中程度</span>'
                f'<span>50% 高い</span><span>100%</span></div>',
                unsafe_allow_html=True,
            )
        st.markdown(f'<div class="ei-note">{v["note"]}</div>', unsafe_allow_html=True)
    st.markdown('<div style="height:6px"></div>', unsafe_allow_html=True)


def chart_series(c, span_min):
    back = back_minutes()
    step = 1 if span_min <= 30 else 2 if span_min <= 120 else 5 if span_min <= 360 else 10
    xs, risks = [], []
    m = max(0, back - span_min)
    while m <= back + 0.5:
        xs.append(m)
        risks.append(M.predict_risk(c, m / 60))
        m += step
    if xs and abs(xs[-1] - back) > 0.5:
        xs.append(back)
        risks.append(M.predict_risk(c, back / 60))
    return xs, risks


def render_chart(c):
    import altair as alt
    import pandas as pd

    span = ss.span_min
    xs, risks = chart_series(c, span)
    if not xs:
        return
    trend = ss.mode == "trend"
    vals = [(1 - r) if trend else r for r in risks]
    back0, back_now = xs[0], xs[-1]

    target = 0.75 if trend else M.RISK_LOW          # 成功率75% / 失敗確率25%
    if trend:
        lo = max(0.0, min(vals) - 0.05)
        hi = 1.0
    else:
        lo = 0.0
        hi = max(0.4, min(1.0, max(vals) + 0.05))

    df = pd.DataFrame({"分": xs, "値": [v * 100 for v in vals]})
    x = alt.X("分:Q", scale=alt.Scale(domain=[back0, back_now], nice=False), axis=None)
    y_axis = alt.Axis(title=None, ticks=False, grid=True, gridColor="var(--line)",
                      gridOpacity=1, labelColor="var(--sub)", labelFontSize=10, format=".0f",
                      domain=False)
    y = alt.Y("値:Q", scale=alt.Scale(domain=[lo * 100, hi * 100], nice=False), axis=y_axis)

    layers = [
        alt.Chart(df).mark_area(color="var(--blue-soft)", line=False).encode(
            x=x, y=alt.Y("値:Q", scale=alt.Scale(domain=[lo * 100, hi * 100], nice=False), axis=None),
            y2=alt.datum(lo * 100)),
        alt.Chart(pd.DataFrame({"y": [target * 100]})).mark_rule(
            color="var(--green)", strokeDash=[5, 4], strokeWidth=1.4, opacity=.8).encode(y="y:Q"),
        alt.Chart(df).mark_line(color="var(--blue)", strokeWidth=2.2).encode(x=x, y=y),
        alt.Chart(df.tail(1)).mark_circle(color="var(--blue)", size=48, stroke="var(--panel)",
                                          strokeWidth=1.5).encode(x=x, y=y),
    ]
    if not trend and ss.calc_t is not None and ss.calc_for == c["id"]:
        mm = max(0.0, (M.WINDOW_SEC - ss.calc_t) / 60)
        if back0 - 0.5 <= mm <= back_now + 0.5:
            layers.insert(2, alt.Chart(pd.DataFrame({"x": [mm]})).mark_rule(
                color="var(--amber)", strokeDash=[3, 3], strokeWidth=1.4).encode(x="x:Q"))

    chart = alt.layer(*layers).properties(height=190).configure_view(stroke=None)
    st.altair_chart(chart, use_container_width=True)

    cur = vals[-1] * 100
    diff = (vals[-1] - vals[0]) * 100
    if diff > 0.05:
        dcolor = "var(--green)" if trend else "var(--red)"
    elif diff < -0.05:
        dcolor = "var(--red)" if trend else "var(--green)"
    else:
        dcolor = "var(--sub)"
    cur_label = "現在" if (trend or ss.calc_t is None) else "計算値"
    st.markdown(
        f'<div class="ei-chart-meta"><span>{cur_label} <b>{cur:.1f}</b>%</span>'
        f'<span>表示 <b>{M.span_text(span)}</b></span>'
        f'<span style="color:{dcolor}">{M.span_text(span)}で {diff:+.1f}pt</span></div>',
        unsafe_allow_html=True,
    )
    labels = []
    for i in range(5):
        back = span * (1 - i / 4)
        labels.append("現在" if back <= 0.5 else "-" + M.span_text(back))
    st.markdown('<div class="ei-axis">' + "".join(f"<span>{l}</span>" for l in labels) + "</div>",
                unsafe_allow_html=True)


def _chart_zoom_overlay():
    """チャートのカードに虫眼鏡マーク（と現在の表示範囲）を出す。"""
    import streamlit.components.v1 as components

    components.html(
        f"""<style>html,body{{margin:0;background:transparent;overflow:hidden}}
        .z{{display:flex;justify-content:flex-end;padding:0 2px;font-family:"Inter","Hiragino Sans",sans-serif}}
        .z span{{display:inline-flex;align-items:center;gap:5px;background:#ffffff;border:1px solid #e3e8ef;
          border-radius:999px;padding:2px 9px;font-size:11px;color:#5b6b80}}
        .z b{{color:#101826}}
        .z svg{{width:13px;height:13px;fill:none;stroke:#5b6b80;stroke-width:1.6}}</style>
        <div class="z"><span><svg viewBox="0 0 16 16"><circle cx="7" cy="7" r="4.6"/>
        <line x1="10.6" y1="10.6" x2="14" y2="14"/></svg>範囲 <b>{M.span_text(ss.span_min)}</b></span></div>""",
        height=30,
    )


def _chart_zoom_js():
    """チャート上でホイール/ドラッグすると表示範囲を変え、Streamlit のスライダーに反映する。"""
    import streamlit.components.v1 as components

    components.html(
        """<script>
        (function(){
          var MIN = 10, MAX = 1440;
          function clampSpan(v){ v = Math.round(v / 10) * 10; return Math.max(MIN, Math.min(MAX, v)); }
          function slider(){
            var wrap = window.parent.document.querySelector('.st-key-span');
            if (!wrap) return null;
            return wrap.querySelector('input[type="range"]') || wrap.querySelector('[role="slider"]');
          }
          var current = 0;
          function readCurrent(){
            var s = slider();
            if (!s) return current || 1440;
            var v = parseInt(s.getAttribute('aria-valuenow') || s.value || '0', 10);
            return v || current || 1440;
          }
          function apply(f){
            current = clampSpan(readCurrent() * f);
            if (current < 10 && f < 1) current = MIN;
            var wrap = window.parent.document.querySelector('.st-key-span');
            if (!wrap) return;
            var s = slider();
            var key = f > 1 ? 'ArrowRight' : 'ArrowLeft';
            var target = s || wrap.querySelector('[role="group"]') || wrap;
            var steps = Math.max(1, Math.round(Math.abs(current - readCurrent()) / 10)) || 1;
            for (var i = 0; i < steps; i++){
              target.dispatchEvent(new KeyboardEvent('keydown', {key:key, code:key, which:key==='ArrowRight'?39:37, bubbles:true, cancelable:true}));
            }
          }
          try {
            var doc = window.parent.document;
            var card = doc.querySelector('div[class*="st-key-chartcard-"]');
            if (!card || card.__eiZoom) return;
            card.__eiZoom = true;
            card.style.cursor = 'zoom-in';
            card.addEventListener('wheel', function(e){
              if (Math.abs(e.deltaY) > 0) { e.preventDefault(); apply(e.deltaY > 0 ? 1.25 : 1/1.25); }
            }, {passive:false});
            var x0 = null;
            card.addEventListener('mousedown', function(e){
              var chart = e.target.closest('canvas, svg, [data-testid="stVegaLiteChart"]');
              if (chart) x0 = e.clientX;
            });
            window.addEventListener('mouseup', function(){ x0 = null; });
            card.addEventListener('mousemove', function(e){
              if (x0 === null) return;
              var dx = e.clientX - x0;
              if (Math.abs(dx) > 40) { apply(dx > 0 ? 1/1.3 : 1.3); x0 = e.clientX; }
            });
          } catch(e){}
        })();
        </script>""",
        height=0,
    )


def render_cause(c):
    p = M.predict(c, back_minutes() / 60)
    p.risk = M.predict_risk(c, back_minutes() / 60)
    up = sorted([t for t in p.terms if t[1] > 0], key=lambda t: -t[1])[:4]
    if not up:
        st.markdown('<div class="ei-quiet">この時点で、失敗確率を上げている要因はありません。</div>',
                    unsafe_allow_html=True)
        return
    mx = max(t[1] for t in up)
    rows = "".join(
        f'<div class="ei-cause-row"><span>{lbl} <span class="ei-quiet">{det}</span></span>'
        f'<span class="pt">+{val:.2f}</span>'
        f'<span class="ei-cause-bar"><i style="width:{max(6, val / mx * 100):.0f}%"></i></span></div>'
        for lbl, val, det in up
    )
    st.markdown(f'<div class="ei-cause">{rows}</div>', unsafe_allow_html=True)


def render_vitals(c):
    d = back_minutes() / 60
    snap = M.snapshot_at(c, d)
    prev = M.snapshot_at(c, d + 5 / 60)

    def delta(cur, before, unit, invert):
        df = cur - before
        if abs(df) < 0.5:
            return f'<span class="d flat ei-quiet">±0{unit}</span>'
        bad = df > 0 if invert else df < 0
        return f'<span class="d {"bad" if bad else "good"}">{df:+.0f}{unit}</span>'

    items = [
        ("心拍数", snap["hr"], "bpm", delta(snap["hr"], prev["hr"], "", False)),
        ("呼吸回数", snap["rr"], "/分", delta(snap["rr"], prev["rr"], "", False)),
        ("SpO2", snap["spo2"], "%", delta(snap["spo2"], prev["spo2"], "%", True)),
    ]
    cards = "".join(
        f'<div class="ei-vital"><div class="k"><span>{k}</span>{dl}</div>'
        f'<div class="v">{v}<small>{u}</small></div></div>'
        for k, v, u, dl in items
    )
    st.markdown(f'<div class="ei-vitals">{cards}</div>', unsafe_allow_html=True)


def render_right(c, now_min: float):
    st.markdown(
        f'<div class="ei-pat"><h2>{H.escape(c["name"])}</h2>'
        f'<div class="sub">{c["id"]}・{c["age"]}歳 {c["sex"]}・{H.escape(c["primary"])}</div>'
        f'<div class="ei-tags"><span class="ei-tag">ICU {c["icu_day"]}日目</span>'
        f'<span class="ei-tag">人工呼吸 {M.snapshot_at(c, 0)["mv_hours"]}時間</span>'
        f'<span class="ei-tag">{M.clock_at(ss.t)} 時点の記録</span></div></div>',
        unsafe_allow_html=True,
    )

    with st.container(border=True):
        m1, m2, _sp, m3 = st.columns([1.15, 1.15, 0.9, 1.6])
        with m1:
            if st.button("成功率のトレンド", use_container_width=True, key="m-trend",
                         type="primary" if ss.mode == "trend" else "secondary"):
                ss.mode = "trend"
                st.rerun()
        with m2:
            if st.button("失敗確率を計算", use_container_width=True, key="m-calc",
                         type="primary" if ss.mode == "calc" else "secondary"):
                ss.mode = "calc"
                st.rerun()
        with m3:
            if ss.mode == "calc":
                done = ss.calc_t is not None and ss.calc_for == c["id"]
                if st.button("この時刻で再計算" if done else "この時刻で計算",
                             use_container_width=True, key="calc", type="primary"):
                    ss.calc_t = ss.t
                    ss.calc_for = c["id"]
                    st.rerun()
            else:
                st.markdown('<div class="ei-quiet" style="padding-top:9px;text-align:right">'
                            '最新の記録から自動計算（成功率）</div>', unsafe_allow_html=True)
        render_hero(c)

    ch, ca = st.columns([1.6, 1], gap="medium")
    with ch:
        with st.container(border=True, key=f"chartcard-{ss.mode}"):
            title = "成功率の推移" if ss.mode == "trend" else "失敗確率の推移"
            legend = ('<span><i></i>成功率</span><span><i class="tgt"></i>75%</span>' if ss.mode == "trend"
                      else '<span><i></i>失敗確率</span><span><i class="tgt"></i>25%</span>')
            st.markdown(f'<div class="ei-card-title"><span>{title}</span>'
                        f'<span class="ei-legend">{legend}</span></div>', unsafe_allow_html=True)
            # カードにカーソルを乗せると虫眼鏡が出て、そこから範囲を変えられる
            _chart_zoom_overlay()
            render_chart(c)
            z1, z2 = st.columns([3, 1])
            with z1:
                span = st.slider("表示範囲（分）", M.ZOOM_MIN, M.ZOOM_MAX, int(ss.span_min),
                                 step=10, key="span", format="%d 分", label_visibility="collapsed")
                if span != ss.span_min:
                    ss.span_min = span
            with z2:
                if st.button("24h に戻す", use_container_width=True, key="span-reset"):
                    ss.span_min = M.ZOOM_MAX
                    st.rerun()
            st.markdown(_chart_zoom_js(), unsafe_allow_html=True)
    with ca:
        with st.container(border=True):
            st.markdown('<div class="ei-card-title"><span>確率を上げている原因</span>'
                        '<span>寄与の大きい順</span></div>', unsafe_allow_html=True)
            render_cause(c)

    with st.container(border=True):
        st.markdown(f'<div class="ei-card-title"><span>バイタル</span>'
                    f'<span>{M.clock_at(ss.t)} の値（差は5分前比）</span></div>', unsafe_allow_html=True)
        render_vitals(c)


def render_all():
    c = current_case()
    if c and not M.is_intubated(c):
        ss.case_id = None
        c = None
    if ss.get("view") == "3d":
        render_3d()
        return
    render_header()
    st.markdown('<div style="height:6px"></div>', unsafe_allow_html=True)
    render_demo_bar()
    now_min = back_minutes()

    left, right = st.columns([1, 3.35], gap="large")
    with left:
        with st.container(border=True):
            render_patient_list(now_min)
    with right:
        if not c:
            st.markdown('<div class="ei-quiet" style="padding:24px 4px;font-size:14px;color:var(--ink)">'
                        '<b>患者を選んでください</b><br>'
                        '<span class="ei-quiet" style="font-size:12.5px">左のリストから患者を選ぶと、'
                        'その時点の抜管失敗の確率と原因が表示されます。<br>'
                        'グレーの患者（抜管済み・気管切開）は人工呼吸器を装着していないため対象外です。</span></div>',
                        unsafe_allow_html=True)
        else:
            render_right(c, now_min)


render_all()

# ===== 再生 =====
if ss.playing:
    time.sleep(0.35)
    ss.t = ss.t + 0.35 * ss.speed
    if ss.t >= M.WINDOW_SEC:
        ss.t = 0.0
    st.rerun()
