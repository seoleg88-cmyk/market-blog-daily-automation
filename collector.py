import yfinance as yf
import json
from datetime import datetime
from zoneinfo import ZoneInfo


KST = ZoneInfo("Asia/Seoul")


def get_market_data(ticker, name, digits=2):
    """Yahoo Finance에서 시장 데이터를 가져옵니다."""

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
            print(f"[FAIL] {name}: 데이터가 없습니다.")
            return None

        if len(data) < 2:
            print(f"[FAIL] {name}: 이전 거래일 데이터가 없습니다.")
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
            "close": round(close, digits),
            "previous_close": round(previous_close, digits),
            "change": round(change, digits),
            "change_percent": round(change_percent, 2)
        }

        print(f"[SUCCESS] {name}")
        print(result)

        return result

    except Exception as e:
        print(f"[ERROR] {name}: {type(e).__name__}")
        print(f"[ERROR MESSAGE] {e}")
        return None


def main():

    collected_at = datetime.now(KST).isoformat()

    # ----------------------------------------
    # 미국 시장
    # ----------------------------------------

    us_market = {
        "S&P500": get_market_data("^GSPC", "S&P 500"),
        "NASDAQ": get_market_data("^IXIC", "NASDAQ"),
        "DOW": get_market_data("^DJI", "Dow Jones"),
        "VIX": get_market_data("^VIX", "VIX")
    }

    # ----------------------------------------
    # 한국 시장
    # ----------------------------------------

    korea_market = {
        "KOSPI": get_market_data("^KS11", "코스피"),
        "KOSDAQ": get_market_data("^KQ11", "코스닥")
    }

    # ----------------------------------------
    # 환율
    # ----------------------------------------

    exchange_rate = {
        "USD_KRW": get_market_data("KRW=X", "원/달러 환율", 4)
    }

    # ----------------------------------------
    # 미국 국채금리
    # ----------------------------------------

    bond_market = {
        "US10Y": get_market_data("^TNX", "미국 10년물 국채금리", 3),
        "US2Y": get_market_data("^IRX", "미국 단기 국채금리", 3)
    }

    # ----------------------------------------
    # 원자재
    # ----------------------------------------

    commodities = {
        "WTI": get_market_data("CL=F", "WTI 원유", 2),
        "BRENT": get_market_data("BZ=F", "브렌트유", 2),
        "GOLD": get_market_data("GC=F", "금", 2)
    }

    # ----------------------------------------
    # 최종 데이터
    # ----------------------------------------

    result = {
        "collected_at": collected_at,
        "us_market": us_market,
        "korea_market": korea_market,
        "exchange_rate": exchange_rate,
        "bond_market": bond_market,
        "commodities": commodities
    }

    print("=" * 60)
    print("시장 데이터 수집 완료")
    print("=" * 60)

    print(json.dumps(result, ensure_ascii=False, indent=2))

    # JSON 파일 저장
    with open("market_data.json", "w", encoding="utf-8") as f:
        json.dump(
            result,
            f,
            ensure_ascii=False,
            indent=2
        )


if __name__ == "__main__":
    main()
