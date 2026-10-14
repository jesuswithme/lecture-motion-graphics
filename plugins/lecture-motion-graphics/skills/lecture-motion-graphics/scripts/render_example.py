# 예시 렌더 스크립트 (첫 강의 "AI, 검색 말고 대화하세요"에 사용한 실제 코드)
# 사용법:  SRC=input.mp4 python3 render_example.py            -> out.mp4 (같은 폴더에 mix.wav 필요)
#          SRC=input.mp4 python3 render_example.py 3.0 10.5    -> 해당 시각 프레임만 prev_*.jpg 로 미리보기
# 새 영상에서는 장면(add 호출), SUBS, KF, CROP_CARD 만 바꿔서 쓴다.
import subprocess, sys, math, os, json, numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

SRC = os.environ.get("SRC", "input.mp4")
W, H, FPS = 1920, 1080, 30
DUR = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", SRC]).decode().strip())
N = int(math.ceil(DUR * FPS))
SW, SH = map(int, subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "csv=p=0:s=x", SRC]).decode().strip().split("x"))
S = 2  # supersample for sprites
PREVIEW = [float(x) for x in sys.argv[1:]]  # times to dump as png instead of full render

FD = "/usr/share/fonts/opentype/noto/NotoSansCJK-%s.ttc"
_fc = {}
def F(weight, size):
    k = (weight, size)
    if k not in _fc:
        _fc[k] = ImageFont.truetype(FD % weight, size, index=1)  # index 1 = KR
    return _fc[k]

# palette
WHITE = (255, 255, 255)
ACC = (255, 178, 72)      # warm sunset orange
TEAL = (88, 220, 205)
RED = (255, 98, 98)
MUTED = (188, 198, 220)
PANEL = (14, 20, 38)
NAVY = (10, 15, 30)

def ease_out(x): return 1 - (1 - x) ** 3
def ease_in(x): return x ** 3
def ease_io(x): return 4 * x ** 3 if x < .5 else 1 - (-2 * x + 2) ** 3 / 2
def back(x, s=1.7): x -= 1; return x * x * ((s + 1) * x + s) + 1
def clamp(x, a=0., b=1.): return max(a, min(b, x))

# ---------------- sprite builders (draw at 2x, downsample) ----------------
class Cv:
    def __init__(s, w, h):
        s.w, s.h = w, h
        s.im = Image.new("RGBA", (w * S, h * S), (0, 0, 0, 0))
        s.d = ImageDraw.Draw(s.im)
    def done(s):
        return s.im.resize((s.w, s.h), Image.LANCZOS)

def tw(text, font):  # width at 1x
    return font.getlength(text)

def text_sprite(parts, size, weight="Bold", pad=0, shadow=True):
    """parts: str or list of (text,color)."""
    if isinstance(parts, str): parts = [(parts, WHITE)]
    f2 = F(weight, size * S)
    w = int(sum(f2.getlength(t) for t, _ in parts) / S) + pad * 2 + 8
    h = int(size * 1.45) + pad * 2
    c = Cv(w, h)
    x = (pad + 2) * S
    if shadow:
        sh = Image.new("RGBA", c.im.size, (0, 0, 0, 0)); sd = ImageDraw.Draw(sh)
        xx = x
        for t, col in parts:
            sd.text((xx, pad * S + 3 * S), t, font=f2, fill=(0, 0, 0, 150)); xx += f2.getlength(t)
        sh = sh.filter(ImageFilter.GaussianBlur(5 * S))
        c.im.alpha_composite(sh)
    for t, col in parts:
        c.d.text((x, pad * S), t, font=f2, fill=col); x += f2.getlength(t)
    return c.done()

def rrect(d, box, r, fill=None, outline=None, width=1):
    d.rounded_rectangle([v * S for v in box], radius=r * S, fill=fill, outline=outline, width=width * S)

def panel_sprite(w, h, r=24, fill=(14, 20, 38, 205), border=(255, 255, 255, 38), accent=None):
    c = Cv(w, h)
    rrect(c.d, (0, 0, w - 1, h - 1), r, fill=fill, outline=border, width=2)
    if accent:
        c.d.rounded_rectangle([0, 0, 8 * S, h * S - 1], radius=4 * S, fill=accent)
    return c.done()

