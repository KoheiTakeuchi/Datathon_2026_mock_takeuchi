# Datathon 2026 — 抜管失敗の確率モック（Team 3 / 竹内）

Datathon Japan 2026・Team 3 の「抜管失敗の確率」画面モック。HTML/CSS/JS の静的モックを Streamlit で配信するだけのアプリ。

- 2Dビュー: 患者を選ぶと、抜管失敗の確率と推移が主役で見える
- 3Dビュー: 確率の変動を立体で眺め、変化に合わせて関西弁ボイスが鳴る

## Streamlit Community Cloud で公開

1. <https://share.streamlit.io> → New app
2. Repository: `KoheiTakeuchi/Datathon_2026_mock_takeuchi` / Branch: `main` / Main file: `app.py`
3. Deploy

ローカルで動かす場合:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -m streamlit run app.py
```

HTML を直接ブラウザで開いても動きます（音声は最初のクリックで解禁）。

## 構成

```
app.py                         Streamlit エントリ
requirements.txt
extubation_risk_mock.html      2Dビュー
extubation_risk_3d_mock.html   3Dビュー
assets/voice/*.wav             関西弁ボイスパック（仕様: assets/voice/SPEC.md）
```

## URL パラメータ（HTML直開き時）

| パラメータ | 例 | 意味 |
|---|---|---|
| `case` | `?case=I20384` | 起動時にその患者を選ぶ |
| `t` | `?t=43200` | 再生位置（秒。0=24時間前の08:30、86400=現在の08:30） |
| `start` | `?start=now` | 現在の時刻から開始 |
| `go` | `?go=1`（3Dのみ） | 案内を出さずに再生開始 |

## 注意

- データはすべて合成。患者を特定できる情報は含みません。
- 予測値は画面確認用の仮ロジックです。診療判断には使用しないでください。
