-- ON while the machine is running (BASIC open, a character typed): the machine must restart with fresh RAM and show the start-up screen, without recreating MAME.
-- Env: GENIO_LOG.  Snapshots: 0 = before ON, 1 = 3 s after ON (title screen), 2 = 8 s after ON.
local machine = manager.machine
local logf = os.getenv("GENIO_LOG")
local function log(s) local f = io.open(logf, "a"); f:write(s .. "\n"); f:close() end
local function field(name) for tag, port in pairs(machine.ioport.ports) do local f = port.fields[name]; if f then return f end end end
local held, step, ton = {}, 0, 0
local function press(name, t) local f = field(name); f:set_value(1); held[#held + 1] = {f, t + 0.4} end
emu.register_frame_done(function()
  local t = machine.time:as_double()
  for i = #held, 1, -1 do if t >= held[i][2] then held[i][1]:set_value(0); table.remove(held, i) end end
  if step == 0 and t > 12 then step = 1; press("BASIC", t) end
  if step == 1 and t > 40 then step = 2; press("B", t) end
  if step == 2 and t > 43 then step = 3; machine.video:snapshot() end
  if step == 3 and t > 44 then step = 4; ton = t; press("ON", t); log("ON pressed at " .. t) end
  if step == 4 and t > ton + 1.5 then step = 5; machine.video:snapshot() end
  if step == 5 and t > ton + 8 then step = 6; machine.video:snapshot() end
  if step == 6 and t > ton + 9 then machine:exit() end
end)
