#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Compile upstream unchanged and with observation-only hooks, plus our adapter."""
from pathlib import Path
import subprocess
ROOT=Path(__file__).resolve().parents[1]
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
 common=['g++','-std=c++20','-O2','-I'+str(ROOT/'engine/compat'),'-I'+str(ROOT/'engine'),'-I'+str(builddir)]
 subprocess.run(common+[str(ROOT/'engine/upstream/barricelli54.cpp'),'-o',str(builddir/'reference')],check=True)
 subprocess.run(common+[str(ROOT/'engine/adapter.cpp'),'-o',str(builddir/'simulator')],check=True)
 subprocess.run(common+[str(ROOT/'engine/symbiotic_oracle.cpp'),'-o',str(builddir/'symbiotic_oracle')],check=True)
if __name__=='__main__': build()