def pill(text, size=30, fg=NAVY, bg=ACC, padx=26, pady=12, weight="Bold"):
    f = F(weight, size)
    w = int(tw(text, f)) + padx * 2; h = int(size * 1.3) + pady * 2
    c = Cv(w, h)
    rrect(c.d, (0, 0, w - 1, h - 1), h // 2, fill=bg)
    f2 = F(weight, size * S)
    c.d.text((padx * S, (pady - size * 0.12) * S), text, font=f2, fill=fg)
    return c.done()

def circle_icon(size, bg, draw_fn=None, text=None, tcol=NAVY, tsize=None):
    c = Cv(size, size)
    c.d.ellipse([0, 0, size * S - 1, size * S - 1], fill=bg)
    if text:
        ts = tsize or int(size * 0.5)
        f2 = F("Black", ts * S)
        tw2 = f2.getlength(text)
        c.d.text(((size * S - tw2) / 2, (size * S - ts * S * 1.42) / 2), text, font=f2, fill=tcol)
    if draw_fn: draw_fn(c.d, size * S)
    return c.done()

def draw_check(d, s, col=NAVY, w=0.1):
    d.line([(s * .27, s * .52), (s * .44, s * .68), (s * .74, s * .34)], fill=col, width=int(s * w), joint="curve")

def draw_x(d, s, col=WHITE, w=0.1):
    d.line([(s * .3, s * .3), (s * .7, s * .7)], fill=col, width=int(s * w))
    d.line([(s * .7, s * .3), (s * .3, s * .7)], fill=col, width=int(s * w))

def person_sprite(size, col, label=None, mood=None):
    h = int(size * 1.25) + (50 if label else 0)
    c = Cv(size, h)
    d = c.d; s = size * S
    hr = s * .2
    d.ellipse([s / 2 - hr, s * .06, s / 2 + hr, s * .06 + 2 * hr], fill=col)
    d.chord([s * .14, s * .52, s * .86, s * 1.22], 180, 360, fill=col)
    d.rectangle([s * .14, s * .86, s * .86, s * 1.0], fill=col)
    if mood:  # simple face
        ey = s * .06 + hr * .85
        d.ellipse([s / 2 - hr * .5 - 6 * S, ey - 5 * S, s / 2 - hr * .5 + 6 * S, ey + 7 * S], fill=NAVY)
        d.ellipse([s / 2 + hr * .5 - 6 * S, ey - 5 * S, s / 2 + hr * .5 + 6 * S, ey + 7 * S], fill=NAVY)
        my = s * .06 + hr * 1.4
        if mood == "sad":
            d.arc([s / 2 - hr * .5, my, s / 2 + hr * .5, my + hr * .6], 200, 340, fill=NAVY, width=int(5 * S))
        else:
            d.arc([s / 2 - hr * .5, my - hr * .35, s / 2 + hr * .5, my + hr * .25], 20, 160, fill=NAVY, width=int(5 * S))
    if label:
        f2 = F("Bold", 30 * S)
        lw = f2.getlength(label)
        d.text(((s - lw) / 2, size * 1.25 * S + 4 * S), label, font=f2, fill=WHITE)
    return c.done()

def heart_sprite(size, col=RED):
    c = Cv(size, size); s = size * S; d = c.d
    r = s * .26
    d.ellipse([s * .5 - 2 * r + s * .02, s * .18, s * .5 + s * .02, s * .18 + 2 * r], fill=col)
    d.ellipse([s * .5 - s * .02, s * .18, s * .5 + 2 * r - s * .02, s * .18 + 2 * r], fill=col)
    d.polygon([(s * .5 - 2 * r + s * .035, s * .18 + r * 1.25), (s * .5 + 2 * r - s * .035, s * .18 + r * 1.25), (s * .5, s * .92)], fill=col)
    return c.done()

def arrow_sprite(w, h=40, col=ACC, dashed=False):
    c = Cv(w, h); s = S; d = c.d
    y = h * s / 2
    if dashed:
        x = 0
        while x < (w - 30) * s:
            d.line([(x, y), (min(x + 16 * s, (w - 30) * s), y)], fill=col, width=6 * s); x += 28 * s
    else:
        d.line([(0, y), ((w - 26) * s, y)], fill=col, width=6 * s)
    d.polygon([((w - 34) * s, y - 16 * s), (w * s - 2, y), ((w - 34) * s, y + 16 * s)], fill=col)
    return c.done()

def bubble_sprite(text, size=30, bg=(255, 255, 255, 235), fg=NAVY, tail="left"):
    f = F("Bold", size)
    w = int(tw(text, f)) + 56; h = int(size * 1.3) + 34
    c = Cv(w, h + 18); d = c.d
    rrect(d, (0, 0, w - 1, h - 1), 26, fill=bg)
    if tail == "left":
        d.polygon([(28 * S, (h - 2) * S), (58 * S, (h - 2) * S), (24 * S, (h + 17) * S)], fill=bg)
    else:
        d.polygon([((w - 58) * S, (h - 2) * S), ((w - 28) * S, (h - 2) * S), ((w - 24) * S, (h + 17) * S)], fill=bg)
    d.text((28 * S, (17 - size * .12) * S), text, font=F("Bold", size * S), fill=fg)
    return c.done()

def search_bar(text, cursor=True, w=760, h=96):
    c = Cv(w, h); d = c.d
    rrect(d, (0, 0, w - 1, h - 1), h // 2, fill=(255, 255, 255, 245))
    # magnifier
    cx, cy, r = 54 * S, h / 2 * S, 17 * S
    d.ellipse([cx - r, cy - r - 3 * S, cx + r, cy + r - 3 * S], outline=(90, 100, 125), width=5 * S)
    d.line([(cx + r * .7, cy + r * .7 - 3 * S), (cx + r * 1.5, cy + r * 1.5 - 3 * S)], fill=(90, 100, 125), width=6 * S)
    f2 = F("Medium", 36 * S)
    d.text((100 * S, (h / 2 - 27) * S), text, font=f2, fill=(30, 36, 52))
    if cursor:
        x = 100 * S + f2.getlength(text) + 6 * S
        d.line([(x, (h / 2 - 22) * S), (x, (h / 2 + 22) * S)], fill=(40, 120, 255), width=4 * S)
    # button
    rrect(d, (w - 150, 14, w - 16, h - 14), (h - 28) // 2, fill=(40, 120, 255))
    f3 = F("Bold", 28 * S)
    d.text(((w - 83) * S - f3.getlength("검색") / 2, (h / 2 - 21) * S), "검색", font=f3, fill=WHITE)
    return c.done()

def tip_card(num, title, sub, w=820, h=136, col=ACC):
    c = Cv(w, h); d = c.d
    rrect(d, (0, 0, w - 1, h - 1), 24, fill=(14, 20, 38, 215), outline=(255, 255, 255, 40), width=2)
    r = 40
    cx, cy = 34 + r, h / 2
    d.ellipse([(cx - r) * S, (cy - r) * S, (cx + r) * S, (cy + r) * S], fill=col)
    fn = F("Black", 44 * S)
    d.text((cx * S - fn.getlength(num) / 2, (cy - 32) * S), num, font=fn, fill=NAVY)
    d.text((140 * S, 20 * S), title, font=F("Bold", 44 * S), fill=WHITE)
    d.text((140 * S, 84 * S), sub, font=F("Regular", 27 * S), fill=MUTED)
    return c.done()

def step_row(icon, text, w=820, h=104, col=RED, sub=None):
    c = Cv(w, h); d = c.d
    rrect(d, (0, 0, w - 1, h - 1), 22, fill=(14, 20, 38, 210), outline=(255, 255, 255, 36), width=2)
    ic = icon.resize((64, 64), Image.LANCZOS)
    im = c.done()
    im.alpha_composite(ic, (24, (h - 64) // 2))
    t = text_sprite(text, 40, "Bold", shadow=False)
    im.alpha_composite(t, (110, (h - t.height) // 2 + 2))
    return im

def underline_fn(w, col=ACC, h=12):
    cache = {}
    def f(t, t0):
        p = ease_io(clamp((t - t0) / 0.6))
        k = int(p * 40)
        if k not in cache:
            ww = max(2, int(w * k / 40))
            c = Cv(w, h); rrect(c.d, (0, 0, ww - 1, h - 1), h // 2, fill=col); cache[k] = c.done()
        return cache[k]
    return f

# ---------------- element system ----------------
class El:
    def __init__(s, t0, t1, spr, x, y, anim="up", dur=0.45, out=0.35, center=False):
        s.t0, s.t1, s.spr, s.anim, s.dur, s.out = t0, t1, spr, anim, dur, out
        s.x, s.y, s.center = x, y, center

def apply_alpha(im, a):
    if a >= 0.999: return im
    im = im.copy()
    A = np.asarray(im.getchannel("A"), dtype=np.float32) * a
    im.putalpha(Image.fromarray(A.astype(np.uint8)))
    return im

def draw_el(base, e, t):
    if t < e.t0 or t > e.t1 + e.out: return
    pin = clamp((t - e.t0) / e.dur); pout = clamp((t - e.t1) / e.out)
    eo = ease_out(pin)
    a = clamp(pin * 1.6) * (1 - ease_in(pout))
    spr = e.spr(t, e.t0) if callable(e.spr) else e.spr
    x, y = e.x, e.y
    if e.center: x -= spr.width / 2
    dx = dy = 0
    if e.anim == "up": dy = (1 - eo) * 40 - pout * 20
    elif e.anim == "left": dx = -(1 - eo) * 60
    elif e.anim == "right": dx = (1 - eo) * 60
    elif e.anim == "pop":
        sc = 0.5 + 0.5 * back(pin) if pin < 1 else 1.0
        sc *= (1 - 0.15 * pout)
        if abs(sc - 1) > 0.005:
            nw, nh = max(1, int(spr.width * sc)), max(1, int(spr.height * sc))
            x += (spr.width - nw) / 2; y += (spr.height - nh) / 2
            spr = spr.resize((nw, nh), Image.BILINEAR)
    spr = apply_alpha(spr, a)
    px, py = int(round(x + dx)), int(round(y + dy))
    # clip into canvas
    cx0, cy0 = max(0, -px), max(0, -py)
    if cx0 or cy0: spr = spr.crop((cx0, cy0, spr.width, spr.height)); px += cx0; py += cy0
    if px >= W or py >= H: return
    base.alpha_composite(spr, (px, py))

ELS = []
def add(*a, **k): ELS.append(El(*a, **k))

LX = 110  # left column x for card-mode graphics

# --- S0 intro (full mode) ---
add(0.25, 3.35, pill("AI 활용 TIP", 28), 90, 70, "left")
add(0.45, 3.35, text_sprite([("AI, ", ACC), ("검색 말고 ", WHITE), ("대화", ACC), ("하세요", WHITE)], 76, "Black"), 82, 122, "left")
name_panel = panel_sprite(420, 120, 22, accent=ACC)
add(2.15, 3.45, name_panel, 90, 770, "left")
add(2.3, 3.45, text_sprite("이용식", 56, "Black", shadow=False), 128, 790, "left")

# --- S1 AI 생활화 (4.1-6.95) ---
add(4.15, 6.95, text_sprite("요즘 우리는", 40, "Medium"), LX, 170, "up")
add(4.45, 6.95, text_sprite([("AI", ACC), ("를 ", WHITE), ("생활화", ACC), (" 하고 있습니다", WHITE)], 62, "Black"), LX - 4, 228, "up")
days = ["월", "화", "수", "목", "금", "토", "일"]
for i, dname in enumerate(days):
    t0 = 5.0 + i * 0.13
    add(t0, 6.95, circle_icon(92, (255, 255, 255, 30) if False else (40, 52, 84), text=dname, tcol=WHITE, tsize=38), LX + i * 112, 420, "pop")
    add(t0 + 0.25, 6.95, circle_icon(40, TEAL, draw_fn=lambda d, s: draw_check(d, s, NAVY, .13)), LX + i * 112 + 56, 400, "pop")
add(5.6, 6.95, text_sprite([("매일 ", WHITE), ("AI", TEAL), ("와 함께", WHITE)], 44, "Bold"), LX, 560, "up")

# --- S2 검색 엔진처럼 (7.0-15.1) ---
add(7.05, 15.1, text_sprite("그런데 우리는 AI를", 40, "Medium"), LX, 150, "up")
add(10.1, 15.1, text_sprite([("검색 엔진", ACC), ("처럼 씁니다", WHITE)], 66, "Black"), LX - 4, 206, "up")
query = "AI 잘 쓰는 법"
_sb = {}
def sb_fn(t, t0):
    k = int(clamp((t - 8.3) / 1.6) * len(query))
    blink = (int(t * 2.2) % 2 == 0) or k < len(query)
    key = (k, blink)
    if key not in _sb: _sb[key] = search_bar(query[:k], blink)
    return _sb[key]
add(7.9, 15.1, sb_fn, LX, 360, "pop")
add(13.17, 15.1, pill("구글", 36, WHITE, (66, 133, 244), 34, 14), LX, 520, "pop")
add(13.47, 15.1, pill("네이버", 36, WHITE, (3, 199, 90), 34, 14), LX + 170, 520, "pop")
add(13.8, 15.1, text_sprite("처럼 사용", 40, "Bold"), LX + 382, 528, "left")
add(11.0, 15.1, text_sprite("필요할 때만 묻고 → 답만 받기", 34, "Regular", shadow=False), LX + 6, 660, "up")

# --- S3 대화식으로 (15.17-19.95) ---
add(15.2, 19.95, text_sprite("그게 아니라,", 40, "Medium"), LX, 150, "up")
add(17.25, 19.95, text_sprite([("AI", ACC), ("와 ", WHITE), ("대화식", ACC), ("으로!", WHITE)], 70, "Black"), LX - 4, 206, "up")
boxA = panel_sprite(300, 200, 26)
add(15.4, 19.95, boxA, LX, 360, "pop")
add(15.5, 19.95, circle_icon(80, (60, 70, 100), draw_fn=lambda d, s: (d.ellipse([s*.28, s*.24, s*.62, s*.58], outline=WHITE, width=int(s*.07)), d.line([(s*.57, s*.53), (s*.74, s*.7)], fill=WHITE, width=int(s*.08)))), LX + 110, 384, "pop")
add(15.6, 19.95, text_sprite("검색", 40, "Bold", shadow=False), LX + 110, 478, "up")
add(16.0, 19.95, circle_icon(84, RED, draw_fn=lambda d, s: draw_x(d, s, WHITE, .12)), LX + 236, 330, "pop")
add(16.3, 19.95, arrow_sprite(130), LX + 330, 440, "left")
boxB = panel_sprite(360, 200, 26, fill=(255, 178, 72, 60), border=(255, 178, 72, 200))
add(16.5, 19.95, boxB, LX + 490, 360, "pop")
add(16.8, 19.95, bubble_sprite("요즘 어때?", 26, tail="left"), LX + 512, 378, "pop")
add(17.6, 19.95, bubble_sprite("좋아요!", 26, bg=(255, 178, 72, 245), tail="right"), LX + 680, 460, "pop")
add(18.5, 19.95, text_sprite([("평소에", TEAL), (" 대화하는 습관", WHITE)], 40, "Bold"), LX, 620, "up")

# --- S4 사람 사이 (20.09-30.55) ---
add(20.12, 30.55, text_sprite("사람 사이에서도", 40, "Medium"), LX, 130, "up")
add(20.4, 30.55, person_sprite(120, (210, 220, 240), "나"), LX + 40, 200, "pop")
add(20.6, 30.55, person_sprite(120, (210, 220, 240), "상대방"), LX + 520, 200, "pop")
add(22.3, 30.55, arrow_sprite(250, col=MUTED, dashed=True), LX + 210, 270, "left")
add(22.83, 30.55, bubble_sprite("부탁해!", 28, tail="left"), LX + 225, 182, "pop")
add(24.6, 30.55, person_sprite(120, (255, 140, 140), None, "sad"), LX + 520, 200, "pop", dur=0.3)
warn = circle_icon(64, RED, text="!", tcol=WHITE, tsize=40)
add(21.67, 30.55, step_row(warn, "필요할 때만 요구하고 부탁하면"), LX, 430, "left")
add(24.49, 30.55, step_row(warn, "상대방은 싫어하고"), LX, 552, "left")
add(28.41, 30.55, step_row(warn, "돌아오는 대답도 시원찮다"), LX, 674, "left")

# --- S5 평소에 잘 지내면 (30.65-40.9) ---
add(30.68, 40.9, text_sprite("하지만", 40, "Medium"), LX, 130, "up")
add(31.0, 40.9, person_sprite(120, (210, 220, 240), "나", "happy"), LX + 40, 200, "pop")
add(31.2, 40.9, person_sprite(120, (255, 205, 140), "상대방", "happy"), LX + 520, 200, "pop")
add(32.3, 40.9, heart_sprite(120), LX + 330, 222, "pop")
ok = circle_icon(64, TEAL, draw_fn=lambda d, s: draw_check(d, s, NAVY, .12))
add(31.83, 40.9, step_row(ok, "평소에 늘 잘 지내고"), LX, 430, "left")
add(34.07, 40.9, step_row(ok, "평소처럼 대화하면"), LX, 552, "left")
add(36.37, 40.9, step_row(ok, "내 부탁도 잘 들어준다"), LX, 674, "left")
eq_panel = panel_sprite(660, 120, 26, fill=(255, 178, 72, 235), border=None)
add(38.63, 40.9, eq_panel, LX + 80, 806, "pop")
add(38.7, 40.9, text_sprite([("AI도 ", NAVY), ("마찬가지!", NAVY)], 58, "Black", shadow=False), LX + 140, 814, "pop")

# --- S6 3가지 방법 (40.97-53.95) ---
add(41.0, 53.95, text_sprite([("무조건 ", WHITE), ("요청", RED), ("만 하지 말고", WHITE)], 40, "Medium"), LX, 130, "up")
add(41.5, 53.95, text_sprite([("AI와 ", WHITE), ("대화하는 3가지 방법", ACC)], 62, "Black"), LX - 4, 186, "up")
add(42.83, 53.95, tip_card("1", "AI에게 의견 묻기", "요청만 하지 말고 의견도 물어보기"), LX, 340, "left")
add(45.35, 53.95, tip_card("2", "AI가 나에게 질문하게", "AI가 되묻도록 대화를 열어두기", col=TEAL), LX, 500, "left")
add(49.27, 53.95, tip_card("3", "맥락 제공하기", "더 구체적인 질문으로 이어지게", col=(160, 140, 255)), LX, 660, "left")
add(52.27, 53.95, pill("구체적으로!", 30, NAVY, (160, 140, 255)), LX + 600, 636, "pop")

# --- S7 핵심 (54.05-57.9, full mode) ---
add(54.1, 57.85, text_sprite("이렇게 하는 것이 바로", 42, "Medium"), W / 2, 70, "up", center=True)
key = text_sprite([("AI", ACC), ("를 잘 활용하는 방법", WHITE)], 84, "Black")
add(55.65, 57.85, key, W / 2, 124, "up", center=True)
add(56.3, 57.85, underline_fn(key.width - 40), W / 2, 248, "left", center=True)
for i, (txt, col) in enumerate([("의견 묻기", ACC), ("역질문 받기", TEAL), ("맥락 제공", (160, 140, 255))]):
    sp = pill(txt, 32, NAVY, col)
    add(56.6 + i * 0.18, 57.85, sp, W / 2 - 360 + i * 250 + 10, 840, "pop")

# --- S8 다음 시간 (57.95-62.6) ---
add(58.3, 62.6, pill("NEXT", 30, NAVY, ACC), LX, 170, "pop")
add(58.5, 62.6, text_sprite("그것에 대해", 40, "Medium"), LX, 250, "up")
add(59.03, 62.6, text_sprite([("구체적으로 ", ACC), ("배워봅시다", WHITE)], 70, "Black"), LX - 4, 306, "up")
for i, (txt, col) in enumerate([("의견 묻기", ACC), ("역질문 받기", TEAL), ("맥락 제공", (160, 140, 255))]):
    ic = circle_icon(64, col, text=str(i + 1), tcol=NAVY, tsize=36)
    add(60.43 + i * 0.25, 62.6, step_row(ic, txt, w=560, h=96), LX, 470 + i * 112, "left")

# --- S9 outro (62.7-end, full mode) ---
add(62.85, 66, text_sprite("감사합니다", 96, "Black"), W / 2, 90, "pop", center=True)
add(63.3, 66, text_sprite([("이용식", ACC)], 46, "Bold"), W / 2, 238, "up", center=True)

# ---------------- subtitles ----------------
SUBS = [
    (1.07, 2.20, "안녕하세요."), (2.25, 3.40, "이용식입니다."),
    (4.09, 7.00, "우리가 요즘 AI를 거의 생활화하고 있는데"),
    (7.01, 10.05, "그런데 우리가 이 AI를 쓸 때에"),
    (10.09, 13.10, "거의 그냥 검색 엔진처럼 씁니다."),
    (13.17, 15.15, "구글과 네이버처럼 쓰는데"),
    (15.17, 17.20, "그게 아니라 평소에"),
    (17.25, 19.90, "AI와 대화식으로 해야 되는 것입니다."),
    (20.09, 22.15, "우리가 다른 사람하고도 필요할 때만"),
    (22.19, 24.45, "그 사람한테 요구하고 부탁하면"),
    (24.49, 26.90, "상대방이 싫어하겠지, 그죠?"),
    (27.05, 29.55, "그래서 그 사람 돌아오는 대답도"),
    (29.57, 30.62, "시원찮을 때가 많이 있습니다."),
    (30.65, 33.90, "하지만 평소에 늘 잘 지내면,"),
    (33.97, 35.38, "그냥 평소처럼 대화하면"),
    (35.41, 38.60, "그 사람이 내 부탁도 잘 들어주듯이"),
    (38.63, 40.90, "AI도 바로 마찬가지입니다."),
    (40.97, 42.80, "무조건 요청하지 마시고"),
    (42.83, 44.98, "AI한테 의견도 물어보기도 하고"),
    (45.03, 47.58, "그리고 AI가 나한테 질문하기도 하고"),
    (47.63, 49.24, "그리고 내가 말할 때는"),
    (49.27, 51.80, "맥락을 제공해 가지고"),
    (51.83, 54.00, "좀 더 구체적으로 질문하게 하는 것"),
    (54.05, 55.62, "이렇게 하는 것이 바로"),
    (55.65, 57.92, "AI를 잘 활용하는 방법입니다."),
    (57.95, 60.40, "그것에 대해서 구체적으로"),
    (60.43, 62.88, "배워볼 시간을 갖도록 하겠습니다."),
    (62.93, 64.60, "감사합니다."),
]
_subc = {}
def sub_sprite(text):
    if text not in _subc:
        f2 = F("Bold", 50 * S)
        tw2 = f2.getlength(text) / S
        w, h = int(tw2) + 64, 84
        c = Cv(w, h)
        rrect(c.d, (0, 0, w - 1, h - 1), 18, fill=(0, 0, 0, 165))
        c.d.text((32 * S, (h / 2 - 37) * S), text, font=f2, fill=WHITE, stroke_width=2, stroke_fill=(0, 0, 0))
        _subc[text] = c.done()
    return _subc[text]

def draw_subs(base, t):
    for a, b, txt in SUBS:
        if a - 0.02 <= t <= b + 0.05:
            sp = sub_sprite(txt)
            al = clamp((t - a) / 0.12) * clamp((b + 0.05 - t) / 0.1)
            sp = apply_alpha(sp, al)
            base.alpha_composite(sp, (int(W / 2 - sp.width / 2), H - 56 - sp.height))
            return

# ---------------- layout (full <-> card) ----------------
KF = [(0, 0), (3.55, 0), (4.15, 1), (53.85, 1), (54.4, 0), (57.7, 0), (58.25, 1), (62.55, 1), (63.1, 0), (99, 0)]
def mode(t):
    for (t0, v0), (t1, v1) in zip(KF, KF[1:]):
        if t0 <= t <= t1:
            return v0 + (v1 - v0) * ease_io((t - t0) / (t1 - t0)) if t1 > t0 else v1
    return 0
CARD = (1050, 70, 760, 830)  # x,y,w,h
crop_w = SH * CARD[2] / CARD[3]
CROP_CARD = (650 - crop_w / 2, 0, crop_w, SH)
def lerp(a, b, c): return a + (b - a) * c

_masks = {}
def rmask(w, h, r):
    k = (w, h, r)
    if k not in _masks:
        m = Image.new("L", (w * 2, h * 2), 0)
        ImageDraw.Draw(m).rounded_rectangle([0, 0, w * 2 - 1, h * 2 - 1], radius=r * 2, fill=255)
        _masks[k] = m.resize((w, h), Image.LANCZOS)
    return _masks[k]

vignette = None
def make_vignette():
    y, x = np.mgrid[0:H, 0:W]
    d = np.sqrt(((x - W / 2) / (W / 2)) ** 2 + ((y - H / 2) / (H / 2)) ** 2)
    a = np.clip((d - 0.75) / 0.7, 0, 1) * 120
    v = np.zeros((H, W, 4), np.uint8); v[..., 3] = a.astype(np.uint8)
    return Image.fromarray(v, "RGBA")
vignette = make_vignette()
# soft gradient at top-left for readability in full mode text, and bottom for subs
def make_grad():
    g = np.zeros((H, W, 4), np.uint8)
    yy = np.arange(H)[:, None]; xx = np.arange(W)[None, :]
    a = np.clip(1 - yy / 330, 0, 1) * 150
    g[..., 3] = a.astype(np.uint8)
    return Image.fromarray(g, "RGBA")
topgrad = make_grad()

def compose(src, t):
    c = mode(t)
    if c < 0.001:
        # full-frame with very slow push-in
        z = 1.0 + 0.03 * ((t % 30) / 30)
        cw, ch = SW / z, SH / z
        fr = src.resize((W, H), Image.BILINEAR, box=((SW - cw) / 2, (SH - ch) / 2, (SW + cw) / 2, (SH + ch) / 2))
        base = fr.convert("RGBA")
    else:
        small = src.resize((192, 108), Image.BILINEAR).filter(ImageFilter.GaussianBlur(5))
        bg = small.resize((W, H), Image.BILINEAR).convert("RGBA")
        bg.alpha_composite(Image.new("RGBA", (W, H), (10, 15, 32, int(165 * c))))
        base = bg
        # card rect
        dx, dy = lerp(0, CARD[0], c), lerp(0, CARD[1], c)
        dw, dh = lerp(W, CARD[2], c), lerp(H, CARD[3], c)
        sx, sy = lerp(0, CROP_CARD[0], c), lerp(0, CROP_CARD[1], c)
        sw, sh = lerp(SW, CROP_CARD[2], c), lerp(SH, CROP_CARD[3], c)
        iw, ih = int(round(dw)), int(round(dh))
        fr = src.resize((iw, ih), Image.BILINEAR, box=(sx, sy, sx + sw, sy + sh))
        r = int(30 * c)
        # shadow
        if c > 0.05:
            sm = Image.new("L", (W // 4, H // 4), 0)
            ImageDraw.Draw(sm).rounded_rectangle([dx / 4 + 2, dy / 4 + 4, (dx + dw) / 4 + 2, (dy + dh) / 4 + 6], radius=8, fill=int(170 * c))
            sm = sm.filter(ImageFilter.GaussianBlur(6)).resize((W, H), Image.BILINEAR)
            sh_img = Image.new("RGBA", (W, H), (0, 0, 0, 0)); sh_img.putalpha(sm)
            base.alpha_composite(sh_img)
        frA = fr.convert("RGBA"); frA.putalpha(rmask(iw, ih, max(r, 0)) if r > 0 else Image.new("L", (iw, ih), 255))
        base.alpha_composite(frA, (int(round(dx)), int(round(dy))))
        if c > 0.5:
            bd = Image.new("RGBA", (iw + 8, ih + 8), (0, 0, 0, 0))
            ImageDraw.Draw(bd).rounded_rectangle([1, 1, iw + 6, ih + 6], radius=r + 4, outline=(255, 178, 72, int(220 * (c - .5) * 2)), width=3)
            base.alpha_composite(bd, (int(round(dx)) - 4, int(round(dy)) - 4))
    base.alpha_composite(vignette)
    fullness = 1 - c
    if fullness > 0.01:
        tg = topgrad if fullness > 0.99 else apply_alpha(topgrad, fullness)
        base.alpha_composite(tg)
    for e in ELS: draw_el(base, e, t)
    draw_subs(base, t)
    # final fade to black
    if t > DUR - 0.6:
        base.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, int(255 * clamp((t - (DUR - 0.6)) / 0.6)))))
    if t < 0.4:
        base.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, int(255 * (1 - t / 0.4)))))
    return base.convert("RGB")

# ---------------- run ----------------
dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", SRC, "-vf", "fps=30", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
FS = SW * SH * 3
if PREVIEW:
    targets = sorted(int(p * FPS) for p in PREVIEW); i = 0; last = None
    for fi in range(N):
        buf = dec.stdout.read(FS)
        if len(buf) == FS: last = Image.frombytes("RGB", (SW, SH), buf)
        if fi in targets:
            compose(last, fi / FPS).save(f"prev_{fi/FPS:05.2f}.jpg", quality=85)
        if fi > targets[-1]: break
    dec.kill(); sys.exit()

enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                        "-i", "mix.wav", "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
                        "-pix_fmt", "yuv420p", "-r", "30", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", "out.mp4"],
                       stdin=subprocess.PIPE)
last = None
import time; T0 = time.time()
for fi in range(N):
    buf = dec.stdout.read(FS)
    if len(buf) == FS: last = Image.frombytes("RGB", (SW, SH), buf)
    enc.stdin.write(compose(last, fi / FPS).tobytes())
    if fi % 150 == 0: print(fi, N, f"{time.time()-T0:.0f}s", flush=True)
enc.stdin.close(); enc.wait(); dec.kill()
print("done")
