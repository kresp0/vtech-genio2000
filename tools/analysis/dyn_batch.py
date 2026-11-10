#!/usr/bin/env python3
"""Run scenarios in MAME (genio2000 driver, private ROM) with exec_trace.lua, in parallel; merge into out/mame/merged.*
usage: dyn_batch.py name=scenario[,stop] ...   (scenario syntax: see tools/mame-tests/lua/scenario.lua; set GENIO_MAME_DIR to the MAME working tree)
Evidence class: EMULATION (MAME), not hardware."""
import os, sys, subprocess, concurrent.futures as cf, collections, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
M = os.environ.get("GENIO_MAME_DIR", ".")
OUT = os.path.join(ROOT, "out", "mame"); os.makedirs(OUT, exist_ok=True)
def one(arg):
    name, rest = arg.split("=", 1)
    scen, _, stop = rest.rpartition("@") if "@" in rest else (rest, "", "30")
    d = tempfile.mkdtemp(prefix="dyn_", dir="/dev/shm")
    env = dict(os.environ, GENIO_SCEN=scen, GENIO_STOP=stop, GENIO_OUT=os.path.join(OUT, name), GENIO_HOLD=os.environ.get("GENIO_HOLD", "0.4"))
    cmd = [M + "/mame/genio", "genio2000", "-rompath", M + "/roms_local", "-homepath", d + "/h", "-cfg_directory", d + "/c", "-nvram_directory", d + "/n",
           "-snapshot_directory", os.path.join(OUT, "snap_" + name), "-video", "none", "-sound", "none", "-seconds_to_run", str(int(float(stop)) + 3),
           "-nothrottle", "-skip_gameinfo", "-autoboot_script", os.path.join(HERE, "exec_trace.lua")]
    p = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=1800)
    return name, p.returncode
if __name__ == "__main__":
    with cf.ThreadPoolExecutor(6) as ex:
        for r in ex.map(one, sys.argv[1:]): print(r)
