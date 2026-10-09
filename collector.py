import yfinance as yf
import json
import re
import html
import requests
import pandas as pd
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from pykrx import stock


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

def get_fred_yield(series_id, name):
    """FRED에서 국채 수익률을 가져옵니다.
    Yahoo/yfinance에는 2년물 국채금리용 신뢰할 만한 티커가 없어(^IRX는 13주물, 2YY=F는 만기 지난 특정월물)
    2년물은 FRED의 DGS2 시계열을 사용합니다."""
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
    try:
        df = pd.read_csv(url)
        # FRED CSV 헤더가 'DATE' → 'observation_date'로 바뀐 적이 있어
        # 이름에 의존하지 않고 첫 번째 열=날짜, 두 번째 열=값으로 읽습니다.
        df = df.iloc[:, :2]
        df.columns = ["date", "value"]
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
        df = df.dropna(subset=["date"])
        df = df.dropna(subset=["value"]).tail(2)

        if len(df) < 2:
            print(f"[FAIL] {name}: 데이터가 부족합니다.")
            return None

        prev_row, latest_row = df.iloc[-2], df.iloc[-1]
        close = float(latest_row["value"])
        previous_close = float(prev_row["value"])
        change = close - previous_close
        change_percent = (change / previous_close) * 100

        result = {
            "name": name,
            "date": latest_row["date"].strftime("%Y-%m-%d"),
            "close": round(close, 3),
            "previous_close": round(previous_close, 3),
            "change": round(change, 3),
            "change_percent": round(change_percent, 2)
        }
        print(f"[SUCCESS] {name}")
        print(result)
        return result
    except Exception as e:
        print(f"[ERROR] {name}: {type(e).__name__}")
        print(f"[ERROR MESSAGE] {e}")
        return None


NAVER_FLOW_URL = (
    "https://finance.naver.com/sise/investorDealTrendDay.naver"
    "?bizdate={bizdate}&sosok={sosok}"
)

# 네이버 금융 시장 구분 코드 (01=코스피, 02=코스닥)
NAVER_SOSOK = {
    "KOSPI": "01",
    "KOSDAQ": "02"
}


def _cell_texts(row_html, tag):
    """<tr> 안의 <td>/<th> 텍스트를 순서대로 뽑습니다."""
    cells = re.findall(
        rf"<{tag}[^>]*>(.*?)</{tag}>",
        row_html,
        flags=re.S | re.I
    )
    return [
        html.unescape(re.sub(r"<[^>]+>", "", c)).strip()
        for c in cells
    ]


def _to_int(text):
    text = text.replace(",", "").replace("+", "").strip()
    if text in ("", "-"):
        return None
    return int(float(text))


def get_naver_investor_flow(market):
    """
    네이버 금융 '투자자별 매매동향(일별)'에서
    가장 최근 거래일의 투자자별 순매수 금액을 가져옵니다.

    단위: 억원 (양수=순매수, 음수=순매도)
    """

    print("=" * 60)
    print(f"[NAVER] {market} 투자자별 수급")

    bizdate = datetime.now(KST).strftime("%Y%m%d")
    url = NAVER_FLOW_URL.format(
        bizdate=bizdate,
        sosok=NAVER_SOSOK[market]
    )

    try:
        resp = requests.get(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/126.0 Safari/537.36"
                ),
                "Referer": "https://finance.naver.com/sise/sise_trans_style.naver"
            },
            timeout=15
        )
        resp.raise_for_status()
        resp.encoding = "euc-kr"
        page = resp.text

        rows = re.findall(r"<tr[^>]*>(.*?)</tr>", page, flags=re.S | re.I)

        # 헤더(th)에서 열 위치 찾기
        header = []
        for row in rows:
            header += _cell_texts(row, "th")
        print(f"[NAVER] 헤더: {header}")

        # 첫 번째 날짜 행(가장 최근 거래일) 찾기
        latest = None
        for row in rows:
            cells = _cell_texts(row, "td")
            if cells and re.fullmatch(r"\d{2}\.\d{2}\.\d{2}", cells[0]):
                latest = cells
                break

        if latest is None:
            print(f"[FAIL] {market}: 날짜 행을 찾지 못했습니다.")
            return None

        print(f"[NAVER] 최신 행: {latest}")

        # 열 순서: 날짜, 개인, 외국인, 기관계, (기관 세부...), 기타법인(마지막)
        if len(latest) < 5:
            print(f"[FAIL] {market}: 열 개수가 예상보다 적습니다.")
            return None

        yy, mm, dd = latest[0].split(".")
        trade_date = f"20{yy}-{mm}-{dd}"

        data = {
            "개인": _to_int(latest[1]),
            "외국인": _to_int(latest[2]),
            "기관합계": _to_int(latest[3]),
            "기타법인": _to_int(latest[-1])
        }

        # 헤더가 예상과 다르면 경고 (열 순서가 바뀌었을 가능성)
        for label in ["개인", "외국인", "기관", "기타법인"]:
            if header and not any(label in h for h in header):
                print(f"[WARNING] {market}: 헤더에 '{label}'이 없습니다. 열 순서 확인 필요")

        result = {
            "date": trade_date,
            "unit": "억원",
            "source": "naver",
            "data": data
        }

        print(f"[SUCCESS] {market} 투자자별 수급 (네이버)")
        print(result)
        return result

    except Exception as e:
        print(f"[ERROR] {market} 네이버 수급: {type(e).__name__}")
        print(f"[ERROR MESSAGE] {e}")
        return None


