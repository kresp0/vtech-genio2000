-- Dump RAM 0xC000-0xDFFF (EMULATION) at GENIO_STOP seconds into GENIO_OUT.ram8k
local m = manager.machine
local prog = m.devices[":maincpu"].spaces["program"]
dofile(os.getenv("GENIO_SCENARIO_LUA") or "scenario.lua")
local stop = tonumber(os.getenv("GENIO_STOP") or "20")
emu.register_frame_done(function()
  if m.time:as_double() >= stop then
    local f = io.open((os.getenv("GENIO_OUT") or "ram") .. ".ram8k", "wb")
    for a = 0xC000, 0xDFFF do f:write(string.char(prog:read_u8(a))) end
    f:close(); m:exit()
  end
end)
