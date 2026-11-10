#!/usr/bin/env python3
"""kb.py "text with ^ENTER tokens" -> scenario string for scenario.lua (1 key/step). Text chars: A-Z 0-9 space; '=' -> ALT+8, '+' -> ALT+5, '-' -> ALT+3,
'"' -> MAYUSCULAS (der.)+', ',' '.'; newline '\\n' -> INTRO.  Usage: kb.py START_T STEP 'text' """
import sys
def keys(txt):
    out = []
    for ch in txt:
        if ch == '\n': out.append('INTRO')
        elif ch == ' ': out.append('ESPACIO')
        elif ch == '=': out.append('ALT+8')
        elif ch == '+': out.append('ALT+5')
        elif ch == '-': out.append('ALT+3')
        elif ch == '"': out.append("MAYUSCULAS (der.)+'")
        elif ch == ':': out.append('MAYUSCULAS (der.)+;')
        elif ch == '(': out.append('MAYUSCULAS (der.)+9')
        elif ch == ')': out.append('MAYUSCULAS (der.)+0')
        elif ch == '*': out.append('MAYUSCULAS (der.)+8')
        elif ch == '<': out.append('MAYUSCULAS (der.)+RETROCESO')
        elif ch == '>': out.append('MAYUSCULAS (der.)+AVANCE')
        else: out.append(ch.upper())
    return out
if __name__ == '__main__':
    t = float(sys.argv[1]); step = float(sys.argv[2]); s = []
    for k in keys(sys.argv[3].replace('\\n', '\n')):
        s.append('%g:press:%s' % (t, k)); t += step
    print(';'.join(s) + '|%g' % t)
