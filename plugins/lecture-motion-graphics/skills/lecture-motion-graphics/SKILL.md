---
name: "lecture-motion-graphics"
description: "강의·발표 영상(얼굴 촬영 또는 컴퓨터 실습 화면)을 받아 음성 타이밍에 맞춘 텍스트·그래픽, 하단 자막, BGM을 넣은 16:9 30fps 모션그래픽 MP4로 만들 때 사용."
---

# 강의 영상 → 모션그래픽 MP4

사용자가 강의/발표 영상을 첨부하고 "모션그래픽 만들어줘" 류의 요청을 하면 이 절차를 따른다. 기본 출력: 1920×1080, 30fps, H.264 + AAC MP4. 별도 지시가 없으면 아래 '하우스 스타일'을 그대로 쓴다(시리즈 통일감이 중요함).

## 함께 들어있는 스크립트
이 스킬 폴더에 `scripts/`가 있으면 처음부터 짜지 말고 그것을 복사해서 시작한다.
- `scripts/bgm.py <길이초>` → `bgm.wav` 생성.
- `scripts/render_example.py` → 첫 강의에 실제로 쓴 완성 코드(모든 헬퍼, 레이아웃 전환, 자막 포함). 작업 폴더에 복사한 뒤 장면(`add(...)`), `SUBS`, `KF`, `CROP_CARD` 중심만 새 영상에 맞게 바꾼다. 실행: `SRC=input.mp4 python3 render.py [미리보기 시각들]` (같은 폴더에 `mix.wav` 필요). 원본이 1280×720이 아니면 `CROP_CARD`의 화자 중심 x(기본 650)를 프레임을 보고 다시 정한다.
`scripts/`가 없으면(스킬 본문만 설치된 경우) 아래 설명대로 직접 구현한다.

## 하우스 스타일 (기본값)
- 색: 강조 주황 ACC=(255,178,72), 청록 TEAL=(88,220,205), 경고 빨강 RED=(255,98,98), 보조 보라 (160,140,255), 흰 글자, 보조글 MUTED=(188,198,220), 패널 남색 반투명 (14,20,38,~210).
- 폰트: Noto Sans CJK KR (`/usr/share/fonts/opentype/noto/NotoSansCJK-{Black,Bold,Medium,Regular}.ttc`, **index=1 이 KR**).
- 레이아웃 2모드를 부드럽게 전환(ease in-out 0.55s):
  - **full**: 영상 전체화면 + 아주 느린 push-in(최대 3%) + 상단 그라데이션. 인사/이름표, 핵심 결론 문장, 마무리 "감사합니다"에 사용.
  - **card**: 같은 영상을 흐리게+남색 오버레이한 배경, 오른쪽 둥근 카드(x1050,y70,760×830, 반경30, 주황 테두리, 그림자)에 화자 크롭, 왼쪽 x≈110 열에 그래픽.
- 배경은 사용자가 준 영상/이미지만 사용(외부 이미지 금지). 이미지가 오면 card 모드 배경이나 장면 전환에 활용.
- 하단 자막: 굵게 50px, 검은 반투명 둥근 박스, 화면 하단 56px 위, 한 줄(≈22자 이하)씩, 단어 타이밍으로 끊기.
- 시작: 상단 좌측 태그 pill + 큰 제목(내용 요약으로 직접 지음, 강조어는 주황), 이름이 나오면 좌하단 이름표.
- 끝: "감사합니다" 큰 글자 + 이름(주황), 마지막 0.6초 페이드아웃.
- 그래픽 요소: 텍스트 kicker(40 Medium) + 헤드라인(62~70 Black, 핵심어 주황), 번호 팁 카드, 아이콘 행(체크/느낌표), 사람 아이콘(표정), 말풍선, 하트, 화살표, 검색창 타이핑, 브랜드명 pill(로고는 그리지 않음). 각 요소는 해당 단어가 발화되는 시각에 등장(up/left/pop 애니메이션 0.45s), 장면 끝에서 페이드아웃.

