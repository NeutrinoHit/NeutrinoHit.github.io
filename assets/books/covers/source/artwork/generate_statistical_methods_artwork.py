from pathlib import Path
import math
import re
import numpy as np
from scipy.spatial import ConvexHull
from skimage.measure import find_contours
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import cairosvg

PROJECT = Path(__file__).resolve().parents[2]
BUILD = PROJECT / "build"
BUILD.mkdir(parents=True, exist_ok=True)

DATA_FILE = BUILD / "juno_like_central_figure_v1_data.npz"
if not DATA_FILE.exists():
    DATA_FILE = PROJECT / "data" / "juno_like_central_figure_v1_data.npz"

OUT_SVG = PROJECT / "source" / "artwork" / "statistical_methods_juno.svg"
OUT_PNG = BUILD / "juno_central_figure_design_v5_latex_preview.png"

D = np.load(DATA_FILE)

INK="#1D2A32"
TEAL="#0A6674"
T2="#4E99A5"
T3="#A9CDD2"
TP="#E4F0F1"
TW="#F4F8F8"
ORANGE="#C98212"
GRAY="#7D898F"
GRID="#D8E0E2"
W,H=1000,930

# Current v5 layout.
PX,PY,PW,PH=100,190,480,360
TX,TY,TWID,TH=PX,64,PW,92
RX,RY,RW,RH=612,PY,118,PH
DCX,DCY,DR=845,118,90
SX,SY,SW,SH=100,642,820,118
ZX,ZY,ZW,ZH=100,802,820,72

DM_MIN,DM_MAX=7.445,7.542
S12_MIN,S12_MAX=0.3054,0.3154
QMAX=7.5

s12=D["s12_grid"]
dm=D["dm21_grid"]*1e5
q=D["q"]
ps=D["profile_s12"]
pd=D["profile_dm21"]
e=D["e_centers"]
obs=D["data"]
sb=D["spec_best"]
s0=D["spec_noosc"]
resid=D["residuals"]
s12_best=float(D["s12_best"])
dm_best=float(D["dm21_best"])*1e5

ratio=obs/np.clip(s0,1e-12,None)
fit=sb/np.clip(s0,1e-12,None)
err=np.sqrt(np.maximum(obs,1))/np.clip(s0,1e-12,None)

def pl(xs,ys):
    return "M "+" L ".join(f"{x:.2f},{y:.2f}" for x,y in zip(xs,ys))

def mx(v):
    return PX+(v-DM_MIN)/(DM_MAX-DM_MIN)*PW

def my(v):
    return PY+PH-(v-S12_MIN)/(S12_MAX-S12_MIN)*PH

def cpath(level):
    loops=find_contours(q,level)
    if not loops:
        return ""
    c=max(loops,key=len)
    sv=np.interp(c[:,0],np.arange(len(s12)),s12)
    dv=np.interp(c[:,1],np.arange(len(dm)),dm)
    return pl([mx(v) for v in dv],[my(v) for v in sv])+" Z"

m=(dm>=DM_MIN)&(dm<=DM_MAX)&(pd<=QMAX)
top=pl([TX+(v-DM_MIN)/(DM_MAX-DM_MIN)*TWID for v in dm[m]],
       [TY+TH-v/QMAX*TH for v in pd[m]])

m=(s12>=S12_MIN)&(s12<=S12_MAX)&(ps<=QMAX)
right=pl([RX+v/QMAX*RW for v in ps[m]],
         [RY+RH-(v-S12_MIN)/(S12_MAX-S12_MIN)*RH for v in s12[m]])

def specxy(ev,val):
    return SX+(ev-1.2)/(7-1.2)*SW, SY+SH-(val-.12)/(.84-.12)*SH

def resxy(ev,val):
    return ZX+(ev-1.2)/(7-1.2)*ZW, ZY+ZH-(val+3.5)/7*ZH

me=(e>=1.2)&(e<=7)
fitpath=pl([specxy(a,b)[0] for a,b in zip(e[me],fit[me])],
           [specxy(a,b)[1] for a,b in zip(e[me],fit[me])])

