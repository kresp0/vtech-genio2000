-- Timing log for the boot / power-off comparisons.  Runs the scripted scenario (GENIO_SCEN, see scenario.lua) and logs, with the
-- emulated time of each write:  "<t> IR <v>" (HD44780 instruction), "<t> DR <v>" (HD44780 data), "<t> P12 <v>" (port 0x12).
-- Env: GENIO_LUADIR (directory of the Lua scripts), GENIO_LOG (output file), GENIO_SCEN, GENIO_HOLD.
dofile((os.getenv("GENIO_LUADIR") or "tests/lua") .. "/scenario.lua")
local machine = manager.machine
local ios = machine.devices[":maincpu"].spaces["io"]
local out = io.open(os.getenv("GENIO_LOG"), "w"); out:setvbuf("line")
-- the taps must stay referenced (globals), otherwise they are garbage collected and logging silently stops
TAP_LCD = ios:install_write_tap(0x0a, 0x0b, "lcd", function(o, d, m)
  out:write(string.format("%.6f %s %02X\n", machine.time:as_double(), o == 0x0a and "IR" or "DR", d & 0xff)); return d end)
TAP_P12 = ios:install_write_tap(0x12, 0x12, "p12", function(o, d, m)
  out:write(string.format("%.6f P12 %02X\n", machine.time:as_double(), d & 0xff)); return d end)
