#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Compile upstream unchanged and with observation-only hooks, plus our adapter."""
from pathlib import Path
import json, os, subprocess, tempfile
ROOT=Path(__file__).resolve().parents[1]
def format_backend(compiler):
 """Probe the real toolchain without the shim on its include path."""
 with tempfile.TemporaryDirectory(prefix='barricelli-format-') as tmp:
  probe=subprocess.run([compiler,'-std=c++20','-x','c++','-','-o',str(Path(tmp)/'probe')],
   input='#include <format>\n#include <string>\nint main(){return std::format("{:2}",42)=="42" ? 0 : 1;}\n',capture_output=True,text=True)
  return 'native' if probe.returncode==0 else 'compatibility'
def build():
 builddir=ROOT/'build'; builddir.mkdir(exist_ok=True)
 src=(ROOT/'engine/upstream/barricelli54.cpp').read_text()
 observed=src.replace('bool debug = false;', 'bool debug = false;\n#include "hooks.hpp"')
 for name in ['Symbiotic','Exclusion','Conditional']:
  sig=f'void reproduce{name}(int i, int j, int level)\n{{'
  observed=observed.replace(sig,sig+'\n    CopyScope copy_scope(i,j,level);')
  start=observed.index(sig); end=observed.index('\n}\n',start)
  body=observed[start:end]
  body=body.replace('        if ((world[j]', '        copy_scope.finish();\n        if ((world[j]')
  body=body.replace(f'            reproduce{name}(i,',f'            HelperScope helper_scope(j);\n            reproduce{name}(i,')
  observed=observed[:start]+body+observed[end:]
 observed=observed.replace('                    nextWorld[j] = (rpos-lpos)', '                    copy_scope.is_mutation=true;\n                    nextWorld[j] = (rpos-lpos)')
 observed=observed.replace('        // copy state to same position on next line', '        CopyScope stay_scope(i,i,0);\n        // copy state to same position on next line')
 observed=observed.replace('        // reproduce state elsewhere on next line','        stay_scope.finish();\n        // reproduce state elsewhere on next line')
 observed=observed.replace('            if (c >= 0 && c < worldSize)', '            CopyScope move_scope(i,c,1);\n            if (c >= 0 && c < worldSize)')
 (builddir/'instrumented_reference.cpp').write_text(observed)
 compiler=os.environ.get('CXX','g++'); backend=format_backend(compiler)
 common=[compiler,'-std=c++20','-O2']
 if backend=='compatibility': common+=['-I'+str(ROOT/'engine/compat')]
 common+=['-I'+str(ROOT/'engine'),'-I'+str(builddir)]
 subprocess.run(common+[str(ROOT/'engine/upstream/barricelli54.cpp'),'-o',str(builddir/'reference')],check=True)
 subprocess.run(common+[str(ROOT/'engine/adapter.cpp'),'-o',str(builddir/'simulator')],check=True)
 subprocess.run(common+[str(ROOT/'engine/symbiotic_oracle.cpp'),'-o',str(builddir/'symbiotic_oracle')],check=True)
 (builddir/'build_metadata.json').write_text(json.dumps({'compiler':subprocess.check_output([compiler,'--version'],text=True).splitlines()[0],'format_backend':backend,'flags':common[1:],'selection':'native header compile/link probe without compatibility include; shim only on failure'},indent=2)+'\n')
if __name__=='__main__': build()
