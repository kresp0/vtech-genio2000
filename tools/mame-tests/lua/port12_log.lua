-- Logs every write to I/O port 0x12 (LED / speaker / power) with emulated time and PC.
-- env: GENIO_LOG (output file), GENIO_CLOCKSEL / GENIO_SOUNDSEL (index of the experimental CLOCK / SOUND configuration switches)
local machine = manager.machine
local cpu = machine.devices[":maincpu"]
local ios = cpu.spaces["io"]
local sel = tonumber(os.getenv("GENIO_CLOCKSEL") or "")
local snd = tonumber(os.getenv("GENIO_SOUNDSEL") or "")
local function setcfg(tag, v)
  local port = machine.ioport.ports[tag]
  for _, f in pairs(port.fields) do f:set_value(v) end
end
if sel then setcfg(":CLOCK", sel) end
if snd then setcfg(":SOUND", snd) end
local out = io.open(os.getenv("GENIO_LOG") or "port12.log", "w")
out:setvbuf("line")


out:write(string.format("# start pc %d\n", cpu.state["PC"].value))
local tap = ios:install_write_tap(0x12, 0x12, "p12", function(offset, data, mask)
  out:write(string.format("%.9f %02X %04X\n", machine.time:as_double(), data, cpu.state["PC"].value))
  return data
end)
local stop = tonumber(os.getenv("GENIO_STOP") or "")
if stop then
  emu.register_frame_done(function()
    if machine.time:as_double() >= stop then tap:remove(); out:flush(); machine:exit() end
  end)
end