def line(x1,y1,x2,y2,width=1.0,stroke=INK,opacity=None):
    op=f' opacity="{opacity}"' if opacity is not None else ""
    return f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" stroke="{stroke}" stroke-width="{width}"{op}/>'

# Axis linework only. Labels are vector math paths added later.
linework=[]
linework += [line(PX,PY+PH,PX+PW,PY+PH,2.0), line(PX,PY,PX,PY+PH,2.0)]
for v in [7.45,7.47,7.49,7.51,7.53]:
    x=mx(v); linework.append(line(x,PY+PH,x,PY+PH+7,1.1))
for v in [0.306,0.308,0.310,0.312,0.314]:
    y=my(v); linework.append(line(PX-7,y,PX,y,1.1))

linework += [line(TX,TY+TH,TX+TWID,TY+TH,1.4), line(TX,TY,TX,TY+TH,1.4)]
for v in [7.45,7.47,7.49,7.51,7.53]:
    x=TX+(v-DM_MIN)/(DM_MAX-DM_MIN)*TWID
    linework.append(line(x,TY+TH,x,TY+TH+5,1.0))
for v in [0,2,4,6]:
    y=TY+TH-v/QMAX*TH
    linework.append(line(TX-5,y,TX,y,1.0))

linework += [line(RX,RY+RH,RX+RW,RY+RH,1.4), line(RX,RY,RX,RY+RH,1.4)]
for v in [0,2,4,6]:
    x=RX+v/QMAX*RW
    linework.append(line(x,RY+RH,x,RY+RH+5,1.0))
for v in [0.306,0.308,0.310,0.312,0.314]:
    y=RY+RH-(v-S12_MIN)/(S12_MAX-S12_MIN)*RH
    linework.append(line(RX-5,y,RX,y,1.0))

linework += [line(SX,SY+SH,SX+SW,SY+SH,1.8), line(SX,SY,SX,SY+SH,1.8)]
for v in [2,3,4,5,6,7]:
    x=specxy(v,.12)[0]
    linework.append(line(x,SY+SH,x,SY+SH+6,1.0))
for v in [.2,.4,.6,.8]:
    y=specxy(1.2,v)[1]
    linework.append(line(SX-6,y,SX,y,1.0))

linework += [line(ZX,ZY+ZH,ZX+ZW,ZY+ZH,1.6), line(ZX,ZY,ZX,ZY+ZH,1.6)]
for v in [2,3,4,5,6,7]:
    x=resxy(v,-3.5)[0]
    linework.append(line(x,ZY+ZH,x,ZY+ZH+5,.9))
for v in [-2,0,2]:
    y=resxy(1.2,v)[1]
    linework.append(line(ZX-5,y,ZX,y,.9))

# Procedural detector:
# smooth inner target + representative PMT shell + triangular steel truss.
def rot(p,ax=-.18,ay=.40,az=-.10):
    x,y,z=p
    c,s=math.cos(ax),math.sin(ax); y,z=y*c-z*s,y*s+z*c
    c,s=math.cos(ay),math.sin(ay); x,z=x*c+z*s,-x*s+z*c
    c,s=math.cos(az),math.sin(az); x,y=x*c-y*s,x*s+y*c
    return x,y,z

def proj(p,r=DR):
    x,y,z=rot(p)
    return DCX+r*x,DCY-r*y,z

gold=math.pi*(3-math.sqrt(5))
nodes=[]
for i in range(150):
    yy=1-2*(i+.5)/150
    rr=math.sqrt(max(0,1-yy*yy))
    ph=i*gold
    nodes.append((rr*math.cos(ph),yy,rr*math.sin(ph)))
nodes=np.array(nodes)
hull=ConvexHull(nodes)
edges=set()
for tri in hull.simplices:
    a,b,c=map(int,tri)
    edges.update({
        tuple(sorted((a,b))),
        tuple(sorted((b,c))),
        tuple(sorted((c,a)))
    })
pn=[proj(tuple(p)) for p in nodes]

DET=[f'<circle cx="{DCX}" cy="{DCY}" r="{DR*.67:.2f}" fill="{TW}" stroke="{T3}" stroke-width="1.4"/>']

