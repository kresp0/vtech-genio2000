-- Headless test of the READY, SET, GO! cartridge in MAME (genio2000).
-- env: RSG_SCEN = "time:action:arg;..." (emulated seconds): press:<field>[+<field>] (held RSG_HOLD s), snap, quit
--      RSG_LOG  = summary file
-- It checks every write to ports 0x0A/0x0B (LCD) and 0x12 (speaker/LED/power) and reports the shortest gaps.
local machine = manager.machine
local cpu = machine.devices[":maincpu"]
local ios = cpu.spaces["io"]
local CLK = 6131790
local hold = tonumber(os.getenv("RSG_HOLD") or "0.3")
local out = io.open(os.getenv("RSG_LOG") or "rsg.log", "w")
out:setvbuf("line")

local ev = {}
for item in string.gmatch(os.getenv("RSG_SCEN") or "", "[^;]+") do
  local t, act, arg = string.match(item, "^([%d%.]+):(%w+):?(.*)$")
  ev[#ev + 1] = {tonumber(t), act, arg}
end
table.sort(ev, function(a, b) return a[1] < b[1] end)

local function find_field(name)
  for tag, port in pairs(machine.ioport.ports) do
    local f = port.fields[name]
    if f then return f end
  end
end

local function now() return machine.time:as_double() end
EXITPC = tonumber(os.getenv("RSG_EXITPC") or "")

-- LCD: shortest gap between two writes while the engine runs (PC >= 0x8000), and the number of writes
local lcd_last, lcd_min, lcd_min_t, lcd_n, lcd_gaps = nil, 1e9, 0, 0, {}
local function lcd(port)
  return function(offset, data, mask)
    local t = now()
    local pc = cpu.state["PC"].value
    if lcd_last and pc >= 0x8000 then
      local g = (t - lcd_last) * CLK
      if g < lcd_min then lcd_min, lcd_min_t = g, t end
      local b = math.floor(g + 0.5)
      if b < 600 then lcd_gaps[b] = (lcd_gaps[b] or 0) + 1 end
    end
    lcd_last = t
    lcd_n = lcd_n + 1
    return data
  end
end
local tap_a = ios:install_write_tap(0x0a, 0x0a, "rsg_a", lcd(0x0a))
local tap_b = ios:install_write_tap(0x0b, 0x0b, "rsg_b", lcd(0x0b))

-- port 0x12: bit 0 must stay 0 until the power-off; sample spacing; LED level
local p_last, p_n, p_bit0, p_led, p_gaps, p_first_off = nil, 0, 0, 0, {}, nil
TAPS = {tap_a, tap_b}
TAPS[3] = ios:install_write_tap(0x12, 0x12, "rsg_p", function(offset, data, mask)
  local t = now()
  if data & 0x01 ~= 0 then
    p_bit0 = p_bit0 + 1
    if not p_first_off then p_first_off = t end
  end
  if data & 0xD6 ~= 0 then out:write(string.format("unexpected bits %02X at %.6f pc %04X\n", data, t, cpu.state["PC"].value)) end
  if data & 0x20 ~= 0 then p_led = p_led + 1 end
  local pc = cpu.state["PC"].value
  if EXITPC and pc >= EXITPC and pc <= EXITPC + 2 then out:write(string.format("segment end at %.6f\n", t)) end
  if p_last then
    local g = math.floor((t - p_last) * CLK + 0.5)
    if g < 2000 then p_gaps[g] = (p_gaps[g] or 0) + 1 end
  end
  p_last = t
  p_n = p_n + 1
  return data
end)

local function report()
  out:write(string.format("LCD writes %d, shortest gap in the cartridge %.1f T-states (%.2f us) at %.3f s\n", lcd_n, lcd_min, lcd_min / CLK * 1e6, lcd_min_t))
  local ks = {}
  for k in pairs(lcd_gaps) do ks[#ks + 1] = k end
  table.sort(ks)
  for i = 1, math.min(#ks, 12) do out:write(string.format("  LCD gap %d T: %d\n", ks[i], lcd_gaps[ks[i]])) end
  out:write(string.format("port 0x12 writes %d, with LED bit %d, with bit 0 %d (first at %s)\n", p_n, p_led, p_bit0, tostring(p_first_off)))
  ks = {}
  for k in pairs(p_gaps) do ks[#ks + 1] = k end
  table.sort(ks, function(a, b) return p_gaps[a] > p_gaps[b] end)
  for i = 1, math.min(#ks, 8) do out:write(string.format("  0x12 gap %d T: %d\n", ks[i], p_gaps[ks[i]])) end
  out:flush()
end

local active, idx, nsnap = {}, 1, 0
emu.register_frame_done(function()
  local t = now()
  for k = #active, 1, -1 do
    if t >= active[k][2] then active[k][1]:set_value(0); table.remove(active, k) end
  end
  while idx <= #ev and t >= ev[idx][1] do
    local e = ev[idx]
    if e[2] == "snap" then
      machine.video:snapshot()
      nsnap = nsnap + 1
      out:write(string.format("snap %d at %.2f\n", nsnap, t))
    elseif e[2] == "press" then
      for name in string.gmatch(e[3], "[^+]+") do
        local f = find_field(name)
        if f then
          f:set_value(1)
          active[#active + 1] = {f, t + (tonumber(os.getenv("RSG_HOLD_" .. name) or "") or hold)}
          out:write(string.format("press %s at %.2f\n", name, t))
        else out:write("MISSING FIELD " .. name .. "\n") end
      end
    elseif e[2] == "quit" then
      report()
      machine:exit()
    end
    idx = idx + 1
  end
end)
