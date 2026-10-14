import numpy as np, wave
SR = 48000
import sys
DUR = float(sys.argv[1]) if len(sys.argv) > 1 else 66.0  # 사용법: python3 bgm.py <영상길이초+0.5>
BPM = 96
beat = 60 / BPM
bar = beat * 4
n = int(SR * DUR)
L = np.zeros(n); R = np.zeros(n)

def midi(m): return 440 * 2 ** ((m - 69) / 12)

# Fmaj7 - G6 - Em7 - Am7 (warm, positive)
chords = [[53, 57, 60, 64], [55, 59, 62, 64], [52, 55, 59, 62], [57, 60, 64, 67]]
roots = [41, 43, 40, 45]

def add(buf, start, sig):
    i = int(start * SR)
    if i >= n: return
    j = min(n, i + len(sig))
    buf[i:j] += sig[:j - i]

def lowpass(x, a):
    y = np.zeros_like(x); acc = 0.0
    # vectorised one-pole via scipy-free cumulative approach (loop in chunks)
    for k in range(len(x)):
        acc += a * (x[k] - acc); y[k] = acc
    return y

t_bar = np.arange(int(bar * SR)) / SR
# Pad: detuned saws, soft envelope, per bar
for b in range(int(DUR / bar) + 1):
    ch = chords[b % 4]
    sig = np.zeros(len(t_bar))
    for m in ch:
        f = midi(m)
        for det in (-0.12, 0.12):
            ph = (t_bar * f * (1 + det / 100)) % 1.0
            sig += (2 * ph - 1) * 0.5 + np.sin(2 * np.pi * f * t_bar)
    env = np.minimum(1, t_bar / 0.6) * np.minimum(1, (bar - t_bar) / 0.5 + 0.2)
    sig = sig * env * 0.018
    add(L, b * bar, sig); add(R, b * bar, sig)

# smooth pad with cheap moving-average lowpass
k = 24
kern = np.ones(k) / k
L = np.convolve(L, kern, 'same'); R = np.convolve(R, kern, 'same')

# Pluck arpeggio (8ths) from bar 1
tp = np.arange(int(0.6 * SR)) / SR
for b in range(1, int(DUR / bar) + 1):
    ch = chords[b % 4]
    pattern = [0, 1, 2, 3, 2, 1, 2, 3]
    for i, p in enumerate(pattern):
        f = midi(ch[p] + 12)
        s = (np.sin(2 * np.pi * f * tp) + 0.3 * np.sin(4 * np.pi * f * tp)) * np.exp(-tp * 7) * 0.05
        st = b * bar + i * beat / 2
        pan = 0.35 + 0.3 * (i % 2)
        add(L, st, s * (1 - pan)); add(R, st, s * pan)

# Bass (quarters) from bar 2
tb = np.arange(int(beat * SR)) / SR
for b in range(2, int(DUR / bar) + 1):
    f = midi(roots[b % 4])
    for q in range(4):
        s = np.sin(2 * np.pi * f * tb) * np.exp(-tb * 3) * np.minimum(1, tb / 0.01) * 0.10
        add(L, b * bar + q * beat, s); add(R, b * bar + q * beat, s)

# Drums from bar 2: soft kick on 1,3 ; hat on offbeats ; clap-ish on 2,4
tk = np.arange(int(0.35 * SR)) / SR
kick = np.sin(2 * np.pi * (50 * tk + 60 * (1 - np.exp(-tk * 30)) / 30)) * np.exp(-tk * 9) * 0.22
rng = np.random.default_rng(1)
th = np.arange(int(0.06 * SR)) / SR
hatn = rng.standard_normal(len(th)); hatn = np.diff(np.concatenate([[0], hatn]))
hat = hatn * np.exp(-th * 70) * 0.025
tc = np.arange(int(0.2 * SR)) / SR
clap = np.convolve(rng.standard_normal(len(tc)), np.ones(6) / 6, 'same') * np.exp(-tc * 25) * 0.05
for b in range(2, int(DUR / bar) + 1):
    for q in range(4):
        st = b * bar + q * beat
        if q in (0, 2): add(L, st, kick); add(R, st, kick)
        if q in (1, 3): add(L, st, clap * 0.8); add(R, st, clap)
        add(L, st + beat / 2, hat * 0.7); add(R, st + beat / 2, hat)

mix = np.stack([L, R], 1)
mix /= np.max(np.abs(mix)) * 1.12
# fades
fi = int(1.5 * SR); fo = int(3.0 * SR)
mix[:fi] *= np.linspace(0, 1, fi)[:, None]
mix[-fo:] *= np.linspace(1, 0, fo)[:, None]
data = (mix * 32767).astype(np.int16)
w = wave.open('bgm.wav', 'wb'); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
w.writeframes(data.tobytes()); w.close()
print('ok')
