-- Virtual serial cable for the pc-link cartridge in headless MAME (the genio2000 driver has no printer port).
-- PC -> Genio: bytes queued from EN_DIR/ctl.txt are played as a UART waveform on port 0x11 bit 5 (BUSY), read
-- through a tap whenever the CPU executes IN 0x11. Genio -> PC: writes to port 0x10 bit 0 (DATA0, port 1 = line
-- low) are timestamped and decoded as a UART into EN_DIR/rx.bin.
-- ctl.txt lines (appended by pclink.py --mame): data <hex> | baud <pc tx baud> <pc rx baud> | break 0|1 | stats | quit
-- | screen <tag> (LCD rows into lua.log) | snap | press <key field name> (held 0.25 s)
-- env: EN_DIR, EN_INVERT=1 (BUSY bit 5 = line level instead of its inverse), EN_RISE_US / EN_FALL_US (rising / falling edges this late)
-- Copyright (c) 2026 Santiago Crespo. SPDX-License-Identifier: GPL-3.0-or-later
local machine = manager.machine
local cpu = machine.devices[":maincpu"]
local ios = cpu.spaces["io"]
local dir = os.getenv("EN_DIR") or "."
local invert = os.getenv("EN_INVERT") == "1"
local rise = tonumber(os.getenv("EN_RISE_US") or "0") * 1e-6    -- model of a slow BUSY input: rising edges late
local fall = tonumber(os.getenv("EN_FALL_US") or "0") * 1e-6    -- falling edges late (what the scope saw on the unit)
local log = io.open(dir .. "/lua.log", "w")
log:setvbuf("line")
local rxf = io.open(dir .. "/rx.bin", "wb")

local function now() return machine.time:as_double() end

-- ---------------------------------------------------------------- PC transmitter
local tx_bt, rx_bt = 1 / 9600, 1 / 9600
local brk = false
local q, qh = {}, 1          -- queued bytes {start, byte}; qh = first not yet finished
local qend = 0
local reads = 0

local function wire(t)       -- level of the PC's TXD at time t: true = high (mark)
  while q[qh] and t - 1e-4 >= q[qh][1] + 10 * tx_bt do qh = qh + 1 end
  local b = nil
  for k = qh, #q do
    if t < q[k][1] then break end
    if t < q[k][1] + 10 * tx_bt then b = q[k] break end
  end
  if b then
    local k = math.floor((t - b[1]) / tx_bt)
    if k == 0 then return false end
    if k >= 9 then return true end
    return (b[2] >> (k - 1)) & 1 == 1
  end
  return not brk
end

taps = {}   -- kept global: a collected tap makes MAME crash
taps[1] = ios:install_read_tap(0x11, 0x11, "busy", function(offset, data, mask)
  reads = reads + 1
  local t = now()
  local high = wire(t)
  if fall > 0 then high = high or wire(t - fall) end
  if rise > 0 then high = high and wire(t - rise) end
  local bit5 = high and 0 or 0x20     -- GL4000 notes: BUSY reads 1 while the line is low
  if invert then bit5 = bit5 ~ 0x20 end
  return (data & ~0x20) | bit5
end)

