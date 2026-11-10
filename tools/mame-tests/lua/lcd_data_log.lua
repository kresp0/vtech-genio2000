-- Logs every byte written to the HD44780 data register (port 0x0B) and instruction register (port 0x0A) until GENIO_STOP seconds.
local machine = manager.machine
local cpu = machine.devices[":maincpu"]
local ios = cpu.spaces["io"]
local out = io.open(os.getenv("GENIO_LOG") or "lcd_data.log", "w"); out:setvbuf("line")
local wt = ios:install_write_tap(0x0a, 0x0b, "lcd", function(off, data, mask)
  out:write(string.format("%.6f %s %02X pc=%04X\n", machine.time:as_double(), off == 0x0a and "IR" or "DR", data & 0xff, cpu.state["PC"].value)); return data end)
local stop = tonumber(os.getenv("GENIO_STOP") or "12")
emu.register_frame_done(function() if machine.time:as_double() >= stop then wt:remove(); out:flush(); machine:exit() end end)
