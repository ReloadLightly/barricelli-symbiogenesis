#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Save data-derived prints, streaming reveal GIFs and rendering recipes."""
import json,pathlib,sys,math
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from barricelli.run import ROOT,read_csv,save_json,sha
from barricelli.plot import color,PALETTE
import numpy as np
from PIL import Image,ImageDraw,ImageFont,GifImagePlugin
ART=ROOT/'results/art'

def font(size): return ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf',size)
def rgb(arr):
 out=np.zeros((*arr.shape,3),dtype=np.uint8)
 for value in np.unique(arr): out[arr==value]=tuple(bytes.fromhex(color(value)[1:]))
 return Image.fromarray(out)
def export(path,slug,title,animation=True):
 path=pathlib.Path(path); arr=read_csv(path/'trajectory.csv'); conf=json.loads((path/'config.json').read_text()); ART.mkdir(parents=True,exist_ok=True)
 image=rgb(arr); scale=max(1,math.ceil(4096/arr.shape[1])); target=(arr.shape[1]*scale,arr.shape[0]*scale)
 # Extremely tall trajectories get a smaller integer scale to stay below64M pixels.
 while target[0]*target[1]>64000000 and scale>1: scale-=1; target=(arr.shape[1]*scale,arr.shape[0]*scale)
 margin=160; canvas=Image.new('RGB',(target[0]+2*margin,target[1]+360),PALETTE['background']); draw=ImageDraw.Draw(canvas)
 draw.text((margin,45),title,font=font(44),fill=PALETTE['text'])
 ref=f"seed {conf['seed']}" if conf.get('seed') is not None else 'frozen initial '+sha(path/'initial.csv')[:12]
 draw.text((margin,110),f"{conf['model']} / {conf['norm']} | {ref} | W{conf['width']} · T{conf['steps']}",font=font(24),fill=PALETTE['accent'])
 canvas.paste(image.resize(target,Image.Resampling.NEAREST),(margin,180))
 draw.text((margin,target[1]+220),'POSITION x →     TIME t ↓     /     SELECTED NUMERICAL WORK',font=font(26),fill=PALETTE['text'])
 draw.text((margin,target[1]+268),'Value colors; no organism identities. Source '+sha(path/'trajectory.csv')[:20],font=font(22),fill=PALETTE['accent'])
 canvas.save(ART/(slug+'.png'),dpi=(300,300)); del canvas
 recipe={'title':title,'selected_artwork':True,'source_run':str(path.relative_to(ROOT)),'trajectory_sha256':sha(path/'trajectory.csv'),'initial_sha256':sha(path/'initial.csv'),
  'profile':conf['model'],'norm':conf['norm'],'seed':conf.get('seed'),'width':conf['width'],'updates':conf['steps'],'palette_file':'configs/palette.json','palette_sha256':sha(ROOT/'configs/palette.json'),
  'renderer_file':'scripts/art.py','renderer_sha256':sha(pathlib.Path(__file__)),'font_file':'/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf','font_sha256':sha('/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf'),
  'print':{'integer_scale':scale,'resampling':'nearest','nominal_dpi':300,'dimensions':[target[0]+320,target[1]+360]},
  'interpretation':'aesthetic curation of an actual numerical history; no biological claim','interventions':conf.get('modifications',[])}
 if animation:
  values=list(map(int,np.unique(np.concatenate([arr.ravel(),[0]]))))
  if len(values)>256: raise ValueError('GIF palette exceeds256 values; use atlas replay')
  palette=[]
  for v in values: palette.extend(bytes.fromhex(color(v)[1:]))
  label_text=len(values); label_accent=len(values)+1
  palette.extend(bytes.fromhex(PALETTE['text'][1:])); palette.extend(bytes.fromhex(PALETTE['accent'][1:]))
  if len(palette)>768: raise ValueError('GIF palette exceeds256 colors including labels')
  palette.extend([0]*(768-len(palette))); index={v:i for i,v in enumerate(values)}
  encoded=np.zeros(arr.shape,dtype=np.uint8)
  for v,i in index.items(): encoded[arr==v]=i
  blank=np.full(arr.shape,index[0],dtype=np.uint8)
  base=Image.new('P',(arr.shape[1]+40,arr.shape[0]+120),index[0]); base.putpalette(palette)
  draw=ImageDraw.Draw(base); draw.text((20,12),title,font=font(16),fill=label_text)
  draw.text((20,37),conf['model']+' / '+conf['norm'],font=font(12),fill=label_accent)
  draw.text((20,58),'POSITION x →      TIME t ↓',font=font(12),fill=label_text)
  draw.text((20,arr.shape[0]+92),f"SELECTED / {ref} / W{conf['width']} T{conf['steps']}",font=font(12),fill=label_accent)
  with (ART/(slug+'.gif')).open('wb') as stream:
   header,_=GifImagePlugin.getheader(base,info={'loop':0,'background':index[0],'optimize':False})
   for block in header: stream.write(block)
   for reveal in np.linspace(0,len(arr),40,dtype=int):
    frame=blank.copy(); frame[:reveal]=encoded[:reveal]; im=base.copy(); data_image=Image.fromarray(frame,'P'); data_image.putpalette(palette); im.paste(data_image,(20,80))
    for block in GifImagePlugin.getdata(im,duration=100 if reveal<len(arr) else 1200,disposal=2): stream.write(block)
   stream.write(b';')
  recipe['animation']={'type':'progressive reveal of saved rows','frames':40,'frame_ms':100,'final_hold_ms':1200,'loops':True,'streamed':True,'frame_dimensions':[arr.shape[1]+40,arr.shape[0]+120],'numerical_crop':[20,80,20+arr.shape[1],80+arr.shape[0]],'time_axis':'downward, explicitly labeled; revealed rows do not alter simulation'}
 save_json(ART/(slug+'.recipe.json'),recipe); return recipe

def main():
 selections=[('results/reconstruction/galloway2026','confluence','Confluence / 2026'),('results/ensemble/galloway2029','strata','Strata / 2029'),('results/ensemble/galloway2030','fault-lines','Fault lines / 2030')]
 save_json(ART/'curation.json' if ART.exists() else ROOT/'results/art-curation.json',{'selection':'three selected illustrations from the complete six-run published-profile ensemble; aesthetic judgments, not scientific sampling','works':[{'run':p,'slug':s,'title':t} for p,s,t in selections]})
 recipes=[export(ROOT/p,s,t) for p,s,t in selections]; save_json(ART/'manifest.json',recipes)
 print([(r['title'],r['print']['dimensions']) for r in recipes])
if __name__=='__main__': main()