## 절차
1. **확인**: `ffprobe`로 길이/해상도/fps. 첨부물에 이미지가 없는데 사용자가 '이미지'를 언급했으면 영상만으로 진행하고 마지막에 알린다. 4×4 프레임 시트(`fps=1/5,scale=480:-1,tile=4x4`)로 화면 내용 파악.
2. **받아쓰기**: `pip install --break-system-packages faster-whisper`. mp4를 바로 넣으면 PyAV 오류가 나므로 `ffmpeg -ac 1 -ar 16000 voice16k.wav`로 뽑고 `wave`+numpy로 읽어 배열을 전달(soundfile 없음). 모델 `medium`, `language='ko'`, `word_timestamps=True`, `vad_filter=True`, `compute_type='int8'`. 단어 타임스탬프를 json으로 저장.
3. **스크립트 정리**: 오인식은 문맥으로 교정(예: 'AI가 대화식으로'→'AI와 대화식으로'), 교정한 곳은 마지막에 알린다. 자막 청크(start,end,text) 목록 작성.
4. **장면 설계**: 의미 단위로 장면을 나누고 각 장면의 kicker/헤드라인/그래픽과 등장 시각(단어 시작 시각)을 정한다. 결론 문장 구간은 full 모드로 큰 제목+밑줄 스윕+요약 pill. 다음 예고가 있으면 NEXT 장면.
5. **BGM**: 아래 `bgm.py`로 직접 합성(저작권 문제 없음). 목소리는 `loudnorm=I=-16`, BGM `volume≈0.16` + `sidechaincompress`로 덕킹, 마지막 0.7s 페이드.
6. **미리보기**: `python3 render.py 2.8 6.5 14.5 ...`처럼 시각을 주면 해당 프레임만 jpg로 저장 → 타일로 묶어 Read로 직접 확인(겹침, 잘림, 자막과 그래픽 충돌, 카드 안 화자 위치). 화자 중심 x는 프레임에서 확인해 `CROP_CARD` 중심을 맞춘다.
7. **전체 렌더**: 인자 없이 실행(65초 영상 ≈ 3분, 2코어). 렌더 후 몇 프레임 추출해 재확인.
8. **전달**: SendUserFile로 MP4 전달. 답변에는 구성 요약, 내가 지은 문구, 자막 교정 내용, 배경 소재 관련 메모만 짧게.

## 컴퓨터 실습(화면 시연) 영상일 때
- 얼굴 영상과 화면 녹화가 **따로** 오면: 시연 구간은 화면 녹화를 크게(full 또는 약간 여백 둔 카드), 얼굴은 우하단 원형 PiP(지름≈260, 주황 테두리)로 계속 표시. 두 파일 싱크는 오디오 상호상관으로 맞추거나 사용자가 준 오프셋 사용.
- **한 파일**에 섞여 오면: `ffmpeg -vf "select='gt(scene,0.3)',showinfo"`로 컷 지점을 찾고, 각 구간 대표 프레임을 Read로 보고 '얼굴'/'화면' 분류 → 구간별 레이아웃 적용(얼굴 구간은 하우스 스타일, 화면 구간은 화면 우선).
- 시연 구간 그래픽: "여기 클릭/이렇게 입력" 발화 시각에 맞춰 (a) 해당 영역 줌(crop box를 1.6~2.2배로 ease 이동, 0.6s), (b) 강조 테두리/화살표 콜아웃, (c) 좌상단 단계 표시 "STEP 1 → 2". 좌표는 프레임을 직접 보고 정한다(추정 금지). 화면 글자가 작으면 줌을 우선 사용.
- 화면 녹화 위에는 그래픽을 과하게 얹지 말고 상단/좌측 여백과 하단 자막만 사용.

