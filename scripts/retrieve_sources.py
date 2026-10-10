#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Download requested sources to a local cache; retain hashes and retrieval evidence."""
import concurrent.futures, datetime, hashlib, json, pathlib, urllib.request
SOURCES = {
 'barricelli2026numerical.pdf':'https://www.tim-taylor.com/papers/barricelli2026numerical.pdf',
 'taylor2026commentary.pdf':'https://www.tim-taylor.com/papers/taylor2026commentary.pdf',
 'Barricelli.pde':'https://cultureandcommunication.org/galloway/Barricelli/Barricelli.pde',
 'galloway-index.html':'https://cultureandcommunication.org/galloway/Barricelli/',
 'galloway-retrospective.html':'https://cultureandcommunication.org/galloway/ephemera-pt-3-barricelli',
 'ashford-arxiv-v1.html':'https://arxiv.org/html/2603.08463v1',
 'ashford-arxiv-abstract.html':'https://arxiv.org/abs/2603.08463',
 'chapter-5.html':'https://www.tim-taylor.com/selfrepbook/web/chapter-5.html',
 'gecco-doi.html':'https://doi.org/10.1145/3795101.3814707',
 'symba-readme.md':'https://raw.githubusercontent.com/JELAshford/symba-alice-2026/main/README.md',
}
def retrieve(item):
 name,url=item; result={'name':name,'url':url,'retrieved_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
 try:
  with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'barricelli-research/0.1'}),timeout=35) as r:
   data=r.read(); result.update(status=r.status,final_url=r.url,bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
  (cache/name).write_bytes(data)
 except Exception as e: result['error']=str(e)
 return result
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser(); p.add_argument('--cache',default='/tmp/barricelli-sources'); a=p.parse_args()
 cache=pathlib.Path(a.cache); cache.mkdir(parents=True,exist_ok=True)
 with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex: records=list(ex.map(retrieve,SOURCES.items()))
 pathlib.Path('references/retrieval.json').write_text(json.dumps(records,indent=2)+'\n')
 for r in records: print(r['name'],r.get('bytes'),r.get('error','ok'))
