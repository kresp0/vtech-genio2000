-- log every execution of GENIO_PCS (comma hex list) with registers HL, A, SP-return and bank entries; first N hits. (EMU)
local m=manager.machine; local cpu=m.devices[":maincpu"]; local sp=cpu.spaces["program"]; local st=cpu.state
local want={}; for h in string.gmatch(os.getenv("GENIO_PCS") or "0F1F","%x+") do want[tonumber(h,16)]=true end
local out=io.open(os.getenv("GENIO_OUT") or "calls.txt","w"); local n=0; local lim=tonumber(os.getenv("GENIO_N") or "3000")
local t=sp:install_read_tap(0,0x7fff,"f",function(off,data,mask)
  if want[off] and off==st["PC"].value and n<lim then
    local s=st["SP"].value; local ret=sp:read_u8(s)|(sp:read_u8(s+1)<<8)
    out:write(string.format("%.3f pc=%04X HL=%04X A=%02X BC=%04X DE=%04X ret=%04X b1=%d b2=%d\n",m.time:as_double(),off,st["HL"].value,st["A"].value,st["BC"].value,st["DE"].value,ret,m.memory.banks[":bank1"].entry,m.memory.banks[":bank2"].entry)); n=n+1 end
  return data end)
dofile(os.getenv("GENIO_SCENARIO_LUA") or "scenario.lua")
emu.register_frame_done(function() if m.time:as_double()>=tonumber(os.getenv("GENIO_STOP") or "20") then out:close(); m:exit() end end)
