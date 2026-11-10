-- Compares every entry of the banked ROM region (:bios, 32 entries of 16 KiB) with the firmware file: entry n must equal bank (n & 7).
-- env: GENIO_FW (128 KiB firmware path), GENIO_LOG (result file)
local machine = manager.machine
local rg = machine.memory.regions[":bios"]
local f = assert(io.open(os.getenv("GENIO_FW"), "rb")); local fw = f:read("*a"); f:close()
local out = io.open(os.getenv("GENIO_LOG") or "bank_check.txt", "w")
out:write(string.format("region_size=%d fw_size=%d\n", rg.size, #fw))
local bad = 0
for e = 0, 31 do
  local src, mism = (e & 7) * 0x4000, 0
  for a = 0, 0x3fff do
    if rg:read_u8(e * 0x4000 + a) ~= fw:byte(src + a + 1) then mism = mism + 1 end
  end
  out:write(string.format("entry %02d == bank %d : %s (%d mismatches)\n", e, e & 7, mism == 0 and "OK" or "FAIL", mism)); bad = bad + mism
end
out:write(bad == 0 and "RESULT OK\n" or "RESULT FAIL\n"); out:close()
emu.register_frame_done(function() machine:exit() end)
