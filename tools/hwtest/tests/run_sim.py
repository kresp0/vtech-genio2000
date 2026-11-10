#!/usr/bin/env python3
"""run_sim.py [ye|ga] -> runs the built image in sim_hw with the default model, writes build/sim_<variant>/capture.* and analyses it with hwtest_rx."""
import os, sys, time, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); HW = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import sim_hw
variant = sys.argv[1] if len(sys.argv) > 1 else 'ye'
image = open(os.path.join(HW, 'build', variant, 'hwtest_%s_AT28C256_32K.bin' % variant), 'rb').read()
rom = open(os.path.join(os.path.dirname(HW), 'rom', 'genio2000_es_128k.bin'), 'rb').read()
t = time.time()
R = sim_hw.run(image, rom, variant=variant)
out = os.path.join(HW, 'build', 'sim_' + variant)
sim_hw.write_capture(R, out)
print('instr %d  bytes %d  synthetic time %.1fs  wall %.1fs  keys left %d  pc outside %s  rom writes %s  LCD-port reads %s' % (
    R.instr, len(R.cap), R.t, time.time() - t, R.keys_left, [hex(x) for x in R.pc_outside[:3]], R.rom_writes[:3], R.bad_ports[:3]))
print('final screen:', R.screen)
print('port writes (distinct, excluding LCD/key ports):', sorted({(p, v) for p, v in R.port_writes if p not in (0x0A, 0x0B, 0x10, 0x11, 0x12)}))
