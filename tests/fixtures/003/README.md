# 003 시험 스냅샷 (형식 2)

`snapshot_data.json` — 재현 테스트(`tests/test_rebuild.py`)용 실제 수집 자료. **테스트 자료일 뿐이며 기업별 결론을 위키에 넣지 않는다(헌법 VI).**

| 항목 | 값 |
|---|---|
| 종목 | 000660.KS, 005930.KS, MU, TSM (지수 ^GSPC, ^KS11, ^SOX) |
| 명령 | `get_financial_stats.py --tickers 000660.KS,005930.KS,MU,TSM --cyclical 000660.KS,005930.KS,MU --snapshot …` |
| 수집 완료 | 2026-10-20 19:02:37 KST (한국 장 마감 후, 미국 개장 전) |
| 코드 | `8b0b659` (claude/003-pipeline-split) |
| 버전 | python 3.13.2, yfinance 1.7.0, pandas 3.0.6, numpy 2.5.4 — pandas·numpy는 `tests/requirements-pinned.txt`에 고정 |
| 크기 | 1.15MB (원본 2.39MB를 들여쓰기 없는 JSON으로 저장, 내용 같음) |
| Section 4 기준본 | `section4` — 생성 때 표준 출력에 `snapshot.section4_body`를 적용해 `attach_section4`로 덧붙임 |

- 네이버 수급에 당일(10-20) 행이 아직 없어 다음 금융 장중 조회(`daum_quote`, `daum_investor_days`)가 실제로 들어 있다. 그래서 수급 표에 '장중 잠정' 행이 있다(잠정 경로 시험).
- 버전을 올리려면 같은 명령으로 다시 수집하고 이 표와 고정 파일을 함께 고친다.