-- ---------------------------------------------------------------- PC receiver
local tr = {{0, true}}       -- transitions of DATA0 {time, high}
local lvl = true
lat_from, lat_sum, lat_n, lat_max = nil, 0, 0, 0   -- answer latency: end of the PC's bytes to the Genio's first edge
taps[2] = ios:install_write_tap(0x10, 0x10, "data0", function(offset, data, mask)
  local high = (data & 1) == 0
  if high ~= lvl then
    lvl = high
    tr[#tr + 1] = {now(), high}
    if not high and lat_from then
      lat_sum, lat_n, lat_max = lat_sum + now() - lat_from, lat_n + 1, math.max(lat_max, now() - lat_from)
      lat_from = nil
    end
  end
  return data
end)

local function find(t)       -- index of the last transition at or before t
  local lo, hi = 1, #tr
  while lo < hi do
    local m = (lo + hi + 1) // 2
    if tr[m][1] <= t then lo = m else hi = m - 1 end
  end
  return lo
end
local function level_at(t) return tr[find(t)][2] end

local search_t = 0
local nbytes, nfe, nglitch = 0, 0, 0
local last_start, per_sum, per_n = nil, 0, 0
local function decode()
  local t = now()
  while true do
    local i = find(search_t) + 1
    while tr[i] and tr[i][2] do i = i + 1 end      -- next falling edge
    if not tr[i] then break end
    local t0 = tr[i][1]
    if t < t0 + 10 * rx_bt then break end
    if level_at(t0 + 0.5 * rx_bt) then
      nglitch = nglitch + 1
      search_t = t0
    else
      local b = 0
      for k = 0, 7 do
        if level_at(t0 + (1.5 + k) * rx_bt) then b = b | (1 << k) end
      end
      if not level_at(t0 + 9.5 * rx_bt) then nfe = nfe + 1 end
      rxf:write(string.char(b))
      nbytes = nbytes + 1
      if last_start and t0 - last_start < 10.5 * rx_bt then
        per_sum = per_sum + (t0 - last_start)
        per_n = per_n + 1
      end
      last_start = t0
      search_t = t0 + 9.5 * rx_bt
    end
  end
  rxf:flush()
end

local function stats()
  log:write(string.format("stats t=%.3f busy_reads=%d genio_bytes=%d framing_errors=%d glitches=%d", now(), reads,
    nbytes, nfe, nglitch))
  if per_n > 0 then
    log:write(string.format(" byte_period_us=%.3f bit_us=%.4f nominal_bit_us=%.4f", per_sum / per_n * 1e6,
      per_sum / per_n / 10 * 1e6, rx_bt * 1e6))
  end
  if lat_n > 0 then
    log:write(string.format(" answer_latency_ms mean=%.1f max=%.1f n=%d", lat_sum / lat_n * 1e3, lat_max * 1e3, lat_n))
  end
  lat_sum, lat_n, lat_max = 0, 0, 0
  log:write("\n")
end

-- ---------------------------------------------------------------- LCD contents, from the HD44780's own DDRAM
local ddram
for tag, dev in pairs(machine.devices) do
  if string.find(tag, "hd44780") then
    for name, idx in pairs(dev.items) do if string.find(name, "m_ddram") then ddram = emu.item(idx) end end
  end
end
local map4 = {0,1,2,3,8,9,10,11,12,13,14,15,24,25,26,27,28,29,30,31,
  64,65,66,67,72,73,74,75,76,77,78,79,88,89,90,91,92,93,94,95,
  4,5,6,7,16,17,18,19,20,21,22,23,32,33,34,35,36,37,38,39,
  68,69,70,71,80,81,82,83,84,85,86,87,96,97,98,99,100,101,102,103}
local function screen(tag)
  for r = 0, 3 do
    local s = ""
    for c = 0, 19 do
      local v = ddram:read(map4[r * 20 + c + 1])
      s = s .. ((v >= 0x20 and v < 0x7F) and string.char(v) or string.format("\\x%02X", v))
    end
    log:write(string.format("screen %s %d |%s|\n", tag, r, s))
  end
end

-- ---------------------------------------------------------------- keys of the emulated matrix
local fields, release = {}, {}
for _, port in pairs(machine.ioport.ports) do
  for name, f in pairs(port.fields) do fields[name] = f end
end

-- ---------------------------------------------------------------- control file
local ctl_pos = 0
local function control()
  local f = io.open(dir .. "/ctl.txt", "r")
  if not f then return end
  f:seek("set", ctl_pos)
  local s = f:read("a") or ""
  f:close()
  local consumed = 0
  for line in string.gmatch(s, "([^\n]*)\n") do
    consumed = consumed + #line + 1
    local cmd, arg = string.match(line, "^(%S+)%s*(.*)$")
    if cmd == "data" then
      local t = now()
      for h in string.gmatch(arg, "%x%x") do
        local st = math.max(t, qend)
        q[#q + 1] = {st, tonumber(h, 16)}
        qend = st + 10 * tx_bt
      end
      lat_from = qend
    elseif cmd == "baud" then
      local a, b = string.match(arg, "^(%S+)%s+(%S+)$")
      tx_bt, rx_bt = 1 / tonumber(a), 1 / tonumber(b)
      per_sum, per_n, last_start = 0, 0, nil
      log:write(string.format("baud tx %s rx %s at %.3f\n", a, b, now()))
    elseif cmd == "break" then
      brk = arg == "1"
    elseif cmd == "screen" then
      screen(arg)
    elseif cmd == "press" then
      fields[arg]:set_value(1)
      release[#release + 1] = {now() + 0.25, fields[arg]}
    elseif cmd == "snap" then
      machine.video:snapshot()
    elseif cmd == "stats" then
      stats()
    elseif cmd == "quit" then
      stats()
      log:write("quit\n")
      log:flush()
      rxf:flush()
      machine:exit()
    end
  end
  ctl_pos = ctl_pos + consumed
end

log:write(string.format("bridge ready, invert=%s\n", tostring(invert)))
emu.register_frame_done(function()
  for i = #release, 1, -1 do
    if now() >= release[i][1] then release[i][2]:set_value(0); table.remove(release, i) end
  end
  decode()
  control()
end)