def get_investor_flow(market):
    """KRX(pykrx, 로그인 필요)로 투자자별 수급을 가져옵니다.

    네이버 금융 일별 수급 페이지(investorDealTrendDay)는
    2026-10 확인 결과 410(페이지 폐지)이라 더 이상 호출하지 않습니다.
    """

    result = get_krx_investor_flow_with_fallback(market)

    if result is not None:
        result["unit"] = "원"
        result["source"] = "krx"

    return result


def get_krx_investor_flow(market, date):
    """
    KRX에서 해당 시장의 투자자별 순매수 거래대금을 가져옵니다.

    시장:
    KOSPI / KOSDAQ

    투자자:
    개인 / 외국인 / 기관합계 / 기타법인

    단위:
    원
    """

    print("=" * 60)
    print(f"[TEST] {market} 투자자별 수급")
    print(f"조회일: {date}")

    investors = [
        "개인",
        "외국인",
        "기관합계",
        "기타법인"
    ]

    result = {}

    try:
        df = stock.get_market_trading_value_by_investor(
            date,
            date,
            market
        )

        if df is None or df.empty:
            print(f"[FAIL] {market}: 투자자별 수급 데이터가 없습니다.")
            return None

        print(f"[SUCCESS] {market}: 원본 데이터 조회 완료")
        print(df)

        for investor in investors:

            if investor not in df.index:
                print(f"[WARNING] {market}: {investor} 데이터가 없습니다.")
                result[investor] = None
                continue

            value = df.loc[investor, "순매수"]

            result[investor] = int(value)

        # 휴장일에는 KRX가 빈 표 대신 0으로 채운 표를 주는 경우가 있음
        # → 전부 0이면 데이터 없음으로 보고 전날로 넘어가게 함
        if all(not v for v in result.values()):
            print(f"[SKIP] {market}: {date} 수급이 전부 0 (휴장일로 판단)")
            return None

        print(f"[SUCCESS] {market} 투자자별 수급")
        print(result)

        return result

    except Exception as e:

        print(f"[ERROR] {market} 투자자별 수급")
        print(f"[ERROR TYPE] {type(e).__name__}")
        print(f"[ERROR MESSAGE] {e}")

        return None


def get_krx_investor_flow_with_fallback(market):
    """
    당일 데이터가 없을 경우 최근 거래일까지 최대 7일간 역추적합니다.

    한국 시장은 주말/공휴일 및 KRX 데이터 제공 시점 때문에
    당일 데이터가 바로 조회되지 않을 수 있습니다.
    """

    today = datetime.now(KST).date()

    for i in range(7):

        target_date = today - timedelta(days=i)
        date_str = target_date.strftime("%Y%m%d")

        print("=" * 60)
        print(f"[KRX] {market} 조회 시도: {date_str}")

        result = get_krx_investor_flow(
            market,
            date_str
        )

        if result is not None:

            return {
                "date": target_date.strftime("%Y-%m-%d"),
                "data": result
            }

    print(f"[FAIL] {market}: 최근 7일 동안 투자자 수급 데이터를 찾지 못했습니다.")

    return None


