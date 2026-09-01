from pykrx import stock
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


KST = ZoneInfo("Asia/Seoul")


def test_krx():

    today = datetime.now(KST).date()

    print("=" * 60)
    print("KRX 투자자별 수급 테스트")
    print("=" * 60)

    for i in range(7):

        target = today - timedelta(days=i)
        date = target.strftime("%Y%m%d")

        print()
        print("=" * 60)
        print(f"조회일: {date}")
        print("=" * 60)

        for market in ["KOSPI", "KOSDAQ"]:

            print()
            print(f"[{market}] 조회 시작")

            try:

                df = stock.get_market_trading_value_by_investor(
                    date,
                    date,
                    market
                )

                print("데이터 타입:", type(df))

                if df is None:
                    print("[FAIL] 데이터가 None입니다.")
                    continue

                if df.empty:
                    print("[FAIL] 데이터가 비어 있습니다.")
                    continue

                print("[SUCCESS] 데이터 조회 성공")
                print()
                print(df)

                print()
                print("컬럼:")
                print(list(df.columns))

                print()
                print("인덱스:")
                print(list(df.index))

                return

            except Exception as e:

                print("[ERROR]")
                print(type(e).__name__)
                print(str(e))


if __name__ == "__main__":
    test_krx()
