-- Drives the calculator cartridge in headless MAME: presses keys on the emulated matrix, checks the screen (the
-- program's shadow buffer against the HD44780's own DDRAM), and runs expression vectors through the real code.
-- env: CT_SCRIPT = script, CT_LOG = log, CT_MAP = linker map (out/calc_gl2000.map), CT_OUT = vector results
-- Script lines:
--   wait <s> | press <field>[+<field>..] | hold <field> <s> | dump [tag] | snap | quit
--   expect <row> <text>      row 0-3, trailing spaces ignored, "*" at the end = prefix; {name} = special glyph
--   until <row> <text> <s>   waits (up to s seconds) until the row starts with text
--   setbuf <text>            puts text in the edit buffer (shown at the next key)
--   eval <text>              puts text in the edit buffer, presses INTRO, logs "R <digits> <exp> <row 3>" or "ERR ..."
--   evalfile <path>          eval for every line of the file (lines starting with ! are mode keys, see below)
--   peek <symbol or hex> <n>
-- Copyright (c) 2026 Santiago Crespo. SPDX-License-Identifier: GPL-3.0-or-later
local machine = manager.machine
local cpu = machine.devices[":maincpu"]
local mem = cpu.spaces["program"]
local out = io.open(os.getenv("CT_LOG") or "drive.log", "w")
out:setvbuf("line")
local vout = os.getenv("CT_OUT") and io.open(os.getenv("CT_OUT"), "w")
if vout then vout:setvbuf("line") end
local HOLD, GAP = 0.06, 0.06

local S = {}
for l in io.lines(os.getenv("CT_MAP")) do
  local a, n = string.match(l, "^%s+(%x%x%x%x%x%x%x%x)%s+(_[%w_]+)")
  if a then S[n] = tonumber(a, 16) end
end

local fields = {}
for _, port in pairs(machine.ioport.ports) do
  for name, f in pairs(port.fields) do fields[name] = f end
end

taps = {}   -- kept global: a collected tap makes MAME crash
local p12 = {n = 0, bit0 = 0}
taps[#taps + 1] = cpu.spaces["io"]:install_write_tap(0x12, 0x12, "p12", function(offset, data, mask)
  p12.n = p12.n + 1
  if data & 1 ~= 0 then p12.bit0 = p12.bit0 + 1 end
  return data
end)
local p03 = {}
taps[#taps + 1] = cpu.spaces["io"]:install_write_tap(0x03, 0x03, "p03", function(offset, data, mask)
  p03[data] = (p03[data] or 0) + 1
  return data
end)

local lcd
for tag, dev in pairs(machine.devices) do if string.find(tag, "hd44780") then lcd = dev end end
local ddram
for name, idx in pairs(lcd.items) do if string.find(name, "m_ddram") then ddram = emu.item(idx) end end
local map4 = {0,1,2,3,8,9,10,11,12,13,14,15,24,25,26,27,28,29,30,31,
  64,65,66,67,72,73,74,75,76,77,78,79,88,89,90,91,92,93,94,95,
  4,5,6,7,16,17,18,19,20,21,22,23,32,33,34,35,36,37,38,39,
  68,69,70,71,80,81,82,83,84,85,86,87,96,97,98,99,100,101,102,103}

-- LCD codes of the glyphs the calculator uses, as in tests/host.c
local SYM = {[0x08] = "{-1}", [0x09] = "{2}", [0x0A] = "{3}", [0x0B] = "{sto}", [0x0C] = "{int}", [0x0D] = "{sum}",
  [0x0E] = "{E}", [0x0F] = "{xrt}", [0xB2] = "{deg}", [0xB7] = "{x}", [0xB8] = "{/}", [0xBE] = "{sqrt}",
  [0xED] = "{pi}", [0x9A] = "{U}", [0x9F] = "{?}"}
local CODE = {}
for c, n in pairs(SYM) do CODE[n] = c end

local function cell(b)
  if SYM[b] then return SYM[b] end
  return (b >= 32 and b < 127) and string.char(b) or string.format("{%02X}", b)
end
local function row(r)
  local s = ""
  for c = 0, 19 do s = s .. cell(mem:read_u8(S._scr + r * 20 + c)) end
  return s
end
local function lcdrow(r)
  local s = ""
  for c = 0, 19 do s = s .. cell(ddram:read(map4[r * 20 + c + 1])) end
  return s
end

local npass, nfail = 0, 0
local function dump(tag)
  out:write(string.format("--- %s t=%.2f\n", tag or "screen", machine.time:as_double()))
  local same = true
  for r = 0, 3 do
    out:write("|" .. row(r) .. "|\n")
    if row(r) ~= lcdrow(r) then same = false end
  end
  if not same then
    out:write("    LCD DDRAM differs from scr:\n")
    for r = 0, 3 do out:write("    |" .. lcdrow(r) .. "|\n") end
  end
end
local function result(ok, what)
  if ok then npass = npass + 1 else nfail = nfail + 1 end
  out:write((ok and "PASS " or "FAIL ") .. what .. "\n")
  if not ok then dump("at failure") end
end

