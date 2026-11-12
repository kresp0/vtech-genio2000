-- Drives the diagnostic cartridge in headless MAME: presses keys on the emulated matrix, checks the shadow screen
-- (scr) against the HD44780's own DDRAM, dumps the result table, logs port 0x12 writes.
-- env: DG_SCRIPT = script, DG_LOG = log, DG_MAP = linker map (out/diag_gl2000.map), DG_CFG (see below)
-- Script lines:
--   wait <s> | press <field> | hold <field> <s> | dump [tag] | snap | results | fields | quit
--   peek <symbol or hex address> <n>
--   expect <row> <text>      row 0-3 of the screen, trailing spaces ignored ("*" at the end = prefix match)
--   status <name> <OK|FAIL|INFO|-->   result of the test whose name is <name>
--   until <row> <text> <s>   waits (up to s seconds) until the row starts with text
-- Copyright (c) 2026 Santiago Crespo. SPDX-License-Identifier: GPL-3.0-or-later
local machine = manager.machine
local cpu = machine.devices[":maincpu"]
local mem = cpu.spaces["program"]
local out = io.open(os.getenv("DG_LOG") or "drive.log", "w")
out:setvbuf("line")
local HOLD, GAP = 0.08, 0.08

local S = {}
for l in io.lines(os.getenv("DG_MAP")) do
  local a, n = string.match(l, "^%s+(%x%x%x%x%x%x%x%x)%s+(_[%w_]+)")
  if a then S[n] = tonumber(a, 16) end
end

local fields = {}
for _, port in pairs(machine.ioport.ports) do
  for name, f in pairs(port.fields) do fields[name] = f end
end

taps = {}   -- kept global: a collected tap makes MAME crash
-- DG_CFG="field=value;field=value": configuration switches (the experimental CLOCK / IRQ selectors of the dev build)
for item in string.gmatch(os.getenv("DG_CFG") or "", "[^;]+") do
  local n, v = string.match(item, "^(.-)=(%d+)$")
  fields[n]:set_value(tonumber(v))
end

-- DG_STUCK0="D234:10": the bits of the mask always read back 0 at that RAM address (fault injection)
local stuck = os.getenv("DG_STUCK0")
if stuck then
  local a, m = string.match(stuck, "^(%x+):(%x+)$")
  a, m = tonumber(a, 16), tonumber(m, 16)
  taps[#taps + 1] = mem:install_write_tap(a, a, "stuck", function(offset, data, mask) return data & ~m end)
end

local lcd
for tag, dev in pairs(machine.devices) do if string.find(tag, "hd44780") then lcd = dev end end
local ddram
for name, idx in pairs(lcd.items) do if string.find(name, "m_ddram") then ddram = emu.item(idx) end end
local map4 = {0,1,2,3,8,9,10,11,12,13,14,15,24,25,26,27,28,29,30,31,
  64,65,66,67,72,73,74,75,76,77,78,79,88,89,90,91,92,93,94,95,
  4,5,6,7,16,17,18,19,20,21,22,23,32,33,34,35,36,37,38,39,
  68,69,70,71,80,81,82,83,84,85,86,87,96,97,98,99,100,101,102,103}

local npass, nfail = 0, 0
local p12 = {n = 0, bit0 = 0, values = {}}
taps[#taps + 1] = cpu.spaces["io"]:install_write_tap(0x12, 0x12, "p12", function(offset, data, mask)
  p12.n = p12.n + 1
  if data & 1 ~= 0 then p12.bit0 = p12.bit0 + 1 end
  p12.values[data] = (p12.values[data] or 0) + 1
  return data
end)

local function cell(b) return (b >= 32 and b < 127) and string.char(b) or string.format("{%02X}", b) end
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

local ST = {[0] = "--", "OK", "FAIL", "INFO"}
local NT = 28
local function test_name(i)   -- tests[i].name: struct of two pointers in ROM
  local p = mem:read_u16(S._tests + 4 * i)
  local s = ""
  while mem:read_u8(p) ~= 0 do s = s .. string.char(mem:read_u8(p)); p = p + 1 end
  return s
end
local function results()
  out:write(string.format("--- results t=%.2f\n", machine.time:as_double()))
  for i = 0, NT - 1 do
    local d = ""
    for c = 0, 19 do d = d .. cell(mem:read_u8(S._res_det + 20 * i + c)) end
    out:write(string.format("%-15s %-5s |%s|\n", test_name(i), ST[mem:read_u8(S._res_st + i)] or "?", d))
  end
end

local lines = {}
for l in io.lines(os.getenv("DG_SCRIPT")) do lines[#lines + 1] = l end
local queue, held, t_next, li, wait_until = {}, nil, 0, 1, nil

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
  elseif cmd == "results" then results()
  elseif cmd == "fields" then
    for n, f in pairs(fields) do
      out:write("field [" .. n .. "]")
      for v, sn in pairs(f.settings or {}) do out:write(string.format(" %s=%s", v, sn)) end
      out:write("\n")
    end
  elseif cmd == "expect" then
    local r, text = string.match(arg, "^(%d)%s?(.*)$")
    local got = row(tonumber(r)):gsub("%s+$", "")
    local ok
    if text:sub(-1) == "*" then ok = got:sub(1, #text - 1) == text:sub(1, -2)
    else ok = got == text:gsub("%s+$", "") end
    result(ok, string.format("row %s = [%s] (got [%s])", r, text, got))
  elseif cmd == "status" then
    local name, st = string.match(arg, "^(.-)%s+(%S+)$")
    local got = "?"
    for i = 0, NT - 1 do if test_name(i) == name then got = ST[mem:read_u8(S._res_st + i)] end end
    result(got == st, string.format("%s = %s (got %s)", name, st, got))
  elseif cmd == "until" then
    local r, text, s = string.match(arg, "^(%d)%s(.-)%s+([%d%.]+)$")
    wait_until = {r = tonumber(r), text = text, limit = t + tonumber(s), start = t}
  elseif cmd == "quit" then
    out:write(string.format("port 0x12: %d writes, %d with bit 0 set; values:", p12.n, p12.bit0))
    for v, n in pairs(p12.values) do out:write(string.format(" %02X x%d", v, n)) end
    out:write(string.format("\nRESULT pass=%d fail=%d\n", npass, nfail))
    out:close()
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
  step(t)
end)
