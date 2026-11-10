#!/usr/bin/env python3
"""video_audio_runs.py <video.mov> -> sound runs of the audio track (RMS in 10 ms windows > max(5 x median of the first 1.5 s, 40), gaps < 150 ms merged), video time in s."""
import sys, subprocess, tempfile, os, numpy as np
from scipy.io import wavfile
t = tempfile.mkdtemp(); w = os.path.join(t, 'a.wav')
subprocess.run(['ffmpeg', '-v', 'error', '-i', sys.argv[1], '-map', '0:a:0', '-ac', '1', '-ar', '16000', w, '-y'], check=True)
sr, x = wavfile.read(w); x = x.astype(float); n = int(sr * .01)
e = np.array([np.sqrt(np.mean(x[i:i + n] ** 2)) for i in range(0, len(x) - n, n)])
base = np.median(e[:150]); on = e > max(5 * base, 40); runs = []; i = 0
while i < len(on):
    if on[i]:
        j = i
        while j < len(on) and on[j]: j += 1
        if runs and (i - runs[-1][1]) < 15: runs[-1][1] = j
        else: runs.append([i, j])
        i = j
    else: i += 1
print('%s baseline_rms %.0f runs(s) %s' % (sys.argv[1], base, [(round(a / 100, 2), round(b / 100, 2)) for a, b in runs]))
os.remove(w); os.rmdir(t)