# ----------------------------------------
# 투자자별 순매수 상위 종목
# ----------------------------------------

TOP_N = 5


def _pick_column(df, keyword):
    """열 이름이 정확히 일치하지 않아도 keyword가 들어간 열을 찾습니다."""
    if keyword in df.columns:
        return keyword
    for col in df.columns:
        if keyword in str(col):
            return col
    return None


def get_top_net_purchases(market, investor, date):
    """
    특정 거래일에 해당 투자자가 가장 많이 순매수/순매도한 종목 상위 N개.

    단위: 원 (순매수거래대금)
    """

    print("=" * 60)
    print(f"[KRX] {market} {investor} 순매수 상위 종목 ({date})")

    try:
        df = stock.get_market_net_purchases_of_equities(
            date, date, market, investor
        )

        if df is None or df.empty:
            print(f"[FAIL] {market} {investor}: 데이터 없음")
            return None

        value_col = _pick_column(df, "순매수거래대금")
        name_col = _pick_column(df, "종목명")

        print(f"[KRX] 열 목록: {list(df.columns)}")

        if value_col is None:
            print(f"[FAIL] {market} {investor}: 순매수거래대금 열을 찾지 못함")
            return None

        df = df.sort_values(value_col, ascending=False)

        def rows(part):
            items = []
            for ticker, row in part.iterrows():
                items.append({
                    "ticker": str(ticker),
                    "name": str(row[name_col]) if name_col else str(ticker),
                    "amount": int(row[value_col])
                })
            return items

        buy = [x for x in rows(df.head(TOP_N)) if x["amount"] > 0]
        sell = [x for x in rows(df.tail(TOP_N).iloc[::-1]) if x["amount"] < 0]

        if not buy and not sell:
            print(f"[SKIP] {market} {investor}: 순매수/순매도가 전부 0")
            return None

        result = {"buy": buy, "sell": sell}
        print(f"[SUCCESS] {market} {investor} 순매수 상위")
        print(result)
        return result

    except Exception as e:
        print(f"[ERROR] {market} {investor} 순매수 상위: {type(e).__name__}")
        print(f"[ERROR MESSAGE] {e}")
        return None


def get_top_net_purchases_all(trade_date):
    """코스피·코스닥 × 외국인·기관합계 순매수/순매도 상위 종목."""

    if trade_date is None:
        return None

    date = trade_date.replace("-", "")

    result = {
        "date": trade_date,
        "unit": "원",
        "top_n": TOP_N
    }

    for market in ["KOSPI", "KOSDAQ"]:
        result[market] = {
            "외국인": get_top_net_purchases(market, "외국인", date),
            "기관합계": get_top_net_purchases(market, "기관합계", date)
        }

    return result


# ----------------------------------------
# 코스피 업종별 등락률
# ----------------------------------------

# 업종이 아닌 지수(규모별·테마·파생 등)는 제외
NON_SECTOR_KEYWORDS = [
    "코스피", "KOSPI", "KRX", "대형", "중형", "소형",
    "200", "100", "50", "배당", "우선주", "레버리지",
    "인버스", "TR", "밸류업", "ESG", "선물"
]


def _is_sector(name):
    return not any(k in name for k in NON_SECTOR_KEYWORDS)


