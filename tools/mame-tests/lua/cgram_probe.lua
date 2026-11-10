-- Installs 8 deterministic CGRAM patterns, then writes GENIO_POKE (80 hex bytes, row-major 4x20 screen order) through the LCD ports 0x0A/0x0B
-- exactly like a program would, one cell per frame, and takes a snapshot.  Used to test codes 0x00-0x0F (CGRAM + alias) and the 8th pixel row.
local machine = manager.machine
local cpu = machine.devices[":maincpu"]; local ios = cpu.spaces["io"]
local lcd_map = {
  0,1,2,3,8,9,10,11,12,13,14,15,24,25,26,27,28,29,30,31,
  64,65,66,67,72,73,74,75,76,77,78,79,88,89,90,91,92,93,94,95,
  4,5,6,7,16,17,18,19,20,21,22,23,32,33,34,35,36,37,38,39,
  68,69,70,71,80,81,82,83,84,85,86,87,96,97,98,99,100,101,102,103 }
local cgram = {}
for k = 0, 7 do for r = 0, 7 do cgram[#cgram+1] = ((k+1)*(r+3)*5) & 0x1F end end
local poke = {}
for h in string.gmatch(os.getenv("GENIO_POKE") or "", "[^,]+") do poke[#poke+1] = tonumber(h, 16) end
local state, snapped = "wait", 0
emu.register_frame_done(function()
  local t = machine.time:as_double()
  if state == "wait" and t >= 9 then
    -- everything inside ONE frame callback: the Z80 cannot interleave its own LCD accesses (run it on a static screen anyway: demo cartridge)
    ios:write_u8(0x0a, 0x40); for _, v in ipairs(cgram) do ios:write_u8(0x0b, v) end
    for i, c in ipairs(poke) do ios:write_u8(0x0a, 0x80 | lcd_map[i]); ios:write_u8(0x0b, c) end
    state = "done"; snapped = t
  elseif state == "done" and t >= snapped + 0.5 then machine.video:snapshot(); machine:exit() end
end)
