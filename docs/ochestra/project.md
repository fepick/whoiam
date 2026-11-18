# whoiam 역할 연결

FastAPI·HTML/JS 기반 로컬 업무·구매·재고·근무·보고 소프트웨어

## 기본 역할

- [software-engineer](agents/software-engineer.md)
- [privacy-review](agents/privacy-review.md)
- [verification](agents/verification.md)
- [report-writer](agents/report-writer.md)
- [deliverables](agents/deliverables.md)

## 필요 시 역할

- [brand-philosophy](agents/brand-philosophy.md)
- [data-integration](agents/data-integration.md)

## 기존 기준 문서

- ../../AGENTS.md
- ../../README.md
- ../../CONTRIBUTING.md
- ../../docs/security.md

## 보존할 제약

- 기존 AGENTS.md와 CONTRIBUTING.md의 아키텍처·검증·브랜치 규칙을 우선한다.
- 운영 데이터·.private·OS 자격증명은 접근하지 않고 합성 데이터만 사용한다.
- core.hooksPath=.githooks와 기존 보안 훅을 유지하며 pre-commit install을 실행하지 않는다.
- 제품 기능인 BOM은 소프트웨어 도메인이다. 실제 전자회로 BOM 역할을 기본 배정하지 않는다.
- 설계철학·브랜드 후보는 승인 전 제안으로 유지한다.
