# KI-008 ADR 통화 불일치

> Sources: yfinance 조회 결과, 2026-10-14
> Raw: [Yahoo 스냅샷](../../raw/data-checks/2026-10-14-yahoo-info-snapshot.md)
> Updated: 2026-10-14

## Overview

TSMC ADR(TSM)은 시세 통화가 USD인데 재무 통화(financialCurrency)는 TWD입니다. 그래서 Yahoo의 bookValue 4.8515477, priceToBook 90.92047처럼 서로 다른 통화를 섞은 값이 나옵니다.

## 조치

- 통화가 다르면 P/B·P/S·EV 배수·BPS를 P/E·ROE·이익률로 역산해 고치고 경고 `[KI-008]`을 냅니다. P/B 밴드는 계산하지 않습니다. 상태: 우회 적용.
