#!/usr/bin/env python3
"""timing_summary.py <boot|off> <log> [press_time]  -> one JSON object with the key emulated events of a timing_log.lua log (EMU)."""
import sys, json
mode, path = sys.argv[1], sys.argv[2]
press = float(sys.argv[3]) if len(sys.argv) > 3 else 20.0
ev = [(float(a), k, int(v, 16)) for a, k, v in (l.split() for l in open(path))]
dr = [(t, v) for t, k, v in ev if k == 'DR']; p12 = [(t, v) for t, k, v in ev if k == 'P12']
r = {}
if mode == 'boot':
    a9 = [t for t, v in dr if v == 0xA9][0]; d_last = [t for t, v in dr if v == 0x64][-1]
    pre = [t for t, v in p12 if t < a9]
    r = dict(lcd_first_data=dr[0][0], first_p12_write=p12[0][0], last_p12_write_before_first_char=pre[-1], melody_span=pre[-1] - p12[0][0],
             first_char_A9=a9, last_char_d=d_last, title_to_first_char=a9 - dr[0][0], typing_span=d_last - a9)
else:
    dr2 = [t for t, v in dr if t >= press]; q = [(t, v) for t, v in p12 if t >= press]
    final = [t for t, v in q if v == 0x01][-1]; first = q[0][0]
    r = dict(press=press, message_first_data=dr2[0] if dr2 else None, first_p12_write=first, final_poweroff_write=final, sound_span=final - first,
             message_delay=(dr2[0] - press) if dr2 else None)
r = {k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()}
print(json.dumps(r))