-- text with {name} escapes -> bytes
local function encode(t)
  local b = {}
  local i = 1
  while i <= #t do
    local c = t:sub(i, i)
    if c == "{" then
      local j = t:find("}", i, true)
      local n = t:sub(i, j)
      b[#b + 1] = CODE[n] or error("unknown " .. n)
      i = j + 1
    else
      b[#b + 1] = string.byte(c); i = i + 1
    end
  end
  return b
end

local function setbuf(t)
  local b = encode(t)
  for i, v in ipairs(b) do mem:write_u8(S._buf + i - 1, v) end
  mem:write_u8(S._buf + #b, 0)
  mem:write_u8(S._blen, #b)
  mem:write_u8(S._cur, #b)
  mem:write_u8(S._editing, 1)
  mem:write_u8(S._have_res, 0)
  mem:write_u16(S._msg, 0)
end

local function ansline()
  local s = mem:read_u8(S._ans)
  local e = mem:read_u16(S._ans + 1)
  if e >= 0x8000 then e = e - 0x10000 end
  local d = ""
  for i = 0, 15 do d = d .. string.char(48 + mem:read_u8(S._ans + 3 + i)) end
  return string.format("R %s%s %d %s", s == 1 and "-" or "+", d, e, (row(3):gsub("^%s+", ""):gsub("%s+$", "")))
end

local lines = {}
for l in io.lines(os.getenv("CT_SCRIPT")) do lines[#lines + 1] = l end
local queue, held, t_next, li, wait_until, pending = {}, nil, 0, 1, nil, nil
local vec, vi = nil, 0

-- mode keys in vector files: "!" lines press a key combination (e.g. !press REVOLTIJO DE LETRAS)
local function start_eval(t, text)
  setbuf(text)
  queue[#queue + 1] = {"INTRO", dur = HOLD}
  pending = {text = text, start = t}
end

local function step(t)
  local l = lines[li]; li = li + 1
  if not l then l = "quit" end
  local cmd, arg = string.match(l, "^(%S+)%s?(.*)$")
  if not cmd or cmd:sub(1, 1) == "#" then return end
  if cmd == "wait" then t_next = t + tonumber(arg)
  elseif cmd == "press" then queue[#queue + 1] = {arg, dur = HOLD}
  elseif cmd == "hold" then
    local n, s = string.match(arg, "^(.-)%s+([%d%.]+)$")
    queue[#queue + 1] = {n, dur = tonumber(s)}
  elseif cmd == "dump" then dump(arg)
  elseif cmd == "snap" then machine.video:snapshot(); out:write(string.format("snap t=%.2f\n", t))
  elseif cmd == "peek" then
    local a, n = string.match(arg, "^(%S+)%s+(%d+)$")
    a = S[a] or tonumber(a, 16)
    local v = ""
    for i = 0, tonumber(n) - 1 do v = v .. string.format("%02X ", mem:read_u8(a + i)) end
    out:write(string.format("peek %04X t=%.2f: %s\n", a, t, v))
  elseif cmd == "expect" then
    local r, text = string.match(arg, "^(%d)%s?(.*)$")
    local got = row(tonumber(r)):gsub("%s+$", "")
    local ok
    if text:sub(-1) == "*" then ok = got:sub(1, #text - 1) == text:sub(1, -2)
    else ok = got == text:gsub("%s+$", "") end
    result(ok and row(tonumber(r)) == lcdrow(tonumber(r)), string.format("row %s = [%s] (got [%s])", r, text, got))
  elseif cmd == "until" then
    local r, text, s = string.match(arg, "^(%d)%s(.-)%s+([%d%.]+)$")
    wait_until = {r = tonumber(r), text = text, limit = t + tonumber(s), start = t}
  elseif cmd == "eval" then start_eval(t, arg)
  elseif cmd == "setbuf" then setbuf(arg)
  elseif cmd == "evalfile" then
    vec = {}
    for v in io.lines(arg) do vec[#vec + 1] = v end
    vi = 0
  elseif cmd == "quit" then
    out:write(string.format("port 0x12: %d writes, %d with bit 0 set\nport 0x03:", p12.n, p12.bit0))
    for v, n in pairs(p03) do out:write(string.format(" %02X x%d", v, n)) end
    out:write(string.format("\nRESULT pass=%d fail=%d\n", npass, nfail))
    out:close()
    if vout then vout:close() end
    machine:exit()
  end
end

emu.register_frame_done(function()
  local t = machine.time:as_double()
  if held then
    if t >= held.t_end then
      for _, n in ipairs(held.k) do fields[n]:set_value(0) end
      held = nil; t_next = t + GAP
    end
    return
  end
  if t < t_next then return end
  if #queue > 0 then
    local k = table.remove(queue, 1)
    local names = {}
    for n in string.gmatch(k[1], "[^+]+") do
      if not fields[n] then out:write("NO FIELD " .. n .. "\n") else fields[n]:set_value(1); names[#names + 1] = n end
    end
    held = {k = names, t_end = t + k.dur}
    return
  end
  if pending then
    local done = mem:read_u8(S._have_res) == 1 or mem:read_u16(S._msg) ~= 0
    if done and not pending.seen then pending.seen = t end     -- the screen is redrawn after the flag is set
    if (done and t - pending.seen > 0.05) or t - pending.start > 120 then
      local line = done and (mem:read_u8(S._have_res) == 1 and ansline() or
        "ERR " .. (row(3):gsub("%s+$", ""))) or "TIMEOUT"
      local w = vout or out
      w:write(line .. string.format("  [%.2fs] %s\n", t - pending.start, pending.text))
      pending = nil
      t_next = t + 0.05
    end
    return
  end
  if wait_until then
    local got = row(wait_until.r)
    if got:sub(1, #wait_until.text) == wait_until.text then
      out:write(string.format("until row %d [%s] after %.2f s\n", wait_until.r, wait_until.text, t - wait_until.start))
      wait_until = nil
    elseif t > wait_until.limit then
      result(false, string.format("until row %d [%s] timed out", wait_until.r, wait_until.text))
      wait_until = nil
    end
    return
  end
  if vec then
    vi = vi + 1
    local v = vec[vi]
    if not v then vec = nil; return end
    if v:sub(1, 7) == "!press " then queue[#queue + 1] = {v:sub(8), dur = HOLD}; t_next = t + 0.3
    else start_eval(t, v) end
    return
  end
  step(t)
end)
