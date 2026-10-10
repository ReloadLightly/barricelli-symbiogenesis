#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Pin and hash the modern primary sources actually inspected."""
import sys,pathlib,concurrent.futures,json,datetime,hashlib,urllib.request
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
import retrieve_sources as source
source.cache=pathlib.Path('/tmp/barricelli-related-sources'); source.cache.mkdir(exist_ok=True)
urls={
 'asal.html':'https://arxiv.org/html/2412.17799',
 'asal-plus-plus.html':'https://arxiv.org/html/2509.22447',
 'computational-life.html':'https://arxiv.org/html/2406.19108',
 'bff-followup.html':'https://arxiv.org/html/2607.01483',
 'distributed-replication.html':'https://arxiv.org/html/2508.08047',
 'programmable-ca.html':'https://arxiv.org/html/2609.06102',
 'lenia.html':'https://arxiv.org/html/1812.05433',
 'genetic-images.html':'https://www.karlsims.com/genetic-images.html'}
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex: records=list(ex.map(source.retrieve,urls.items()))
pathlib.Path('references/related-retrieval.json').write_text(json.dumps(records,indent=2)+'\n')
for r in records: print(r['name'],r.get('bytes'),r.get('error','ok'))
