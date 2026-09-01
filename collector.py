import json
from datetime import datetime, timezone, timedelta

import yfinance as yf
from pykrx import stock


# 한국 시간
KST = timezone(timedelta(hours=9))
now = datetime.now(KST)


def get_yahoo_data(ticker):
    """Yahoo Finance에서 최근 거래일 데이터를 가져옵니다."""
    data = yf.download(
        ticker,
        period="5d",
        interval="1d",
        auto_adjust=False,
        progress=False
    )

    if data.empty:
        return None

    row = data.iloc[-1]

    close = float(row["Close"].iloc[0])
    previous_close = float(data.iloc[-2]["Close"].iloc[0])

    change = close - previous_close
    change_percent = (change / previous_close) * 100

    return {
        "close": round(close, 4),
        "change": round(change, 4),
        "change_percent": round(change_percent, 2)
    }


def get_korea_data(ticker, name):
    """KRX에서 최근 거래일 데이터를 가져옵니다."""

    today = now.strftime("%Y%m%d")

    data = stock.get_market_ohlcv_by_date(
        today,
        today,
        ticker
    )

    # 오늘 데이터가 없으면 최근 10일에서 마지막 거래일을 찾습니다.
    if data.empty:
        start = (now - timedelta(days=10)).strftime("%Y%m%d")

        data = stock.get_market_ohlcv_by_date(
            start,
            today,
            ticker
        )

    if data.empty:
        return None

    row = data.iloc[-1]

    close = float(row["종가"])
    change_percent = float(row["등락률"])

    return {
        "name": name,
        "date": data.index[-1].strftime("%Y-%m-%d"),
        "close": round(close, 2),
        "change_percent": round(change_percent, 2)
    }


# -----------------------------------
# 미국 주요 지수
# -----------------------------------

us_market = {
    "S&P500": get_yahoo_data("^GSPC"),
    "NASDAQ": get_yahoo_data("^IXIC"),
    "DOW": get_yahoo_data("^DJI"),
    "VIX": get_yahoo_data("^VIX")
}


# -----------------------------------
# 국내 주요 지수
# -----------------------------------

korea_market = {
    "KOSPI": get_korea_data("1001", "코스피"),
    "KOSDAQ": get_korea_data("2001", "코스닥")
}


# -----------------------------------
# 결과 통합
# -----------------------------------

result = {
    "collected_at": now.isoformat(),
    "us_market": us_market,
    "korea_market": korea_market
}


# -----------------------------------
# JSON 파일 저장
# -----------------------------------

with open("market_data.json", "w", encoding="utf-8") as f:
    json.dump(
        result,
        f,
        ensure_ascii=False,
        indent=2
    )


# -----------------------------------
# GitHub Actions 로그에도 출력
# -----------------------------------

print("=" * 50)
print("시장 데이터 수집 완료")
print("=" * 50)

print(json.dumps(
    result,
    ensure_ascii=False,
    indent=2
))

print("=" * 50)