## bgm.py (Fmaj7–G6–Em7–Am7, 96bpm, 패드+아르페지오+베이스+소프트 드럼)
```python
import numpy as np, wave, sys
SR=48000; DUR=float(sys.argv[1]) if len(sys.argv)>1 else 66.0
BPM=96; beat=60/BPM; bar=beat*4; n=int(SR*DUR)
L=np.zeros(n); R=np.zeros(n)
def midi(m): return 440*2**((m-69)/12)
chords=[[53,57,60,64],[55,59,62,64],[52,55,59,62],[57,60,64,67]]; roots=[41,43,40,45]
def add(buf,start,sig):
    i=int(start*SR)
    if i>=n: return
    j=min(n,i+len(sig)); buf[i:j]+=sig[:j-i]
t_bar=np.arange(int(bar*SR))/SR
for b in range(int(DUR/bar)+1):
    sig=np.zeros(len(t_bar))
    for m in chords[b%4]:
        f=midi(m)
        for det in(-0.12,0.12):
            ph=(t_bar*f*(1+det/100))%1.0; sig+=(2*ph-1)*0.5+np.sin(2*np.pi*f*t_bar)
    env=np.minimum(1,t_bar/0.6)*np.minimum(1,(bar-t_bar)/0.5+0.2)
    add(L,b*bar,sig*env*0.018); add(R,b*bar,sig*env*0.018)
k=np.ones(24)/24; L=np.convolve(L,k,'same'); R=np.convolve(R,k,'same')
tp=np.arange(int(0.6*SR))/SR
for b in range(1,int(DUR/bar)+1):
    for i,p in enumerate([0,1,2,3,2,1,2,3]):
        f=midi(chords[b%4][p]+12)
        s=(np.sin(2*np.pi*f*tp)+0.3*np.sin(4*np.pi*f*tp))*np.exp(-tp*7)*0.05
        st=b*bar+i*beat/2; pan=0.35+0.3*(i%2)
        add(L,st,s*(1-pan)); add(R,st,s*pan)
tb=np.arange(int(beat*SR))/SR
for b in range(2,int(DUR/bar)+1):
    f=midi(roots[b%4])
    for q in range(4):
        s=np.sin(2*np.pi*f*tb)*np.exp(-tb*3)*np.minimum(1,tb/0.01)*0.10
        add(L,b*bar+q*beat,s); add(R,b*bar+q*beat,s)
tk=np.arange(int(0.35*SR))/SR
kick=np.sin(2*np.pi*(50*tk+60*(1-np.exp(-tk*30))/30))*np.exp(-tk*9)*0.22
rng=np.random.default_rng(1)
th=np.arange(int(0.06*SR))/SR; hn=np.diff(np.concatenate([[0],rng.standard_normal(len(th))]))
hat=hn*np.exp(-th*70)*0.025
tc=np.arange(int(0.2*SR))/SR
clap=np.convolve(rng.standard_normal(len(tc)),np.ones(6)/6,'same')*np.exp(-tc*25)*0.05
for b in range(2,int(DUR/bar)+1):
    for q in range(4):
        st=b*bar+q*beat
        if q in(0,2): add(L,st,kick); add(R,st,kick)
        else: add(L,st,clap*0.8); add(R,st,clap)
        add(L,st+beat/2,hat*0.7); add(R,st+beat/2,hat)
mix=np.stack([L,R],1); mix/=np.max(np.abs(mix))*1.12
fi=int(1.5*SR); fo=int(3*SR)
mix[:fi]*=np.linspace(0,1,fi)[:,None]; mix[-fo:]*=np.linspace(1,0,fo)[:,None]
w=wave.open('bgm.wav','wb'); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
w.writeframes((mix*32767).astype(np.int16).tobytes()); w.close()
```

## 오디오 믹스
```bash
ffmpeg -y -i SRC.mp4 -i bgm.wav -filter_complex "[0:a]loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000,asplit=2[v1][v2];[1:a]volume=0.16[b];[b][v1]sidechaincompress=threshold=0.05:ratio=4:attack=30:release=500[bd];[v2][bd]amix=inputs=2:duration=first:normalize=0,afade=t=out:st=<DUR-0.75>:d=0.74,alimiter=limit=0.95[a]" -map "[a]" -ar 48000 -ac 2 mix.wav
```

