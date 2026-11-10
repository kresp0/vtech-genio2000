-- Power cycle of the experimental power model: CAPS LED output, OFF (LCD must go blank), ON (the machine restarts without recreating MAME and shows the start-up).
-- Env: GENIO_LOG (result lines).  Snapshots: 0 = powered off, 1 = 8 s after ON.
local machine = manager.machine
local logf = os.getenv("GENIO_LOG")
local function log(s) local f = io.open(logf, "a"); f:write(s .. "\n"); f:close() end
local function field(name) for tag, port in pairs(machine.ioport.ports) do local f = port.fields[name]; if f then return f end end end
local held, step, ton = {}, 0, 0
local function press(name, t) local f = field(name); f:set_value(1); held[#held + 1] = {f, t + 0.4} end
emu.register_frame_done(function()
  local t = machine.time:as_double()
  for i = #held, 1, -1 do if t >= held[i][2] then held[i][1]:set_value(0); table.remove(held, i) end end
  if step == 0 and t > 14 then step = 1; press("BLOQ. MAYUSCULAS", t) end
  if step == 1 and t > 16 then step = 2; log("led_caps after CAPS = " .. tostring(machine.output:get_value("led_caps"))) end
  if step == 2 and t > 18 then step = 3; press("BLOQ. MAYUSCULAS", t) end
  if step == 3 and t > 20 then step = 4; log("led_caps after CAPS again = " .. tostring(machine.output:get_value("led_caps"))); press("OFF", t) end
  if step == 4 and t > 30 then step = 5; machine.video:snapshot(); log("powered off: snapshot at " .. t) end
  if step == 5 and t > 31 then step = 6; ton = t; press("ON", t) end
  if step == 6 and t > ton + 8 then step = 7; machine.video:snapshot(); log("after ON: snapshot at " .. t) end
  if step == 7 and t > ton + 9 then machine:exit() end
end)
