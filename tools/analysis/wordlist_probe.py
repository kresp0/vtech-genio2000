import sys
sys.path.insert(0,'tools'); sys.path.insert(0,__import__('os').path.dirname(__import__('os').path.abspath(__file__)))
from textdec_probe import mk
def word(z,bank,A,D,E,budget=400000):
    z.mem[0xD400:0xD500]=bytes(256); z.mem[0xDB2A]=0; z.mem[0xDFF3]=bank; z.mem[0xDB23]=1
    z.a=A; z.d=D; z.e=E; z.b=z.c=0; z.set_hl(0xD500); z.sp=0xDF00; z.ww(z.sp,0xFFF0); z.ix=0xDCF3; z.pc=0x0C13
    n=0
    while z.pc!=0xFFF0 and n<budget: z.step(); n+=1
    if z.pc!=0xFFF0: return None
    L=z.mem[0xD400]; return z.a, bytes(z.mem[0xD401:0xD401+L])
if __name__=='__main__':
    z=mk(4)
    print(word(z,4,1,0,1))
    for A in range(0,6):
        for D in range(0,4):
            print(A,D,[word(z,4,A,D,E) for E in range(0,3)])
