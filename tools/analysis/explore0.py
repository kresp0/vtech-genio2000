import sys, os, collections
sys.path.insert(0, 'tools')
import trace as T
rom = open('rom/genio2000_es_128k.bin','rb').read()
seeds = [(0,0,a,'vector') for a in (0x0000,0x0008,0x0010,0x0018,0x0020,0x0028,0x0030,0x0038,0x0066)]
# API jump table 0x003B..0x0116
for a in range(0x3B, 0x119, 3):
    seeds.append((0,0,a,'api_jump_table'))
t = T.Tracer(rom).run(seeds)
c = t.code[(0,0)]
print("bank0 traced bytes:", sum(i.length for i in c.values()), "of 16384 =", round(100*sum(i.length for i in c.values())/16384,1), "%")
far = collections.Counter((k,tgt) for (_,_,_,k,tgt) in t.far)
print("far targets:", len(far))
for (k,tg),n in sorted(far.items(), key=lambda x:x[0][1]): print("  %s %04X x%d" % (k,tg,n))
print("jpind:", [(hex(p),x) for _,_,p,x in t.jpind])
