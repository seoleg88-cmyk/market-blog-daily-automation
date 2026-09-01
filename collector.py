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

    if data.empty or len(data) < 2:
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
    """Yahoo Finance에서 한국 지수 데이터를 가져옵니다."""

    print("=" * 60)
    print(f"[TEST] {name}")
    print(f"Yahoo Finance ticker: {ticker}")

    try:
        data = yf.download(
            ticker,
            period="5d",
            interval="1d",
            auto_adjust=False,
            progress=False
        )

        if data.empty:
            print(f"[FAIL] {name}: Yahoo Finance 데이터가 없습니다.")
            return None

        print(f"데이터 행 개수: {len(data)}")
        print(f"최근 데이터:\n{data.tail()}")

        if len(data) < 2:
            print(f"[FAIL] {name}: 비교할 이전 거래일 데이터가 없습니다.")
            return None

        latest = data.iloc[-1]
        previous = data.iloc[-2]

        close = float(latest["Close"].iloc[0])
        previous_close = float(previous["Close"].iloc[0])

        change = close - previous_close
        change_percent = (change / previous_close) * 100

        result = {
            "name": name,
            "date": data.index[-1].strftime("%Y-%m-%d"),
            "close": round(close, 2),
            "change": round(change, 2),
            "change_percent": round(change_percent, 2)
        }

        print(f"[SUCCESS] {name}: {result}")

        return result

    except Exception as e:
        print(f"[ERROR] {name}: {type(e).__name__}")
        print(f"[ERROR MESSAGE] {e}")

        return None


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
    "KOSPI": get_korea_data("^KS11", "코스피"),
    "KOSDAQ": get_korea_data("^KQ11", "코스닥")
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
# JSON 저장
# -----------------------------------

with open("market_data.json", "w", encoding="utf-8") as f:
    json.dump(
        result,
        f,
        ensure_ascii=False,
        indent=2
    )


# -----------------------------------
# GitHub Actions 로그 출력
# -----------------------------------

print("=" * 60)
print("시장 데이터 수집 완료")
print("=" * 60)

print(json.dumps(
    result,
    ensure_ascii=False,
    indent=2
))

print("=" * 60)
