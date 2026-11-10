-- Dynamic execution trace for the genio2000 driver (EMULATION evidence only).
-- Records every opcode-fetch address (read at address == PC) with the current bank entries of :bank0/:bank1/:bank2,
-- plus non-sequential control-flow edges (prev_pc -> pc) and all I/O port accesses with (pc, value).
-- env: GENIO_SCEN (scenario.lua syntax), GENIO_STOP (emulated seconds), GENIO_OUT (output prefix)
local m = manager.machine
local cpu = m.devices[":maincpu"]
local prog = cpu.spaces["program"]
local ios = cpu.spaces["io"]
local b0, b1, b2 = m.memory.banks[":bank0"], m.memory.banks[":bank1"], m.memory.banks[":bank2"]
local clog=io.open((os.getenv("GENIO_OUT") or "exec")..".calls","w"); local want={}; for h in string.gmatch(os.getenv("GENIO_PCS") or "0F1F","%x+") do want[tonumber(h,16)]=true end; local seen, edges, iolog = {}, {}, {}
local prev = -10
local pcs = cpu.state["PC"]
local ppc = cpu.state["CURPC"]  -- start address of the instruction being executed (PC advances during operand fetch)
local tap = prog:install_read_tap(0x0000, 0xdfff, "fetch", function(off, data, mask)
  if off == pcs.value then
    local pc = ppc.value
    if want[pc] and off==pc then local st=cpu.state; local sp_=st["SP"].value; clog:write(string.format("%.3f pc=%04X HL=%04X A=%02X BC=%04X DE=%04X IX=%04X ret=%04X b1=%d b2=%d\n",m.time:as_double(),pc,st["HL"].value,st["A"].value,st["BC"].value,st["DE"].value,st["IX"].value,prog:read_u8(sp_)|(prog:read_u8(sp_+1)<<8),b1.entry,b2.entry)) end
    local k = pc | (b1.entry << 16) | (b2.entry << 24)
    seen[k] = (seen[k] or 0) + 1
    local d = pc - prev
    if d ~= 0 and (d < 1 or d > 4) then
      local e = (prev << 16) | pc
      -- key edges also by bank context of destination
      local ek = e + ((b1.entry << 8 | b2.entry) << 32)
      edges[ek] = (edges[ek] or 0) + 1
    end
    prev = pc
  end
  return data
end)
local iow = ios:install_write_tap(0x00, 0xff, "iow", function(off, data, mask)
  local k = string.format("W %02X %02X %04X", off, data & 0xff, pcs.value); iolog[k] = (iolog[k] or 0) + 1; return data end)
local ior = ios:install_read_tap(0x00, 0xff, "ior", function(off, data, mask)
  local k = string.format("R %02X %02X %04X", off, data & 0xff, pcs.value); iolog[k] = (iolog[k] or 0) + 1; return data end)
dofile(os.getenv("GENIO_SCENARIO_LUA") or "scenario.lua")
local stop = tonumber(os.getenv("GENIO_STOP") or "20")
local pre = os.getenv("GENIO_OUT") or "exec"
emu.register_frame_done(function()
  if m.time:as_double() >= stop then
    tap:remove(); iow:remove(); ior:remove()
    local f = io.open(pre .. ".exec", "w")
    for k, n in pairs(seen) do f:write(string.format("%04X %d %d %d\n", k & 0xffff, (k >> 16) & 0xff, (k >> 24) & 0xff, n)) end
    f:close()
    f = io.open(pre .. ".edges", "w")
    for k, n in pairs(edges) do f:write(string.format("%04X %04X %d %d %d\n", (k >> 16) & 0xffff, k & 0xffff, (k >> 40) & 0xff, (k >> 32) & 0xff, n)) end
    f:close()
    f = io.open(pre .. ".io", "w")
    for k, n in pairs(iolog) do f:write(k .. " " .. n .. "\n") end
    f:close(); clog:close()
    m:exit()
  end
end)
