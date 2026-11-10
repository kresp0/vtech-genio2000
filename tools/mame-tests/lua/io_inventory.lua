-- Inventory of I/O port accesses: counts per (port, R/W, value) with first PC and first time; bank-select writes (0x00,0x01,0x03) logged in order.
-- env: GENIO_LOG (summary file), GENIO_BANKLOG (ordered bank writes), GENIO_STOP (seconds), GENIO_SCEN (see scenario.lua; reuse by dofile)
local machine = manager.machine
local cpu = machine.devices[":maincpu"]
local ios = cpu.spaces["io"]
local stat, order = {}, {}
local banklog = io.open(os.getenv("GENIO_BANKLOG") or "banks.log", "w"); banklog:setvbuf("line")
local function note(kind, port, data)
  local key = string.format("%02X %s %02X", port, kind, data)
  local s = stat[key]
  if not s then
    s = {n = 0, pc = cpu.state["PC"].value, t = machine.time:as_double()}; stat[key] = s; order[#order+1] = key
  end
  s.n = s.n + 1
  if kind == "W" and (port == 0 or port == 1 or port == 3) then
    banklog:write(string.format("%.6f %02X %02X %04X\n", machine.time:as_double(), port, data, cpu.state["PC"].value))
  end
end
local wt = ios:install_write_tap(0x00, 0xff, "iow", function(off, data, mask) note("W", off, data & 0xff) return data end)
local rt = ios:install_read_tap(0x00, 0xff, "ior", function(off, data, mask) note("R", off, data & 0xff) return data end)
dofile(os.getenv("GENIO_SCENARIO_LUA") or "tests/lua/scenario.lua")
local stop = tonumber(os.getenv("GENIO_STOP") or "20")
emu.register_frame_done(function()
  if machine.time:as_double() >= stop then
    wt:remove(); rt:remove()
    local out = io.open(os.getenv("GENIO_LOG") or "io_inventory.txt", "w")
    table.sort(order)
    for _, k in ipairs(order) do local s = stat[k]; out:write(string.format("%s count=%d first_pc=%04X first_t=%.4f\n", k, s.n, s.pc, s.t)) end
    out:close(); banklog:close(); machine:exit()
  end
end)