for a,b in edges:
    xa,ya,za=pn[a]; xb,yb,zb=pn[b]
    if (za+zb)<0:
        DET.append(line(xa,ya,xb,yb,.7,T3,.28))

back=[]; front=[]
for i in range(1200):
    yy=1-2*(i+.5)/1200
    rr=math.sqrt(max(0,1-yy*yy))
    ph=i*gold
    x,y,z=proj((rr*math.cos(ph),yy,rr*math.sin(ph)),DR*.80)
    dot=f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{(.52+.20*max(z,0)):.2f}" fill="{INK}" opacity="{.16 if z<0 else .56}"/>'
    (front if z>=0 else back).append(dot)
DET += back

for a,b in edges:
    xa,ya,za=pn[a]; xb,yb,zb=pn[b]
    if (za+zb)>=0:
        DET.append(line(xa,ya,xb,yb,.85,T2,.58))
DET += front

DET += [
    f'<circle cx="{DCX}" cy="{DCY}" r="{DR*.67:.2f}" fill="none" stroke="{TEAL}" stroke-width="2.0" opacity=".82"/>',
    f'<circle cx="{DCX}" cy="{DCY}" r="{DR}" fill="none" stroke="{TEAL}" stroke-width="3.2"/>'
]
for a in np.linspace(0,2*math.pi,10,endpoint=False):
    r=DR*.50
    x=DCX+r*math.cos(a)
    y=DCY+r*math.sin(a)
    DET.append(line(DCX,DCY,x,y,.8,ORANGE,.35))
DET.append(f'<circle cx="{DCX}" cy="{DCY}" r="3.2" fill="{ORANGE}"/>')

SM=[]; RM=[]
for i in np.where(me)[0][::2]:
    x,y=specxy(e[i],ratio[i])
    _,yl=specxy(e[i],ratio[i]-err[i])
    _,yh=specxy(e[i],ratio[i]+err[i])
    SM += [
        line(x,yl,x,yh,1.0,GRAY,.62),
        f'<circle cx="{x:.2f}" cy="{y:.2f}" r="2" fill="{INK}" opacity=".82"/>'
    ]
    x,y=resxy(e[i],resid[i])
    RM.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="2.1" fill="{TEAL}"/>')

zero=resxy(4,0)[1]
bx,by=mx(dm_best),my(s12_best)

