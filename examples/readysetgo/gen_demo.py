#!/usr/bin/env python3
"""readysetgo: generates engine.h (the player loop), song.h (the music) and scenes.h (event streams, glyphs, segments)."""
import gen_engine, gen_music, gen_scenes
from gen_engine import UNIT_S

def main():
    gen_engine.write_engine()
    songs, pats = gen_music.build(gen_scenes.typing_times())
    msize = gen_music.write_song(songs, pats)
    infos, csize, su, mqs, mql = gen_scenes.write_scenes(songs, pats)
    esize = sum(i['size'] for i in infos)
    total = 0
    for i in infos:
        sec = su['song_' + i['name']] * UNIT_S
        total += sec
        print('%-8s %6.2f s  %4d records  %5d bytes  latest step %.1f ms late' % (i['name'], sec, i['recs'], i['size'], i['late_ms']))
    print('marquee: %d steps, text %d bytes' % (mqs, mql))
    print('music %d bytes, events %d bytes, glyph halves %d bytes (%d), one pass %.1f s' % (msize, esize, csize, csize // 32, total))

if __name__ == '__main__':
    main()
