# -*- coding: utf-8 -*-
"""患者選択が壊れていないかを毎回確認するスモークテスト（追加パッケージ不要）。

やること:
  1. 各HTMLの <script> を JS エンジンで構文チェック（重複宣言などを検出）
  2. 主要な要素IDがHTMLに存在するか確認
  3. 患者カードの選択処理（クリック→選択状態）が配線されているか確認
  4. headless Edge があれば、実際にカードをクリックして選択が変わったか確認

使い方（このフォルダで）:
    python smoke_test.py            # 1-3 を実行
    python smoke_test.py --browser  # 4 も実行（Edge が必要）

終了コード 0 = 全部OK / 1 = 失敗あり
"""
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
FILES = ["extubation_risk_mock.html", "extubation_risk_3d_mock.html"]

REQUIRED_IDS = {
    "extubation_risk_mock.html": ["patList", "patSearch", "chartSvg", "chartAxis"],
    "extubation_risk_3d_mock.html": ["patList", "patSearch", "scene", "hud"],
}

EDGE_CANDIDATES = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]

failures = []
checks = 0


def check(ok, label, detail=""):
    global checks
    checks += 1
    if ok:
        print(f"[OK]   {label}")
    else:
        print(f"[FAIL] {label}" + (f"  -> {detail}" if detail else ""))
        failures.append(label)


def find_node():
    node = shutil.which("node")
    if node:
        return node
    for p in (
        r"C:\Program Files\nodejs\node.exe",
        r"C:\Program Files (x86)\nodejs\node.exe",
    ):
        if Path(p).exists():
            return p
    return None


def find_edge():
    for p in EDGE_CANDIDATES:
        if Path(p).exists():
            return p
    return shutil.which("msedge")


def syntax_check(node, src_path):
    try:
        r = subprocess.run(
            [node, "--check", str(src_path)],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60,
        )
    except Exception as e:  # noqa: BLE001
        return False, f"node実行に失敗: {e}"
    out = (r.stderr or r.stdout or "").strip()
    if r.returncode == 0:
        return True, ""
    return False, out.splitlines()[0] if out else "syntax error"


BROWSER_RUNNER = """<!doctype html><meta charset="utf-8"><title>pending</title>
<iframe id="f" style="width:1100px;height:760px;border:0"></iframe>
<script>
(function(){
  const file = __FILE__;
  const fr = document.getElementById("f");
  fr.src = file + "?PLAYQ";
  window.addEventListener("load", function(){
    setTimeout(function(){
      const d = fr.contentDocument;
      const start = d.getElementById("startBtn");
      if (start) start.click();
      setTimeout(function(){
        const cards = Array.prototype.slice.call(d.querySelectorAll("#patList .pat-card:not(.off)"));
        if (cards.length < 2){ document.title = "RESULT:" + file + ":FAIL:cards=" + cards.length; return; }
        const target = cards[cards.length - 1];
        const rect = target.getBoundingClientRect();
        const hitAtStart = d.elementFromPoint(
          Math.round(rect.left + rect.width / 2),
          Math.round(rect.top + rect.height / 2)
        );
        const hitName = hitAtStart ? (hitAtStart.className && hitAtStart.className.baseVal !== undefined
          ? hitAtStart.className.baseVal : hitAtStart.className) || hitAtStart.tagName : "NULL";
        // 押下したまま再生中に何フレームか描画させ、同じ要素が残っているか確認する
        target.dispatchEvent(new MouseEvent("pointerdown", {bubbles:true}));
        setTimeout(function(){
          const stillThere = d.contains(target);
          target.dispatchEvent(new MouseEvent("pointerup", {bubbles:true}));
          target.click();
          setTimeout(function(){
            const on = Array.prototype.slice.call(d.querySelectorAll("#patList .pat-card"))
              .filter(function(e){ return e.getAttribute("aria-pressed") === "true"; }).length;
            const ctx = d.querySelector(".main-col .pat-head") || d.getElementById("hudName");
            const shown = (ctx ? ctx.textContent : "").replace(/\\s+/g, " ").trim();
            const ok = on === 1 && shown && stillThere &&
              (PLAYING || (d.getElementById("emptyPanel") ? d.getElementById("emptyPanel").hidden : true));
            document.title = "RESULT:" + file + (ok ? ":PASS:" : ":FAIL:") +
              "selected=" + on + ";survivesRerender=" + stillThere + ";shown=" + shown.slice(0, 12);
          }, 500);
        }, 900);
      }, 900);
    }, 2200);
  });
})();
</script>
"""


