#!/usr/bin/env python3
"""Segment a mono/stereo WAV into notes and report pitch + duration, to compare an EMULATOR capture with a RECORDING of the real unit.
  wav_notes.py a.wav [b.wav]            -> note table(s); with two files also onset-to-onset tempo ratio and pitch ratio per note
Pitch = mean repetition rate by crossing count (comparable with the emulator edge log; the spectral peak of an interrupted tone is biased upwards).  Segmentation = RMS envelope.
A real recording needs: quiet room, phone 5-10 cm from the speaker, 44.1/48 kHz, no AGC if possible.  Only RATIOS between the two
files are meaningful if the recorder gain/speed is uncertain; ratios of pitch and of durations jointly tell the effective-clock ratio."""
import sys, numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfiltfilt
def load(p):
    sr, x = wavfile.read(p); x = x.astype(float)
    if x.ndim > 1: x = x.mean(1)
    return sr, x / (np.abs(x).max() or 1)
def notes(p, win=0.01, thr=0.15, min_dur=0.04, fmin=60, fmax=4000):
    sr, x = load(p); n = int(sr * win)
    env = np.array([np.sqrt(np.mean(x[i:i + n] ** 2)) for i in range(0, len(x) - n, n)])
    on = env > thr * env.max(); out = []; i = 0
    while i < len(on):
        if on[i]:
            j = i
            while j < len(on) and on[j]: j += 1
            # bridge tiny gaps (< 20 ms) handled by min_dur filtering on merged runs
            out.append([i, j]); i = j
        else: i += 1
    merged = []
    for s, e in out:
        if merged and (s - merged[-1][1]) * win < 0.03: merged[-1][1] = e
        else: merged.append([s, e])
    res = []
    for s, e in merged:
        d = (e - s) * win
        if d < min_dur: continue
        seg = x[int(s * n + 0.2 * (e - s) * n): int(e * n - 0.1 * (e - s) * n)]
        if len(seg) < 256: continue
        w = np.hanning(len(seg)); N = 1 << int(np.ceil(np.log2(len(seg) * 8)))
        sp = np.abs(np.fft.rfft(seg * w, N)); fr = np.fft.rfftfreq(N, 1 / sr)
        m = (fr > fmin) & (fr < fmax); k = np.argmax(sp * m)
        if 0 < k < len(sp) - 1:
            a, b, c = np.log(sp[k - 1:k + 2] + 1e-12); k = k + 0.5 * (a - c) / (a - 2 * b + c)
        res.append((s * win, d, avg_freq(x, sr, s * n, e * n)))
    return res
def avg_freq(x, sr, a, b):
    """Mean repetition rate = rising zero crossings of the 80-1500 Hz band-passed signal / time (meaningful for the 1-bit sound model and for a real recording; NOT for the gated 3250 Hz beeper model) (what an oscilloscope-style edge count gives; includes
    the pauses caused by interrupts, exactly like the edge log of the emulator, tests/lua/port12_log.lua).  Works for a gated carrier too."""
    seg = x[int(a):int(b)]; sos = butter(2, [80, min(1500, sr / 2 * 0.8)], 'band', fs=sr, output='sos')
    y = sosfiltfilt(sos, seg)
    up = np.where((y[:-1] < 0) & (y[1:] >= 0))[0]
    if len(up) < 3: return 0.0
    return (len(up) - 1) * sr / (up[-1] - up[0])
def main(a):
    tabs = [notes(p) for p in a]
    for p, t in zip(a, tabs):
        print(p)
        for i, (t0, d, f) in enumerate(t): print('  note %2d  onset %.3f s  dur %.3f s  f_avg %.1f Hz' % (i, t0, d, f))
    if len(tabs) == 2 and tabs[0] and tabs[1]:
        n = min(len(tabs[0]), len(tabs[1])); A, B = tabs[0][:n], tabs[1][:n]
        pr = [b[2] / a_[2] for a_, b in zip(A, B)]; dr = [a_[1] / b[1] for a_, b in zip(A, B)]
        io = [(B[i + 1][0] - B[i][0]) / (A[i + 1][0] - A[i][0]) for i in range(n - 1)]
        print('pitch ratio B/A per note:', ' '.join('%.3f' % x for x in pr))
        print('duration ratio A/B per note:', ' '.join('%.3f' % x for x in dr))
        print('median pitch ratio %.4f   median duration ratio %.4f   median inter-onset ratio A/B %.4f' % (np.median(pr), np.median(dr), 1 / np.median(io) if io else float('nan')))
        print('(if the emulator is A and the real unit is B and both quantities agree, the real unit runs at that EFFECTIVE-clock ratio relative to the emulator)')
if __name__ == '__main__': main(sys.argv[1:])
