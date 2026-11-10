local m = manager.machine
for tag, b in pairs(m.memory.banks) do print("BANK", tag, b.entry) end
local ios = m.devices[":maincpu"].spaces["program"]
print("SPACES ok")
emu.register_frame_done(function() if m.time:as_double() > 1 then m:exit() end end)