def browser_check(edge, name):
    work = Path(tempfile.mkdtemp(prefix="ei_smoke_"))
    try:
        src = HERE / name
        work.joinpath(name).write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
        runner = work.joinpath("runner.html")
        runner.write_text(
            BROWSER_RUNNER.replace("__FILE__", json.dumps(name))
            .replace("?PLAYQ", "")
            .replace("PLAYING", "false"),
            encoding="utf-8",
        )
        url = runner.as_uri()
        # 再生中（=毎フレーム再描画）でも押下中のカードが破棄されないことを見る版
        runner_playing = work.joinpath("runner_playing.html")
        runner_playing.write_text(
            BROWSER_RUNNER.replace("__FILE__", json.dumps(name))
            .replace("?PLAYQ", "?pause=0")
            .replace("PLAYING", "true"),
            encoding="utf-8",
        )
        url_playing = runner_playing.as_uri()
        # 3Dは初回描画が重いので時間切れになりやすい。最大3回まで試す。
        last = "結果が取得できませんでした（ブラウザ起動失敗の可能性）"
        for target_url, playing in ((url, False), (url_playing, True)):
            ok = False
            for _ in range(3):
                r = subprocess.run(
                    [edge, "--headless=new", "--disable-gpu", "--allow-file-access-from-files",
                     "--virtual-time-budget=25000", "--window-size=1150,800", "--dump-dom", target_url],
                    capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180,
                )
                m = re.search(r"RESULT:([^:<]+):(PASS|FAIL):([^<]*)", r.stdout or "")
                if not m:
                    last = "結果が取得できませんでした（描画が間に合わなかった可能性）"
                    continue
                last = m.group(3).strip()
                ok = m.group(2) == "PASS"
                if ok:
                    break
            if not ok:
                return False, ("再生中: " if playing else "") + last
        return True, last
    except Exception as e:  # noqa: BLE001
        return False, f"ブラウザ実行に失敗: {e}"
    finally:
        shutil.rmtree(work, ignore_errors=True)


def main():
    want_browser = "--browser" in sys.argv
    node = find_node()
    if node is None:
        print("[SKIP] node が見つからないため構文チェックは省略します")
    edge = find_edge() if want_browser else None
    if want_browser and edge is None:
        print("[SKIP] Edge が見つからないためブラウザでの確認は省略します")

    for name in FILES:
        path = HERE / name
        check(path.exists(), f"{name}: ファイルが存在")
        if not path.exists():
            continue
        html = path.read_text(encoding="utf-8")

        for el_id in REQUIRED_IDS[name]:
            check(f'id="{el_id}"' in html, f"{name}: #{el_id} が存在")

        # 患者カードのクリック配線
        # 2D: btn.addEventListener("click", ()=>{ ... if (!isIntubated(c)) return; state.caseId = c.id; ... })
        # 3D: btn.addEventListener("click", ()=> { if (isIntubated(c)) selectCase(c.id); })
        wired = re.search(r"pat-card", html) is not None and (
            re.search(r"selectCase\(c\.id\)", html) is not None
            or re.search(r'addEventListener\("click",\s*\(\)\s*=>\s*\{[^}]*state\.caseId', html) is not None
        )
        check(wired, f"{name}: 患者カードのクリックが選択処理につながっている")

        # インライン <script> の構文チェック
        scripts = re.findall(r"<script[^>]*>(.*?)</script>", html, flags=re.S)
        inline = "\n;\n".join(s for s in scripts if s.strip())
        if node is not None:
            tmp = Path(tempfile.mkdtemp(prefix="ei_syntax_")).joinpath("extracted.js")
            tmp.write_text(inline, encoding="utf-8")
            try:
                ok, detail = syntax_check(node, tmp)
            finally:
                shutil.rmtree(tmp.parent, ignore_errors=True)
            check(ok, f"{name}: JavaScript の構文が正しい", detail)

        if edge is not None:
            ok, detail = browser_check(edge, name)
            check(ok, f"{name}: 実際にカードをクリックして患者が切り替わる", detail)

    print()
    print(f"{checks - len(failures)}/{checks} OK")
    if failures:
        print("失敗:", ", ".join(failures))
        return 1
    print("患者選択まわりのスモークテスト: すべてOK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
