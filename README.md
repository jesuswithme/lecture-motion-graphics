# lecture-motion-graphics

강의·발표 영상을 넣으면 **말하는 타이밍에 맞춘 텍스트·그래픽 + 하단 자막 + BGM**이 들어간
**16:9, 30fps 모션그래픽 MP4**로 만들어 주는 Claude 스킬입니다.

- 음성을 받아쓰고(단어 단위 타이밍), 내용에 맞는 키워드·그래픽 장면을 자동 구성
- 화자 영상이 전체 화면 ↔ 오른쪽 카드로 부드럽게 전환, 왼쪽에 그래픽
- 하단 자막, 저작권 걱정 없는 자체 합성 BGM(말할 때 자동으로 작아짐)
- 배경은 사용자가 준 영상·이미지만 사용(그림을 만들어 달라고 하면 Codex CLI의 codex-image로 생성, TopView 크레딧 없음)
- 컴퓨터 실습(화면 녹화) 영상: 얼굴 원형 PiP, 클릭 위치 확대·강조, 단계 표시

## 사용법

영상을 첨부하고 아래처럼 입력합니다.

```
/lecture-motion-graphics
```

필요하면 한 줄 덧붙입니다.

```
/lecture-motion-graphics 제목은 "프롬프트 잘 쓰는 법"으로, 3가지 팁 부분을 크게
```

## 설치

### 1) Claude 앱(claude.ai · 데스크톱) — ZIP 업로드
1. 이 저장소의 [`dist/lecture-motion-graphics.zip`](dist/lecture-motion-graphics.zip)을 내려받습니다.
2. Claude 설정의 **스킬(Skills)** 메뉴에서 ZIP을 업로드합니다.

### 2) Claude Code — 플러그인으로 설치 (업데이트도 자동)
```bash
claude plugin marketplace add jesuswithme/lecture-motion-graphics
claude plugin install lecture-motion-graphics@lecture-motion-graphics
```
설치 후 세션에서 `/lecture-motion-graphics:lecture-motion-graphics` 로 실행합니다.

### 3) Claude Code — 폴더 복사 (가장 단순)
```bash
git clone https://github.com/jesuswithme/lecture-motion-graphics
cp -r lecture-motion-graphics/plugins/lecture-motion-graphics/skills/lecture-motion-graphics ~/.claude/skills/
```

## 실행 환경
Python 3, ffmpeg, Pillow, numpy, 한글 폰트(Noto Sans CJK KR). 받아쓰기는 `faster-whisper`(첫 실행 때 자동 설치·모델 다운로드).

## 구성
```
.claude-plugin/marketplace.json          # Claude Code 마켓플레이스
plugins/lecture-motion-graphics/
  .claude-plugin/plugin.json
  skills/lecture-motion-graphics/
    SKILL.md                             # 스킬 본문(절차·하우스 스타일)
    scripts/bgm.py                       # BGM 합성
    scripts/render_example.py            # 실제 렌더 코드(예시 장면 포함)
dist/lecture-motion-graphics.zip         # Claude 앱 업로드용
```
