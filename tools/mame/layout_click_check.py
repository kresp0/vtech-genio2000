import sys, subprocess, time, re, os
import xml.etree.ElementTree as ET
H=os.environ.get('GENIO_MAME_DIR', '.') + '/'; D=sys.argv[1]; binary=sys.argv[2]; artpath=sys.argv[3]; label=sys.argv[4]; out=sys.argv[5]
r=ET.parse(H+'artwork/genio2000/default.lay',parser=ET.XMLParser(target=ET.TreeBuilder(insert_comments=True))).getroot().find('view'); k=list(r)
LW=float(r.find("element[@ref='lid']/bounds").get('width')); LHt=float(r.find("element[@ref='base']/bounds").get('y'))+float(r.find("element[@ref='base']/bounds").get('height'))
def centre(l):
    for i,e in enumerate(k):
        if e.tag=='element' and e.get('inputtag') and i>0 and k[i-1].tag is ET.Comment and k[i-1].text.strip()==l:
            b=e.find('bounds'); return float(b.get('x'))+float(b.get('width'))/2, float(b.get('y'))+float(b.get('height'))/2
cx,cy=centre(label)
subprocess.run('rm -rf %s/h %s/c %s/n; mkdir -p %s/c'%(D,D,D,D),shell=True)
p=subprocess.Popen([binary,'genio2000','-rompath',H+'roms_local','-artpath',artpath,'-homepath',D+'/h','-cfg_directory',D+'/c','-nvram_directory',D+'/n','-video','soft','-window','-nomax','-resolution','700x1000','-sound','none','-seconds_to_run','60','-skip_gameinfo'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,stdin=subprocess.DEVNULL)
def info():
    t=subprocess.run(['xwininfo','-root','-tree'],capture_output=True,text=True).stdout
    for l in t.splitlines():
        if 'Genio 2000 (Spain) [genio2000]' in l:
            w=l.split()[0]; i=subprocess.run(['xwininfo','-id',w],capture_output=True,text=True).stdout
            g=lambda kk:int(re.search(kk+r':\s+(-?\d+)',i).group(1)); return w,g('Absolute upper-left X'),g('Absolute upper-left Y'),g('Width'),g('Height')
time.sleep(4); w=info()
def click(x,y,sc,ax,ay):
    subprocess.run(['xdotool','mousemove',str(int(ax+x*sc)),str(int(ay+y*sc))]); time.sleep(0.3); subprocess.run(['xdotool','mousedown','1']); time.sleep(0.6); subprocess.run(['xdotool','mouseup','1'])
wid,ax,ay,ww,wh=w; sc=min(ww/LW,wh/LHt); ax+=(ww-LW*sc)/2; ay+=(wh-LHt*sc)/2   # the view is letterboxed in the window
click(LW/2,60,sc,ax,ay); time.sleep(16)
click(cx,cy,sc,ax,ay); time.sleep(14)
subprocess.run(['import','-window','root','-crop','%dx%d+%d+%d'%(ww,wh,ax,ay),'+repage',out]); p.terminate()
print('clicked',label,'at layout',round(cx),round(cy))
