import sys

#00:00:00,000
def srt_time_to_ms(str):
    return ((int(str[0:2])*60+int(str[3:5]))*60+int(str[6:8]))*1000+int(str[9:12])

def ms_to_srt_time(ms):
    milli=ms%1000
    ms=int(ms/1000)
    sec=ms%60
    ms=int(ms/60)
    minute=ms%60
    hour=int(ms/60)
    return "%02d:%02d:%02d,%03d"%(hour,minute,sec,milli)

class Caption(object):
    num=0
    start=0
    end=0
    cap=""

    def __init__(self,str):
        self.from_str(str)

    def from_str(self,str):
        lines=str.split("\n")
        self.num=int(lines[0])
        self.start=srt_time_to_ms(lines[1][0:12])
        self.end=srt_time_to_ms(lines[1][17:29])
        self.cap=lines[2]

    def to_str(self):
        return str(self.num)+"\n"+ms_to_srt_time(self.start)+" --> "+ms_to_srt_time(self.end)+"\n"+self.cap+"\n\n"

def read_one_caption(fin):
    lines=""
    for i in range(0,4):
        line=fin.readline()
        if line=="":
            return ""
        lines=lines+line
    return lines

def fixmain(srtpath,fps):
    caps=[]
    fin=open(srtpath,"r",encoding="utf-8")
    while True:
        capstr=read_one_caption(fin)
        if capstr=="":
            break
        caps.append(Caption(capstr))
    ext=srtpath[srtpath.rfind("."):]
    fout=open(srtpath[:-len(ext)]+"_fix"+ext,"w",encoding="utf-8")
    for i in range(0,len(caps)):
        if i<len(caps)-1 and caps[i].end>=caps[i+1].start:
            caps[i].end=caps[i+1].start-1000/fps
        fout.write(caps[i].to_str())

if len(sys.argv)<2:
    print("Usage: fix_you_srt_tl.py <SRT file> [FPS(Default=60)]")
elif len(sys.argv)<3:
    fixmain(sys.argv[1],60)
else:
    fixmain(sys.argv[1],float(sys.argv[2]))