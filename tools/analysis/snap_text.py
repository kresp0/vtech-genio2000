import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'mame-tests'))
import lcd_ocr
CG=os.environ.get('GENIO_CGROM', 'genio2000_cgrom_reconstructed.bin')
for p in sys.argv[1:]:
    print(p); print(lcd_ocr.ocr(p, CG))
