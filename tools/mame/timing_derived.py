#!/usr/bin/env python3
"""timing_derived.py  – combines logs/timing/video/events.csv (hardware, read by eye) with logs/timing/emulation/*/summary.json (MAME) and prints the derived numbers
used in the documentation.  Run from the project root.  The video numbers carry ~ +-0.05 s (frame step 1/60 s, LCD fade latency not measured)."""
import csv, json, glob, os
ev = {(r['file'], r['event']): float(r['video_time_s']) for r in csv.DictReader(open('logs/timing/video/events.csv'))}
emu = {os.path.basename(os.path.dirname(p)): json.load(open(p)) for p in glob.glob('logs/timing/emulation/*/summary.json')}
g = lambda f, e: ev[(f, e)]
pause = g('on.mov', 'first_char_visible') - g('on.mov', 'title_first_visible')
span = g('on.mov', 'last_char_visible') - g('on.mov', 'first_char_visible')
mel = g('on.mov', 'audio_last_run_end') - g('on.mov', 'audio_first_run_start')
snd = g('off.mov', 'audio_run_end') - g('off.mov', 'audio_run_start')
b4, b6, o4, o6 = (emu[k] for k in ('boot_clk4.0MHz_irq50Hz', 'boot_clk6.0MHz_irq50Hz', 'off_clk4.0MHz_irq50Hz', 'off_clk6.0MHz_irq50Hz'))
ticks = b4['typing_span'] * 50
print('HW (video)   title->first char      %.2f s   | MAME 4 MHz %.2f  MAME 6 MHz %.2f' % (pause, b4['title_to_first_char'], b6['title_to_first_char']))
print('HW (video)   welcome typing span    %.2f s   | MAME 4 MHz %.2f  MAME 6 MHz %.2f  (MAME: %.1f ticks of the periodic interrupt at any clock)' % (span, b4['typing_span'], b6['typing_span'], ticks))
print('  -> interrupt rate if the span is %.0f ticks: %.1f Hz  (video-only range for +-0.05 s per edge: %.1f-%.1f Hz)' % (ticks, ticks / span, ticks / (span + .1), ticks / (span - .1)))
print('HW (video audio) boot melody span   %.2f s   | MAME 4 MHz %.2f  MAME 6 MHz %.2f   (MAME span = first to last write of port 0x12)' % (mel, b4['melody_span'], b6['melody_span']))
print('HW (video audio) farewell sound     %.2f s   | MAME 4 MHz %.2f  MAME 6 MHz %.2f   (MAME span = keypress write to OUT (12h),01)' % (snd, o4['sound_span'], o6['sound_span']))
print('HW (video)   message visible        %.2f -> dark %.2f (%.2f s)' % (g('off.mov', 'message_first_visible'), g('off.mov', 'screen_dark'), g('off.mov', 'screen_dark') - g('off.mov', 'message_first_visible')))
print('speed ratios HW/MAME4: pause %.2f  melody %.2f  farewell %.2f   (HW/MAME6: %.2f %.2f %.2f)' % (b4['title_to_first_char'] / pause, b4['melody_span'] / mel, o4['sound_span'] / snd, b6['title_to_first_char'] / pause, b6['melody_span'] / mel, o6['sound_span'] / snd))
