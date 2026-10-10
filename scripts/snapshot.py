#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Deterministic compact source archive and regeneration-version manifest."""
import gzip,tarfile,json,pathlib,sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from barricelli.run import ROOT,sha,save_json,REFERENCE_COMMIT
def main():
 files=[]
 for folder in ['engine','barricelli','scripts','configs','fixtures','tests','atlas','references']:
  for p in (ROOT/folder).rglob('*'):
   if p.is_file() and '__pycache__' not in str(p) and p.name not in ['data.js','manifest.json','register.html','source_manifest.json']: files.append(p)
 for name in ['README.md','AGENTS.md','PROVENANCE.md','NOTICES.md','RESEARCH_RECORD.md','DEVELOPMENT_LOG.md','LICENSE','Makefile','pyproject.toml','requirements.txt','.gitignore']: files.append(ROOT/name)
 archive_path=ROOT/'results/source_snapshot.tar.gz'
 with archive_path.open('wb') as raw:
  with gzip.GzipFile(filename='',fileobj=raw,mode='wb',mtime=0) as zipped:
   with tarfile.open(fileobj=zipped,mode='w') as archive:
    for p in sorted(files):
     entry=archive.gettarinfo(str(p),arcname=str(p.relative_to(ROOT))); entry.mtime=0; entry.uid=entry.gid=0; entry.uname=entry.gname=''
     with p.open('rb') as stream: archive.addfile(entry,stream)
 p=ROOT/'references/source_manifest.json'
 if p.exists(): d=json.loads(p.read_text())
 else:
  retained=[ROOT/'engine/upstream/barricelli54.cpp',ROOT/'engine/upstream/README.md',ROOT/'LICENSE',*sorted((ROOT/'fixtures').glob('*.csv'))]
  d={'reference_repository':'https://github.com/tim-taylor/barricelli54','actual_commit':REFERENCE_COMMIT,'retained_files_sha256':{str(f.relative_to(ROOT)):sha(f) for f in retained}}
 d['final_regeneration_snapshot']={'archive':str(archive_path.relative_to(ROOT)),'sha256':sha(archive_path),'files_sha256':{str(f.relative_to(ROOT)):sha(f) for f in sorted(files)},'native_binary_sha256':sha(ROOT/'build/simulator'),'reference_binary_sha256':sha(ROOT/'build/reference'),'note':'final buildable source; earlier per-run source hashes remain intact; complete current-engine numeric replay verifies compatibility; saved results are retained separately in the full repository'}
 if (ROOT/'build/symbiotic_oracle').exists(): d['final_regeneration_snapshot']['symbiotic_oracle_binary_sha256']=sha(ROOT/'build/symbiotic_oracle')
 save_json(p,d); print('source snapshot:',len(files),'files,',archive_path.stat().st_size,'bytes')
if __name__=='__main__': main()
