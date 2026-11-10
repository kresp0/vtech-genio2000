-- Generic scripted scenario: GENIO_SCEN = "time:action:arg;time:action:arg;..."  (emulated seconds)
--   press:<field name>[+<field name>...]   press the named keyboard fields (all held together) for GENIO_HOLD seconds (default 0.4)
--   snap                                   save a snapshot (sequential PNGs in the snapshot directory)
--   quit                                   exit
-- Field names are the key legends of the Spanish keyboard (e.g. "BASIC", "ALGEBRA", "A", "ALT").
local machine = manager.machine
local hold = tonumber(os.getenv("GENIO_HOLD") or "0.4")
local ev = {}
for item in string.gmatch(os.getenv("GENIO_SCEN") or "", "[^;]+") do
  local t, act, arg = string.match(item, "^([%d%.]+):(%w+):?(.*)$")
  ev[#ev+1] = {tonumber(t), act, arg}
end
table.sort(ev, function(a, b) return a[1] < b[1] end)
local function find_field(name)
  for tag, port in pairs(machine.ioport.ports) do
    local f = port.fields[name]
    if f then return f end
  end
end
local active, idx = {}, 1
emu.register_frame_done(function()
  local t = machine.time:as_double()
  for k = #active, 1, -1 do
    if t >= active[k][2] then active[k][1]:set_value(0); table.remove(active, k) end
  end
  while idx <= #ev and t >= ev[idx][1] do
    local e = ev[idx]
    if e[2] == "snap" then machine.video:snapshot()
    elseif e[2] == "press" then
      for name in string.gmatch(e[3], "[^+]+") do
        local f = find_field(name)
        if f then f:set_value(1); active[#active+1] = {f, t + hold} else print("MISSING FIELD " .. name) end
      end
    elseif e[2] == "quit" then machine:exit() end
    idx = idx + 1
  end
end)
