# 0004. 스펙 주도 개발 도구로 Spec Kit을 쓴다

- 상태: 채택
- 날짜: 2026-10-14

## 배경

로드맵·스펙을 폴더 규칙(`specs/NNN/spec·plan·tasks`)으로만 운영해 왔다. 순서를 지키게 하는 장치가 CLAUDE.md 문장뿐이었고, 문서 형식도 임의로 정했다. 후보는 GitHub Spec Kit과 OpenSpec(Fission-AI)이었다.

## 결정

Spec Kit v1.1.3을 Claude Code 통합(스킬 `/speckit-*`)과 PowerShell 보조 스크립트로 도입한다.

- 기존 `specs/001`이 이미 Spec Kit 구조(spec·plan·tasks)라 옮길 것이 적다.
- 설치가 `uv`로 끝난다. OpenSpec은 Node.js 20.19+가 새로 필요하다.
- '현재 동작의 진실'은 이미 `references/rules/`(스킬과 함께 배포)와 위키에 있다. OpenSpec의 `openspec/specs/`를 들이면 같은 역할이 세 곳에 생긴다.
- 헌법(`constitution.md`)에 투자 스킬의 객관성 원칙과 데이터 품질 원칙을 넣어, 모든 스펙 단계가 이를 점검하게 할 수 있다.
- PowerShell 스크립트는 첫 줄이 `pwsh`지만 Windows PowerShell 5.1에서도 동작함을 확인했다(`check-prerequisites.ps1`).
- 최신 v1.2.0은 도입 당일 릴리스라, 며칠 검증된 v1.1.3으로 고정했다.

## 결과

- 장점: 단계별 명령과 헌법 점검, `/speckit-analyze`의 문서 간 일관성 점검.
- 단점: 문서가 무겁다. 작은 수정은 스펙 없이 하도록 헌법 '개발 흐름'에 예외를 둔다. 결과 검증 기능은 없어 CI가 보완한다.
- 현재 스펙 폴더 지정(`.specify/feature.json`)은 PC별이라 Git에 없다. 새 PC에서는 직접 지정한다(README).
- 업그레이드: CLI를 올린 뒤 `specify init --here --force --integration claude --script ps`로 프로젝트 파일을 갱신한다. 헌법·템플릿 변경분이 덮어써질 수 있으므로 먼저 브랜치에서 비교한다.