base=f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}">
<rect width="{W}" height="{H}" fill="white"/>
{''.join(linework)}
<path d="{top}" fill="none" stroke="{TEAL}" stroke-width="3.6" stroke-linecap="round"/>
<path d="{right}" fill="none" stroke="{TEAL}" stroke-width="3.6" stroke-linecap="round"/>
<path d="{cpath(11.83)}" fill="{TP}" stroke="{T3}" stroke-width="2.6"/>
<path d="{cpath(6.18)}" fill="{T3}" stroke="{T2}" stroke-width="2.8" opacity=".90"/>
<path d="{cpath(2.30)}" fill="{T2}" stroke="{TEAL}" stroke-width="3.0" opacity=".84"/>
<circle cx="{bx:.2f}" cy="{by:.2f}" r="6.6" fill="{ORANGE}"/>
<circle cx="{bx:.2f}" cy="{by:.2f}" r="11" fill="none" stroke="{ORANGE}" stroke-width="1.5" opacity=".52"/>
<g id="juno-detector">{''.join(DET)}</g>
{''.join(SM)}
<path d="{fitpath}" fill="none" stroke="{TEAL}" stroke-width="3.4" stroke-linecap="round"/>
<line x1="{ZX}" y1="{zero:.2f}" x2="{ZX+ZW}" y2="{zero:.2f}" stroke="{GRID}" stroke-width="1.4"/>
{''.join(RM)}
</svg>'''

# All graph labels in Computer Modern mathtext, converted to SVG paths.
plt.rcParams.update({
    "mathtext.fontset":"cm",
    "font.family":"serif",
    "svg.fonttype":"path"
})
fig=plt.figure(figsize=(W/72,H/72),dpi=72,facecolor="none")
ax=fig.add_axes([0,0,1,1])
ax.set_axis_off()
ax.set_xlim(0,W)
ax.set_ylim(H,0)

def lab(x,y,s,size,ha="center",rot=0):
    ax.text(x,y,s,fontsize=size,ha=ha,va="center",
            rotation=rot,color=INK)

for v in [7.45,7.47,7.49,7.51,7.53]:
    lab(mx(v),PY+PH+25,rf"${v:.2f}$",13)
for v in [0.306,0.308,0.310,0.312,0.314]:
    lab(PX-12,my(v),rf"${v:.3f}$",13,"right")
lab(PX+PW/2,PY+PH+57,r"$\Delta m^2_{21}\,[10^{-5}\,\mathrm{eV}^2]$",19)
lab(PX-82,PY+PH/2,r"$\sin^2\theta_{12}$",19,rot=90)

for v in [7.45,7.47,7.49,7.51,7.53]:
    x=TX+(v-DM_MIN)/(DM_MAX-DM_MIN)*TWID
    lab(x,TY+TH+20,rf"${v:.2f}$",11)
for v in [0,2,4,6]:
    y=TY+TH-v/QMAX*TH
    lab(TX-9,y,rf"${v}$",11,"right")
lab(TX+TWID/2,TY-13,r"$q_{\mathrm{p}}(\Delta m^2_{21})$",15)

for v in [0,2,4,6]:
    lab(RX+v/QMAX*RW,RY+RH+20,rf"${v}$",11)
for v in [0.306,0.308,0.310,0.312,0.314]:
    y=RY+RH-(v-S12_MIN)/(S12_MAX-S12_MIN)*RH
    lab(RX-9,y,rf"${v:.3f}$",11,"right")
lab(RX+RW/2,RY-13,r"$q_{\mathrm{p}}(\sin^2\theta_{12})$",15)

for v in [2,3,4,5,6,7]:
    lab(specxy(v,.12)[0],SY+SH+22,rf"${v}$",12)
for v in [.2,.4,.6,.8]:
    lab(SX-10,specxy(1.2,v)[1],rf"${v:.1f}$",12,"right")
lab(SX+SW/2,SY+SH+50,r"$E_{\mathrm{vis}}\,[\mathrm{MeV}]$",18)
lab(SX-61,SY+SH/2,r"$N/N_0$",18,rot=90)

for v in [2,3,4,5,6,7]:
    lab(resxy(v,-3.5)[0],ZY+ZH+20,rf"${v}$",11)
for v in [-2,0,2]:
    lab(ZX-9,resxy(1.2,v)[1],rf"${v}$",11,"right")
lab(ZX+ZW/2,ZY+ZH+45,r"$E_{\mathrm{vis}}\,[\mathrm{MeV}]$",16)
lab(ZX-63,ZY+ZH/2,r"$\frac{n-\hat{\mu}}{\sqrt{\hat{\mu}}}$",17,rot=90)

overlay=BUILD/"_math_overlay.svg"
fig.savefig(overlay,format="svg",transparent=True)
plt.close(fig)

ov=overlay.read_text(encoding="utf-8")
inner=re.sub(r"^.*?<svg\b[^>]*>","",ov,count=1,flags=re.S)
inner=re.sub(r"</svg>\s*$","",inner,count=1,flags=re.S)
inner=inner.replace("xlink:href","href")
ids=re.findall(r'id="([^"]+)"',inner)
for old in sorted(ids,key=len,reverse=True):
    new="math_"+old
    inner=inner.replace(f'id="{old}"',f'id="{new}"')
    inner=inner.replace(f'url(#{old})',f'url(#{new})')
    inner=inner.replace(f'href="#{old}"',f'href="#{new}"')

final=re.sub(
    r"</svg>\s*$",
    lambda _:inner+"\n</svg>",
    base,
    count=1,
    flags=re.S
)
OUT_SVG.write_text(final,encoding="utf-8")
cairosvg.svg2png(
    bytestring=final.encode("utf-8"),
    write_to=str(OUT_PNG),
    output_width=1800,
    output_height=1674,
    background_color="white"
)
overlay.unlink(missing_ok=True)

print(OUT_SVG)
print(OUT_PNG)
