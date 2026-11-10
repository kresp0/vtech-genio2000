-- Lists every input field: tag, mask, type, name, default PC key sequence.  env GENIO_LOG
local out = io.open(os.getenv("GENIO_LOG") or "fields.txt", "w")
for tag, port in pairs(manager.machine.ioport.ports) do
  for name, f in pairs(port.fields) do
    out:write(string.format("%s\t0x%02X\t%s\t%s\t%s\n", tag, f.mask, f.type_class, name, f:input_seq(0)  and manager.machine.input:seq_name(f:input_seq(0)) or ""))
  end
end
out:close(); emu.register_frame_done(function() manager.machine:exit() end)