def get_sector_performance(trade_date, kospi_change_percent):
    """
    코스피 업종지수별 하루 등락률.

    KRX '기간 등락률'은 조회 기간의 기준점 해석이 애매할 수 있어,
    코스피 지수 자체의 등락률이 야후 값과 맞는 조회 구간을 찾아
    그 구간의 업종 등락률을 사용합니다(자체 검증).
    """

    if trade_date is None:
        return None

    print("=" * 60)
    print(f"[KRX] 코스피 업종별 등락률 ({trade_date})")

    end = datetime.strptime(trade_date, "%Y-%m-%d").date()

    # 같은 날(0) → 1~7일 전 시작으로 차례로 시도
    for back in range(0, 8):

        start = (end - timedelta(days=back)).strftime("%Y%m%d")
        end_str = end.strftime("%Y%m%d")

        try:
            df = stock.get_index_price_change(start, end_str, "KOSPI")

            if df is None or df.empty:
                continue

            rate_col = _pick_column(df, "등락률")
            if rate_col is None:
                print(f"[KRX] 등락률 열 없음: {list(df.columns)}")
                continue

            # 코스피 지수 행으로 조회 구간 검증
            kospi_rows = [
                n for n in df.index
                if str(n).strip() in ("코스피", "KOSPI", "코스피 지수")
            ]

            if kospi_rows and kospi_change_percent is not None:
                krx_kospi = float(df.loc[kospi_rows[0], rate_col])
                print(
                    f"[KRX] 시작일 {start}: 코스피 {krx_kospi}% "
                    f"(야후 {kospi_change_percent}%)"
                )
                if abs(krx_kospi - kospi_change_percent) > 0.05:
                    continue
            elif back > 0:
                # 검증할 코스피 행이 없으면 첫 시도 결과만 신뢰하지 않음
                print("[KRX] 코스피 행을 찾지 못해 검증 불가")
                continue

            sectors = []
            for name, row in df.iterrows():
                name = str(name).strip()
                if not _is_sector(name):
                    continue
                sectors.append({
                    "name": name,
                    "change_percent": round(float(row[rate_col]), 2)
                })

            if not sectors:
                print("[FAIL] 업종 지수를 찾지 못함")
                return None

            if all(s["change_percent"] == 0 for s in sectors):
                print(f"[SKIP] 시작일 {start}: 업종 등락률이 전부 0")
                continue

            sectors.sort(key=lambda s: s["change_percent"], reverse=True)

            result = {
                "date": trade_date,
                "sectors": sectors
            }

            print(f"[SUCCESS] 업종 {len(sectors)}개")
            print(sectors[:3], "...", sectors[-3:])
            return result

        except Exception as e:
            print(f"[ERROR] 업종 등락률 ({start}): {type(e).__name__} {e}")

    print("[FAIL] 코스피 등락률과 일치하는 업종 데이터를 찾지 못함")
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
    # 한국 투자자별 수급
    # ----------------------------------------

    investor_flow = {
        "KOSPI": get_investor_flow("KOSPI"),
        "KOSDAQ": get_investor_flow("KOSDAQ")
    }

    # 수급이 확인된 거래일을 기준으로 종목·업종 데이터 조회
    kospi_flow = investor_flow["KOSPI"]
    trade_date = kospi_flow["date"] if kospi_flow else None

    top_net_purchases = get_top_net_purchases_all(trade_date)

    # 야후 코스피 날짜가 수급 기준일과 같을 때만 검증값으로 사용
    yahoo_kospi = korea_market["KOSPI"]
    kospi_check = (
        yahoo_kospi["change_percent"]
        if yahoo_kospi and yahoo_kospi["date"] == trade_date
        else None
    )

    sector_performance = get_sector_performance(trade_date, kospi_check)

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
        "US2Y": get_fred_yield("DGS2", "미국 2년물 국채금리")
    }

    # FRED는 하루 늦게 발표되는 경우가 많아 2년물 기준일이
    # 10년물(다른 미국 지표)보다 이를 수 있음 → 표시해 둠
    us2y = bond_market["US2Y"]
    us10y = bond_market["US10Y"]

    if us2y is not None:
        lagged = (
            us10y is not None
            and us2y["date"] < us10y["date"]
        )
        us2y["is_previous_day"] = lagged
        us2y["note"] = (
            f"FRED 발표 지연으로 {us2y['date']} 기준(하루 전) 데이터"
            if lagged else ""
        )

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

        "korea_market": {
            "KOSPI": korea_market["KOSPI"],
            "KOSDAQ": korea_market["KOSDAQ"],
            "investor_flow": investor_flow,
            "top_net_purchases": top_net_purchases,
            "sector_performance": sector_performance
        },

        "exchange_rate": exchange_rate,

        "bond_market": bond_market,

        "commodities": commodities
    }

    print("=" * 60)
    print("시장 데이터 수집 완료")
    print("=" * 60)

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2
        )
    )

    # ----------------------------------------
    # JSON 파일 저장
    # ----------------------------------------

    with open(
        "market_data.json",
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            result,
            f,
            ensure_ascii=False,
            indent=2
        )

    print("=" * 60)
    print("market_data.json 저장 완료")
    print("=" * 60)


if __name__ == "__main__":
    main()
