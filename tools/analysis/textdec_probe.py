import sys
sys.path.insert(0,__import__('os').path.dirname(__import__('os').path.abspath(__file__)))
from z80core import Z80
import os
ROM=open(os.environ.get('GENIO_ROM','rom/genio2000_es_128k.bin'),'rb').read()   # GENIO_ROM: alternative image (e.g. rom/genio2000_es_128k_unit2.bin)
def mk(bank):
    z=Z80(); z.mem[0:0x4000]=ROM[0:0x4000]
    def load(b): z.mem[0x8000:0xC000]=ROM[b*0x4000:(b+1)*0x4000]
    load(bank)
    def out(p,v):
        if p==3: load(v & 7)
    z.io_out=out
    return z
def decode(z,idxs,t0,bank=4):
    z.mem[0xC100:0xC100+len(idxs)]=bytes(idxs)
    for a,v in ((0xD800,t0),(0xD802,t0+14),(0xD804,t0+44),(0xD806,0xC200)):
        z.mem[a]=v&255; z.mem[a+1]=v>>8
    z.mem[0xDB2A]=0; z.mem[0xDFF3]=bank; z.mem[0xC200]=0
    z.set_hl(0xC100); z.b=len(idxs); z.ix=0xD900; z.sp=0xDF00; z.ww(z.sp,0xFFF0); z.pc=0x0964
    n=0
    while z.pc!=0xFFF0 and n<200000:
        z.step(); n+=1
    return bytes(z.mem[0xD900:0xD9A0]), n
if __name__=='__main__':
    z=mk(4)
    for i in (0,1,2,3):
        o,n=decode(mk(4),[i],0x80DB); print(i,n,o[:24])
