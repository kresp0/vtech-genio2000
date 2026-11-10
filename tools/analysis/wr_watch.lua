-- poll a RAM range every frame, log changes (EMU).  env GENIO_WATCH="D800-D807"
local m=manager.machine; local cpu=m.devices[":maincpu"]; local sp=cpu.spaces["program"]
local lo,hi=string.match(os.getenv("GENIO_WATCH") or "D800-D807","(%x+)-(%x+)"); lo=tonumber(lo,16); hi=tonumber(hi,16)
local out=io.open(os.getenv("GENIO_OUT") or "watch.txt","w"); local last=""
dofile(os.getenv("GENIO_SCENARIO_LUA") or "scenario.lua")
emu.register_frame_done(function()
  local s={}; for a=lo,hi do s[#s+1]=string.format("%02X",sp:read_u8(a)) end; s=table.concat(s," ")
  if s~=last then out:write(string.format("%.2f %s | DFF3=%02X\n",m.time:as_double(),s,sp:read_u8(0xDFF3))); last=s end
  if m.time:as_double()>=tonumber(os.getenv("GENIO_STOP") or "20") then out:close(); m:exit() end end)