## render.py 골격 (PIL 합성 → ffmpeg 파이프)
핵심 구조. 장면 내용(`add(...)` 호출들), `SUBS`, `KF`(모드 키프레임), `CROP_CARD` 중심만 영상마다 바꾼다.

- 디코드: `ffmpeg -i SRC -vf fps=30 -f rawvideo -pix_fmt rgb24 -` 에서 SW*SH*3 바이트씩 읽음(프레임 부족 시 마지막 프레임 재사용). N=ceil(DUR*30).
- 인코드: `ffmpeg -f rawvideo -pix_fmt rgb24 -s 1920x1080 -r 30 -i - -i mix.wav -map 0:v -map 1:a -c:v libx264 -preset medium -crf 18 -pix_fmt yuv420p -c:a aac -b:a 192k -shortest -movflags +faststart out.mp4`
- 스프라이트는 2배 크기(S=2)로 그린 뒤 LANCZOS 축소(안티앨리어싱). 정적 스프라이트는 미리 만들어 캐시, 매 프레임은 위치/알파/스케일만 변경.
- 요소 클래스 `El(t0,t1,sprite_or_fn,x,y,anim='up'|'left'|'right'|'pop',dur=0.45,out=0.35,center=False)`; 등장 알파=clamp(pin*1.6)*(1-ease_in(pout)), up은 40px 아래서, left는 60px 왼쪽에서, pop은 0.5→1 easeOutBack. 동적 요소(타이핑 검색창, 밑줄 스윕)는 `fn(t,t0)`가 캐시된 스프라이트 반환.
- 알파 적용은 numpy로 A채널 곱. 캔버스 밖 음수 좌표는 crop 후 합성.
- 모드 전환: `mode(t)`가 KF를 ease_io 보간한 c∈[0,1]. dest rect는 (0,0,1920,1080)→CARD, 소스 crop은 (0,0,1280,720)→CROP_CARD를 같은 c로 보간 후 `src.resize((w,h), BILINEAR, box=...)`. 배경은 소스를 192×108로 줄여 GaussianBlur(5) 후 확대 + 남색 오버레이(알파 165*c). 그림자는 1/4 해상도 마스크 블러. 둥근 마스크는 크기별 캐시.
- 매 프레임: 배경/카드 → 비네트 → (full일수록) 상단 그라데이션 → 요소들 → 자막 → 시작 0.4s 페이드인/끝 0.6s 페이드아웃.
- 미리보기 모드: argv에 시각들이 있으면 그 프레임만 `prev_XX.XX.jpg`로 저장하고 종료.

주요 헬퍼(직접 구현): `text_sprite(parts,size,weight)`(parts=[(텍스트,색)...], 블러 그림자), `pill`, `panel_sprite(w,h,accent=)`, `circle_icon(size,bg,draw_fn|text)`, `draw_check`, `draw_x`, `person_sprite(size,col,label,mood='sad'|'happy')`, `heart_sprite`, `arrow_sprite(w,dashed)`, `bubble_sprite(text,tail)`, `search_bar(text,cursor)`, `tip_card(num,title,sub,col)`, `step_row(icon,text)`, `underline_fn(w)`, `sub_sprite(text)`.

## 주의
- 실제 로고·캐릭터는 그리지 않는다(브랜드명은 텍스트 pill로만).
- 그래픽이 카드(x≥1050)나 자막 영역(y≥930)을 침범하지 않게 왼쪽 열 폭 ≤ 880px 유지.
- 화면이 바뀌는 순간과 그래픽 등장이 겹치면 그래픽을 0.2~0.3s 늦춘다.
- 작업용 파일은 scratchpad에, 최종 MP4는 작업 디렉터리에 의미 있는 한글 파일명으로 저장 후 전달.