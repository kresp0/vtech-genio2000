#!/usr/bin/env python3
"""wav_compare.py <emulator.wav> <recording.wav> [...]  – compare a recording of the real unit with an emulator capture of the same boot melody.
Per recording: note onsets (band-passed 350-2500 Hz RMS envelope, threshold 25 % of the 99th percentile, gaps < 25 ms bridged, notes < 60 ms dropped),
least-squares time scale  real/emu  of the onset sequence (first 3.2 s of the real melody), and the ratio of the Welch spectral peak (250-1500 Hz)
of every real note to that of the emulator note whose scaled onset is nearest (< 60 ms).  Zero-crossing/autocorrelation pitch is NOT used: it gives
octave errors on microphone recordings.  Only RATIOS are meaningful (recorder gain/speed unknown).  Output: text, one block per recording."""
import sys, numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfiltfilt, welch
def load(f):
    sr, x = wavfile.read(f); x = x.astype(float)
    return sr, (x.mean(1) if x.ndim > 1 else x)
def segs(f, lo=350, hi=2500, win=0.01):
    sr, x = load(f)
    y = sosfiltfilt(butter(4, [lo, hi], 'band', fs=sr, output='sos'), x)
    n = int(sr * win); env = np.array([np.sqrt(np.mean(y[i:i + n] ** 2)) for i in range(0, len(y) - n, n)])
    on = env > 0.25 * np.percentile(env, 99); out = []; i = 0
    while i < len(on):
        if on[i]:
            j = i
            while j < len(on) and on[j]: j += 1
            out.append([i, j]); i = j
        else: i += 1
    m = []
    for s, e in out:
        if m and (s - m[-1][1]) * win < 0.025: m[-1][1] = e
        else: m.append([s, e])
    return sr, x, [(s * win, e * win) for s, e in m if 0.06 <= (e - s) * win < 1.5]
def peak(sr, x, s, e):
    seg = x[int(s * sr):int(e * sr)]; f, p = welch(seg, sr, nperseg=min(len(seg), 8192)); k = (f > 250) & (f < 1500); return f[k][p[k].argmax()]
sr0, x0, m0 = segs(sys.argv[1]); t0 = m0[0][0]; emu = np.array([a - t0 for a, b in m0])
print('emulator capture %s: %d notes, onsets %s' % (sys.argv[1], len(emu), np.round(emu, 2).tolist()))
for f in sys.argv[2:]:
    sr, x, m = segs(f); keep = [q for q in m if q[0] - m[0][0] < 3.2]; on = np.array([a - keep[0][0] for a, b in keep])
    best = min(((np.sum(np.minimum([np.min(np.abs(emu * sc - a)) for a in on], 0.1) ** 2), sc) for sc in np.arange(0.5, 1.0001, 0.002)))
    sc = best[1]; rms = 1000 * np.sqrt(best[0] / len(on))
    pr = []
    for (a, b), o in zip(keep, on):
        j = int(np.argmin(np.abs(emu * sc - o)))
        if abs(emu[j] * sc - o) < 0.06: pr.append(peak(sr, x, a, b) / peak(sr0, x0, m0[j][0], m0[j][1]))
    print('%s\n  real notes %d, onsets %s\n  time scale real/emu = %.3f  (speed ratio %.3f), rms onset misfit %.0f ms\n  spectral-peak ratio real/emu over %d matched notes: %s  median %.2f'
          % (f, len(on), np.round(on, 2).tolist(), sc, 1 / sc, rms, len(pr), np.round(pr, 2).tolist(), np.median(pr) if pr else float('nan')))
