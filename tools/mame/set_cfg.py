#!/usr/bin/env python3
"""set_cfg.py <cfg_dir> [--if-missing] [CLOCK=<0-9; 0 = 6.13179 MHz default, 9 = 4.0 MHz>] [IRQ=<0-6>]
Writes the MAME per-machine config genio2000.cfg selecting the experimental CLOCK / IRQ options (genio2000-dev branch only).  With --if-missing an existing cfg is kept: only the options that
are not in it yet are added (used by run_genio.sh to default the LCD to the photographed drawing without overriding the user's choices)."""
import sys, os
import xml.etree.ElementTree as ET
args = [a for a in sys.argv[1:] if a != '--if-missing']; keep = '--if-missing' in sys.argv
d = args[0]; os.makedirs(d, exist_ok=True); path = os.path.join(d, 'genio2000.cfg')
masks = {'CLOCK': 15, 'IRQ': 15}
want = [(k, int(v)) for k, v in (a.split('=') for a in args[1:])]
if keep and os.path.exists(path):
    tree = ET.parse(path); root = tree.getroot(); system = root.find('system')
    if system is None: system = ET.SubElement(root, 'system', name='genio2000')
    inp = system.find('input')
    if inp is None: inp = ET.SubElement(system, 'input')
    have = {p.get('tag') for p in inp.findall('port')}
    for k, v in want:
        if ':%s' % k not in have: ET.SubElement(inp, 'port', tag=':%s' % k, type='CONFIG', mask=str(masks[k]), defvalue='0', value=str(v))
    tree.write(path, encoding='utf-8', xml_declaration=True)
else:
    ports = ''.join('   <port tag=":%s" type="CONFIG" mask="%d" defvalue="0" value="%d" />\n' % (k, masks[k], v) for k, v in want)
    open(path, 'w').write('<?xml version="1.0"?>\n<mameconfig version="10">\n <system name="genio2000">\n  <input>\n%s  </input>\n </system>\n</mameconfig>\n' % ports)
