"""抜管予報 — モックのロジック（Streamlit 版の共通部分）

HTML モックに出していた合成データと簡易スコアリングを、そのまま Python に移植したもの。
本番では predict() の中身を学習済みモデル（または API 呼び出し）に差し替える。
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

WINDOW_SEC = 86400          # 24時間
START_SEC = 8 * 3600 + 30 * 60   # 08:30 開始
ZOOM_MIN = 10               # チャートの最小表示範囲（分）
ZOOM_MAX = WINDOW_SEC // 60  # 1440 分

CASES: list[dict] = [
    {"id": "I20384", "name": "佐々木 康弘", "age": 78, "sex": "男性", "primary": "肺炎 / 敗血症", "icu_day": 5, "mv_hours": 96,
     "vitals": {"hr": 104, "rr": 27, "spo2": 93}, "vent": {"fio2": 45, "peep": 8},
     "gas": {"ph": 7.36, "pco2": 46, "lactate": 1.8}, "gcs": 11, "cough": "moderate", "secretion": "moderate"},
    {"id": "I20412", "name": "中村 由美", "age": 64, "sex": "女性", "primary": "食道癌術後", "icu_day": 4, "mv_hours": 78,
     "vitals": {"hr": 86, "rr": 19, "spo2": 98}, "vent": {"fio2": 30, "peep": 5},
     "gas": {"ph": 7.42, "pco2": 38, "lactate": 1.0}, "gcs": 14, "cough": "strong", "secretion": "none",
     "phase": "脱管済み", "note": "09:40 に抜管・翌日一般病棟へ転棟"},
    {"id": "I20455", "name": "山本 茂", "age": 81, "sex": "男性", "primary": "誤嚥性肺炎", "icu_day": 7, "mv_hours": 168,
     "vitals": {"hr": 118, "rr": 36, "spo2": 90}, "vent": {"fio2": 60, "peep": 10},
     "gas": {"ph": 7.29, "pco2": 54, "lactate": 2.9}, "gcs": 9, "cough": "weak", "secretion": "abundant"},
    {"id": "I20471", "name": "高橋 美咲", "age": 57, "sex": "女性", "primary": "急性心不全", "icu_day": 3, "mv_hours": 52,
     "vitals": {"hr": 92, "rr": 21, "spo2": 96}, "vent": {"fio2": 40, "peep": 6},
     "gas": {"ph": 7.38, "pco2": 44, "lactate": 1.4}, "gcs": 13, "cough": "moderate", "secretion": "moderate"},
    {"id": "I20503", "name": "小林 正一", "age": 70, "sex": "男性", "primary": "慢性閉塞性肺疾患の増悪", "icu_day": 6, "mv_hours": 132,
     "vitals": {"hr": 99, "rr": 25, "spo2": 94}, "vent": {"fio2": 38, "peep": 7},
     "gas": {"ph": 7.34, "pco2": 52, "lactate": 1.6}, "gcs": 12, "cough": "moderate", "secretion": "moderate"},
    {"id": "I20538", "name": "加藤 大輔", "age": 44, "sex": "男性", "primary": "交通外傷 / 骨盤骨折", "icu_day": 2, "mv_hours": 40,
     "vitals": {"hr": 88, "rr": 18, "spo2": 98}, "vent": {"fio2": 30, "peep": 5},
     "gas": {"ph": 7.43, "pco2": 37, "lactate": 1.1}, "gcs": 15, "cough": "strong", "secretion": "none"},
    {"id": "I20567", "name": "渡辺 理恵", "age": 66, "sex": "女性", "primary": "胆管炎 / 術後", "icu_day": 4, "mv_hours": 70,
     "vitals": {"hr": 95, "rr": 22, "spo2": 96}, "vent": {"fio2": 35, "peep": 6},
     "gas": {"ph": 7.40, "pco2": 41, "lactate": 1.3}, "gcs": 14, "cough": "strong", "secretion": "moderate"},
    {"id": "I20604", "name": "伊藤 すみ子", "age": 85, "sex": "女性", "primary": "肺炎", "icu_day": 8, "mv_hours": 190,
     "vitals": {"hr": 112, "rr": 32, "spo2": 91}, "vent": {"fio2": 55, "peep": 9},
     "gas": {"ph": 7.31, "pco2": 50, "lactate": 2.4}, "gcs": 10, "cough": "weak", "secretion": "abundant",
     "phase": "気管切開", "note": "長期人工呼吸のため気管切開へ移行"},
    {"id": "I20631", "name": "田中 慎太郎", "age": 52, "sex": "男性", "primary": "くも膜下出血", "icu_day": 3, "mv_hours": 62,
     "vitals": {"hr": 78, "rr": 16, "spo2": 98}, "vent": {"fio2": 30, "peep": 5},
     "gas": {"ph": 7.44, "pco2": 36, "lactate": 0.9}, "gcs": 13, "cough": "strong", "secretion": "none"},
    {"id": "I20678", "name": "松本 健太", "age": 73, "sex": "男性", "primary": "腹膜炎", "icu_day": 5, "mv_hours": 110,
     "vitals": {"hr": 106, "rr": 28, "spo2": 94}, "vent": {"fio2": 48, "peep": 8},
     "gas": {"ph": 7.35, "pco2": 47, "lactate": 2.1}, "gcs": 11, "cough": "moderate", "secretion": "abundant"},
]

COUGH_VALUE = {"strong": -0.25, "moderate": 0.10, "weak": 0.45}
COUGH_LABEL = {"strong": "強い", "moderate": "中等度", "weak": "弱い"}
SECRETION_VALUE = {"none": -0.15, "moderate": 0.10, "abundant": 0.38}
SECRETION_LABEL = {"none": "少ない", "moderate": "中等度", "abundant": "多い"}


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def _seed(key: str) -> float:
    """JS 側の seeded() と同じ FNV-1a で、患者ごとに揺らぎの位相を決める。"""
    h = 2166136261
    for ch in key:
        h ^= ord(ch)
        h = (h * 16777619) & 0xFFFFFFFF
    return ((h % 10000) / 10000) * math.pi * 2


def _wave(c: dict, key: str, d: float, period: float, amp: float) -> float:
    p = (d / period) * math.pi * 2
    return (math.sin(p + _seed(f"{c['id']}:{key}")) * amp
            + math.sin(p * 2.4 + _seed(f"{c['id']}:{key}b")) * amp * 0.45)


def snapshot_at(c: dict, d: float) -> dict:
    """d = 何時間前の記録か（0 = 現在、24 = 24時間前）。"""
    v = c["vitals"]
    return {
        "hr": round(v["hr"] + _wave(c, "hr", d, 3.2, 4.0) + d * 0.55),
        "rr": round(v["rr"] + _wave(c, "rr", d, 2.5, 1.6) + d * 0.16),
        "spo2": round(clamp(v["spo2"] + _wave(c, "spo2", d, 2.8, 1.0) - d * 0.16, 70, 100)),
        "peep": round(clamp(c["vent"]["peep"] + d * 0.45, 5, 20)),
        "fio2": round(clamp((c["vent"]["fio2"] + d * 0.8) / 5, 2, 20)) * 5,
        "ph": round(c["gas"]["ph"] - d * 0.002, 2),
        "pco2": round(c["gas"]["pco2"] + d * 0.22),
        "lactate": round(c["gas"]["lactate"] + d * 0.03, 1),
        "gcs": round(clamp(c["gcs"] + d * 0.18, 3, 15)),
        "mv_hours": round(max(0, c["mv_hours"] - d)),
    }


@dataclass
class Prediction:
    risk: float
    terms: list[tuple[str, float, str]] = field(default_factory=list)
    snap: dict = field(default_factory=dict)


def predict(c: dict, d: float) -> Prediction:
    """抜管失敗の確率（合成データ用の簡易ロジック。本番ではここを差し替える）。"""
    s = snapshot_at(c, d)
    terms = [
        ("年齢", (c["age"] - 65) * 0.012, f"{c['age']}歳"),
        ("人工呼吸期間", (s["mv_hours"] - 72) * 0.004, f"{s['mv_hours']}時間"),
        ("呼吸回数", (s["rr"] - 20) * 0.038, f"{s['rr']}回/分"),
        ("心拍数", (s["hr"] - 90) * 0.006, f"{s['hr']}bpm"),
        ("SpO2", (95 - s["spo2"]) * 0.085, f"{s['spo2']}%"),
        ("PEEP", (s["peep"] - 6) * 0.070, f"{s['peep']}cmH2O"),
        ("FiO2", (s["fio2"] - 35) * 0.012, f"{s['fio2']}%"),
        ("GCS", (14 - s["gcs"]) * 0.095, f"{s['gcs']}点"),
        ("PaCO2", (s["pco2"] - 40) * 0.012, f"{s['pco2']}mmHg"),
        ("pH", (7.40 - s["ph"]) * 2.0, f"{s['ph']:.2f}"),
        ("乳酸", (s["lactate"] - 1.2) * 0.22, f"{s['lactate']:.1f}mmol/L"),
        ("咳の強さ", COUGH_VALUE[c["cough"]], COUGH_LABEL[c["cough"]]),
        ("喀痰量", SECRETION_VALUE[c["secretion"]], SECRETION_LABEL[c["secretion"]]),
    ]
    z = -0.35 + sum(t[1] for t in terms)
    return Prediction(risk=1 / (1 + math.exp(-z)), terms=terms, snap=s)


def curve(d: float) -> float:
    """24時間前→現在の「改善度」。最新の記録ほど抜管準備が整っている想定。"""
    return 0.95 - 0.68 * (1 - d / 24)


def predict_risk(c: dict, d: float) -> float:
    """表示に使う最終的な失敗確率（predict() に時間経過ぶんの改善を掛ける）。"""
    p = predict(c, d)
    r = clamp(p.risk * curve(d), 0.02, 0.985)
    p.risk = r
    return r


RISK_LOW, RISK_HIGH = 0.25, 0.50


def is_intubated(c: dict) -> bool:
    """人工呼吸器を装着していない患者（抜管済み・気管切開）は計算対象外。"""
    return not c.get("phase")


def fail_cat(risk: float) -> tuple[str, str, str, str]:
    """(クラス, ラベル, 補足, 色) — 失敗確率で判定。低=緑 / 中程度=黄 / 高い=赤。"""
    if risk < RISK_LOW:
        return "good", "低い", "通常の観察で経過をみてよさそうです。", "#3fd39b"
    if risk < RISK_HIGH:
        return "mid", "中程度", "抜管前のチェックを入念に。再挿管の準備を確認してください。", "#ffcc8d"
    return "bad", "高い", "抜管可否を再評価し、上位者への相談を検討してください。", "#ff5a6e"


def ago_text(minutes: float) -> str:
    m = int(round(minutes))
    if m <= 0:
        return "現在"
    if m < 60:
        return f"{m}分前"
    h, mm = divmod(m, 60)
    return f"{h}時間{mm}分前" if mm else f"{h}時間前"


def span_text(minutes: float) -> str:
    m = int(round(minutes))
    if m >= 1440:
        return "24時間"
    if m >= 60:
        h = m / 60
        return f"{h:g}時間"
    return f"{m}分"


def clock_at(t_sec: float) -> str:
    total = int((START_SEC + round(t_sec)) % 86400)
    return f"{total // 3600:02d}:{(total // 60) % 60:02d}:{total % 60:02d}"
