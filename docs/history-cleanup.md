# Git 이력 개인정보 정리

2026-11-04에 원격 전체 이력을 별도 복제해 정리했습니다. 기능을 main에 병합하는 작업과는 별개로, 기존 커밋의 개인정보를 치환한 작업입니다.

## 수행 범위

- 원본 Git bundle을 checkout 밖 `%LOCALAPPDATA%\WhoiamHistoryBackups\`의 사용자 전용 폴더에 보존합니다.
- 백업은 Windows DPAPI CurrentUser로 암호화하고 복호화 후 해시 대조를 마쳤습니다. 현재 Windows 계정에서만 복호화할 수 있습니다.
- 파일 내용과 커밋·태그 메시지에서 기존 이름·개인 이메일을 치환하고, 작성자·커미터·태거 메타데이터는 공개 별칭과 GitHub noreply 주소로 정리합니다.
- 관리하는 브랜치·태그의 집합과 최신 배포 소스 트리를 대조하고, 이름·이메일 잔존 여부와 회귀 테스트를 검사합니다.
- 원격 갱신은 사전에 기록한 각 참조의 SHA와 일치할 때만 원자적으로 수행합니다. 다른 사람의 새 작업이 생기면 중단합니다.
- 기존 PR은 닫고 정리된 이력으로 검토 PR을 다시 만듭니다.

## 다른 개발 PC

이전 clone에서 그대로 push하거나 이전 브랜치를 병합하면 원래 이력이 다시 유입될 수 있습니다.
다른 PC에서는 기존 clone에 미공유 작업이 있는지 먼저 확인한 후 새 폴더에 clone합니다. 실제 운영 데이터는 소스 폴더와 별도로 보존합니다.

```powershell
git clone --branch release/v0.04 https://github.com/fepick/whoiam.git whoiam-clean
cd whoiam-clean
```

개발 커밋을 만들기 전에는 자신의 GitHub 별칭과 계정 설정에 표시된 noreply 이메일을 해당 저장소의 `user.name`·`user.email`에 지정합니다. 다른 기기의 전역 Git 설정은 자동 변경하지 않습니다.
이전 clone·백업은 로컬에 비공개 보관하며, 정리 전 이력을 원격으로 다시 올리지 않습니다.

## GitHub에 남을 수 있는 참조

원격 갱신 후 GitHub에서 새로 clone해 관리하는 15개 브랜치의 원래 이름·이메일 잔존 일치가 0건임을 재확인했습니다.
기존 PR #1의 `refs/pull/1/head`는 정리 전 커밋을 계속 가리키는 것으로 확인했습니다. 이 읽기 전용 참조는 별도 지원 문의 대상입니다.

닫힌 PR의 `refs/pull/*`는 GitHub의 읽기 전용 참조이므로 일반 force push로 제거할 수 없습니다. PR 닫기는 캐시나 과거 커밋을 완전히 지우는 조치가 아닙니다.
기존 PR 참조·캐시에 개인정보가 남아 있다면 저장소 소유자가 [GitHub Support](https://support.github.com/)에 제거 가능 여부를 문의합니다. GitHub는 지원 기준에 해당하는 민감정보만 처리하며 일반 이름·이메일 정리를 보장하지 않습니다.
문의에는 저장소·기존 PR 번호·최초 변경 커밋 정보와 잔존 위치를 전달하고, 원문 값이나 백업 파일은 공개 Issue·PR에 붙이지 않습니다.
제3자의 clone·fork는 소유자와 별도로 정리해야 합니다. [GitHub 공식 안내](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository)를 참고합니다.

공개가 목적이고 이전 PR·캐시의 잔존 범위를 해소할 수 없다면, 검토된 최신 소스만 새 저장소의 첫 커밋으로 배포하는 방식을 검토합니다. 기존 저장소의 정보가 사라지는 것은 아닙니다.

## 현재 작업 폴더의 복구 자료

현재 VS Code 작업 폴더의 브랜치 참조·소스는 새 원격 이력과 동기화했습니다. 운영 데이터·가상환경은 변경하지 않았습니다.
사용자의 추가 명시 승인 후 암호화 백업의 복호화와 복구 범위를 다시 검증하고, 로컬 `ORIG_HEAD`·이전 reflog·도달 불가능한 기존 Git 객체를 정리했습니다.
정리 직후 모든 로컬 Git 객체 589개를 검사해 원래 이름·이메일 잔존 일치 0건을 확인했고, 브랜치 참조·소스 트리 보존과 `git fsck`도 통과했습니다.
원본 암호화 백업은 유지합니다. 이후 정상적인 커밋·fetch로 새로 생성되는 reflog는 정리된 별칭과 noreply 설정을 사용합니다.
