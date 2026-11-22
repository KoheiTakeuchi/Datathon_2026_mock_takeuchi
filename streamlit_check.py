"""Streamlit 版（streamlit_app.py）の見た目と操作を確認する（headless Edge / Playwright）。

使い方:
  1) .\\.venv\\Scripts\\streamlit run streamlit_app.py --server.port 8599 --server.headless true
  2) .\\.venv\\Scripts\\python streamlit_check.py
スクリーンショットは .tmp/st_*.png に保存する。
"""
from __future__ import annotations

import io
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

URL = "http://localhost:8599/"
OUT = Path(__file__).with_name(".tmp")
OUT.mkdir(exist_ok=True)

results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = ""):
    results.append((name, ok, detail))


def wait_idle(page, ms=2500):
    page.wait_for_timeout(ms)


with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=True)
    page = browser.new_page(viewport={"width": 1520, "height": 1150}, color_scheme="light")
    errors: list[str] = []
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    page.goto(URL, wait_until="networkidle")
    wait_idle(page, 3500)

    body = page.inner_text("body")
    check("例外が出ていない", "Traceback" not in body)
    check("患者一覧が出る", "佐々木" in body)
    check("装着中の件数が出る", "装着中" in body)
    check("対象外の患者が出る", "対象外" in body)

    cards = page.get_by_role("button", name="選択", exact=True)
    check("選べる患者カード 8 件", cards.count() == 8, f"count={cards.count()}")
    page.screenshot(path=str(OUT / "st_1_initial.png"), full_page=True)

    # 患者カードをクリックして選択
    cards.nth(1).click()
    wait_idle(page, 3200)
    body = page.inner_text("body")
    check("カードクリックで患者が選べる", "山本 茂" in body.split("患者")[-1])
    check("危険度が出る", "危険度" in body)
    check("原因パネルが出る", "確率を上げている原因" in body)
    check("バイタルが出る", "バイタル" in body)
    page.screenshot(path=str(OUT / "st_2_selected.png"), full_page=True)

    # 連続で別の患者を選べる
    page.get_by_role("button", name="選択", exact=True).nth(3).click()
    wait_idle(page, 3200)
    check("別の患者に切り替えられる", "小林 正一" in page.inner_text("body").split("患者")[-1])

    # 失敗確率を計算モード
    page.get_by_role("button", name="失敗確率を計算").click()
    wait_idle(page, 2000)
    check("計算前は未計算表示", "計算ボタンを押してください" in page.inner_text("body"))
    page.get_by_role("button", name="この時刻で計算").click()
    wait_idle(page, 2500)
    body = page.inner_text("body")
    check("計算後に失敗確率の危険度が出る", "失敗の確率" in body and "危険度" in body)
    page.screenshot(path=str(OUT / "st_3_calc.png"), full_page=True)

    # 一時停止 → 再生
    play = page.get_by_role("button", name="▶❚❚")
    check("再生ボタンがある", play.count() >= 1, f"count={play.count()}")
    if play.count() >= 1:
        play.first.click()
        wait_idle(page, 2000)
        check("一時停止できる", "▶ 08:" in page.inner_text("body") or "▶" in page.inner_text("body"))

    check("コンソールエラーなし", not errors, " / ".join(errors[:3]))
    browser.close()

for name, ok, detail in results:
    print(("OK   " if ok else "NG   ") + name + (f"  ({detail})" if detail and not ok else ""))
ok_count = sum(1 for _, ok, _ in results if ok)
print(f"\n{ok_count}/{len(results)} OK")
sys.exit(0 if ok_count == len(results) else 1)
