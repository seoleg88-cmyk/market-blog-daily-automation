import json
import sys
from datetime import datetime


# 반드시 존재해야 하는 데이터
REQUIRED_MARKETS = {
    "us_market": [
        "S&P500",
        "NASDAQ",
        "DOW",
        "VIX"
    ],
    "korea_market": [
        "KOSPI",
        "KOSDAQ"
    ],
    "exchange_rate": [
        "USD_KRW"
    ],
    "bond_market": [
        "US10Y",
        "US2Y"
    ],
    "commodities": [
        "WTI",
        "BRENT",
        "GOLD"
    ]
}


# 각 데이터에 반드시 존재해야 하는 값
REQUIRED_FIELDS = [
    "name",
    "date",
    "close",
    "previous_close",
    "change",
    "change_percent"
]


def validate_number(value, field_name, market_name):
    """숫자 데이터인지 확인"""

    if value is None:
        print(f"[FAIL] {market_name}: {field_name} 값이 없습니다.")
        return False

    if isinstance(value, bool):
        print(f"[FAIL] {market_name}: {field_name} 값이 잘못되었습니다.")
        return False

    if not isinstance(value, (int, float)):
        print(
            f"[FAIL] {market_name}: "
            f"{field_name}이 숫자가 아닙니다. "
            f"현재 값: {value}"
        )
        return False

    return True


def validate_market(market_name, data):
    """개별 시장 데이터 검증"""

    success = True

    if data is None:
        print(f"[FAIL] {market_name}: 데이터가 없습니다.")
        return False

    if not isinstance(data, dict):
        print(f"[FAIL] {market_name}: 데이터 형식이 잘못되었습니다.")
        return False

    # 필수 필드 확인
    for field in REQUIRED_FIELDS:

        if field not in data:
            print(
                f"[FAIL] {market_name}: "
                f"필수 항목 '{field}'가 없습니다."
            )
            success = False

    if not success:
        return False

    # 숫자 필드 확인
    numeric_fields = [
        "close",
        "previous_close",
        "change",
        "change_percent"
    ]

    for field in numeric_fields:

        if not validate_number(
            data[field],
            field,
            market_name
        ):
            success = False

    # 날짜 확인
    try:
        datetime.strptime(
            data["date"],
            "%Y-%m-%d"
        )
    except Exception:

        print(
            f"[FAIL] {market_name}: "
            f"날짜 형식이 잘못되었습니다. "
            f"현재 값: {data['date']}"
        )

        success = False

    # 종가가 0 이하인지 확인
    if isinstance(data["close"], (int, float)):

        if data["close"] <= 0:

            print(
                f"[FAIL] {market_name}: "
                f"종가가 0 이하입니다."
            )

            success = False

    # 전일 종가가 0 이하인지 확인
    if isinstance(data["previous_close"], (int, float)):

        if data["previous_close"] <= 0:

            print(
                f"[FAIL] {market_name}: "
                f"전일 종가가 0 이하입니다."
            )

            success = False

    # 등락률 계산 검증
    try:

        calculated_change = (
            data["close"]
            - data["previous_close"]
        )

        calculated_percent = (
            calculated_change
            / data["previous_close"]
            * 100
        )

        if abs(
            calculated_percent
            - data["change_percent"]
        ) > 0.1:

            print(
                f"[WARNING] {market_name}: "
                f"등락률 계산값과 저장값에 차이가 있습니다."
            )

    except Exception:
        pass

    if success:

        print(
            f"[PASS] {market_name}: "
            f"{data['date']} / "
            f"{data['close']} / "
            f"{data['change_percent']}%"
        )

    return success


def main():

    print("=" * 60)
    print("시장 데이터 검증 시작")
    print("=" * 60)

    # JSON 파일 읽기
    try:

        with open(
            "market_data.json",
            "r",
            encoding="utf-8"
        ) as f:

            data = json.load(f)

    except FileNotFoundError:

        print("[FAIL] market_data.json 파일이 없습니다.")
        sys.exit(1)

    except json.JSONDecodeError as e:

        print(
            "[FAIL] market_data.json의 "
            f"JSON 형식이 잘못되었습니다: {e}"
        )

        sys.exit(1)

    overall_success = True

    # 수집 시각 확인
    if "collected_at" not in data:

        print("[FAIL] collected_at이 없습니다.")
        overall_success = False

    # 각 시장 검증
    for market_group, markets in REQUIRED_MARKETS.items():

        print()
        print(f"[CHECK] {market_group}")

        if market_group not in data:

            print(
                f"[FAIL] {market_group} 데이터 그룹이 없습니다."
            )

            overall_success = False
            continue

        for market_name in markets:

            if market_name not in data[market_group]:

                print(
                    f"[FAIL] {market_name}: "
                    f"데이터 항목이 없습니다."
                )

                overall_success = False
                continue

            result = validate_market(
                market_name,
                data[market_group][market_name]
            )

            if not result:
                overall_success = False

    print()
    print("=" * 60)

    if overall_success:

        print("✅ 시장 데이터 검증 성공")
        print("모든 필수 데이터가 정상입니다.")
        print("=" * 60)

        sys.exit(0)

    else:

        print("❌ 시장 데이터 검증 실패")
        print("잘못된 데이터가 발견되었습니다.")
        print("=" * 60)

        # GitHub Actions를 실패 처리
        sys.exit(1)


if __name__ == "__main__":
    main()
