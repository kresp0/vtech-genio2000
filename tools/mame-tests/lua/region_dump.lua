-- Dumps a memory region to a file: env GENIO_REGION (e.g. :hd44780), GENIO_OUT
local machine = manager.machine
local rg = machine.memory.regions[os.getenv("GENIO_REGION") or ":hd44780"]
local f = io.open(os.getenv("GENIO_OUT") or "region.bin", "wb")
for a = 0, rg.size - 1 do f:write(string.char(rg:read_u8(a))) end
f:close(); emu.register_frame_done(function() machine:exit() end)
