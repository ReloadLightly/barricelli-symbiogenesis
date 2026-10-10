#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Optional real-browser smoke checks; Playwright is a development dependency."""
import os,pathlib,sys,json,time
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
os.environ.setdefault('PLAYWRIGHT_BROWSERS_PATH','/tmp/barricelli-browsers')
from barricelli.run import ROOT,save_json,read_csv
from barricelli.plot import color
from playwright.sync_api import sync_playwright

def main():
 errors=[]; assertions=[]
 with sync_playwright() as p:
  browser=p.chromium.launch(headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
  page=browser.new_page(viewport={'width':1440,'height':1000}); page.on('pageerror',lambda e:errors.append(str(e)))
  expected_worlds=len(json.loads((ROOT/'atlas/manifest.json').read_text())['worlds'])
  page.goto((ROOT/'atlas/index.html').as_uri()); page.wait_for_function('window.ATLAS && document.querySelectorAll("#world option").length===window.ATLAS.worlds.length')
  assert page.locator('#world option').count()==expected_worlds; assertions.append(f'{expected_worlds} worlds selectable from saved numerical payload')
  expected_prints=len(list((ROOT/'results/art').glob('*.recipe.json')))
  assert page.locator('#printcards article').count()==expected_prints; assertions.append(f'{expected_prints} linked print/animation/recipe cards')
  # Avoid the global browser History object: canvas is the source of dimensions.
  data=page.evaluate('({width:canvas.width,height:canvas.height,value:current.values[0],rgb:Array.from(ctx.getImageData(0,0,1,1).data)})')
  assert [data['width'],data['height']]==[511,512]; assert data['rgb'][:3]==list(bytes.fromhex(color(data['value'])[1:])); assertions.append('canvas dimensions and integer-value palette agree with source data')
  page.locator('#reset').click(); assert page.locator('#time').input_value()=='0'
  page.locator('#play').click(); page.wait_for_function('Number(document.getElementById("time").value)>3'); page.locator('#play').click(); assertions.append('reset, timed reveal and pause operate without changing data')
  page.locator('#time').evaluate('(el)=>{el.value=511;el.dispatchEvent(new Event("input"))}')
  page.locator('#history').scroll_into_view_if_needed(); box=page.locator('#history').bounding_box(); page.mouse.click(box['x']+box['width']*.4,box['y']+box['height']*.2)
  assert 'value' in page.locator('#readout').inner_text(); assert 'x:' in page.locator('#numbers').inner_text(); assertions.append('cell readout and numerical close-up work')
  if page.locator('#zoom').count():
   assert page.evaluate('document.getElementById("zoom").width>0'); assert 't' in page.locator('#zoomnote').inner_text(); assertions.append('coordinate-labelled enlarged pixel close-up is generated from saved integers')
  page.locator('#world').select_option('results--search--codex_feedback--repeat3--trial07'); assert page.locator('#neighbors button').count()==4
  page.locator('#neighbors button').first.click(); assert 'Nearby' in page.locator('#world option:checked').inner_text(); assertions.append('saved nearby variants navigate correctly')
  r6='results--descendant_detector--runs--copying_positive'
  if page.locator(f'#world option[value="{r6}"]').count():
   page.locator('#world').select_option(r6)
   data=page.evaluate('({width:canvas.width,height:canvas.height,rgb:Array.from(ctx.getImageData(64,0,1,1).data)})')
   assert [data['width'],data['height']]==[256,17]
   assert data['rgb'][:3]==list(bytes.fromhex(color(8)[1:])); assertions.append('R6 copying calibration replays its saved dimensions and integer palette')
  r7='results--partner_dyad--runs--construction_d4_intact--continuation'
  if page.locator(f'#world option[value="{r7}"]').count():
   page.locator('#world').select_option(r7)
   data=page.evaluate('({width:canvas.width,height:canvas.height,rgb:Array.from(ctx.getImageData(236,1,1,1).data),value:current.values[512+236]})')
   assert [data['width'],data['height']]==[512,13] and data['value']==4
   assert data['rgb'][:3]==list(bytes.fromhex(color(4)[1:])); assertions.append('R7 child pixels agree with the saved first-generation integers')
   assert page.locator('#neighbors button').count()==6
   page.locator('#world').select_option('results--partner_dyad--runs--construction_d4_negative_removed--continuation')
   assert page.evaluate('current.values.filter(v=>v===-4).length')==0
   page.locator('#neighbors button').first.click(); assert page.locator('#world').input_value()==r7
   assertions.append('R7 partner-deletion replay and six matched treatment neighbors operate')
  page.locator('#world').select_option('results--reconstruction--galloway2026'); page.evaluate('window.scrollTo(0,0)'); page.screenshot(path=str(ROOT/'results/atlas-desktop.png'),full_page=True)
  page.set_viewport_size({'width':390,'height':844}); page.screenshot(path=str(ROOT/'results/atlas-mobile.png'),full_page=True)
  assert page.evaluate('document.documentElement.scrollWidth<=window.innerWidth'); assertions.append('390px mobile viewport has no horizontal overflow')
  page.goto((ROOT/'atlas/register.html').as_uri()); total=page.locator('tbody tr').count(); assert total==len(json.loads((ROOT/'results/run_register.json').read_text()))
  page.locator('#filter').fill('galloway_published'); count=page.locator('tbody tr:visible').count(); assert 0<count<total; assertions.append(f'complete {total}-run register filters correctly')
  assert not errors,errors; browser.close()
 save_json(ROOT/'results/atlas_qa.json',{'browser':'Playwright Chromium, local file URLs; no hosted service','assertions':assertions,'page_errors':errors,'screenshots':['results/atlas-desktop.png','results/atlas-mobile.png']}); print('atlas browser checks passed')
if __name__=='__main__': main()
