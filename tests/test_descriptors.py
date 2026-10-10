# SPDX-License-Identifier: GPL-3.0-only
import unittest
from unittest.mock import patch
from types import SimpleNamespace
import numpy as np
from barricelli.descriptors import signatures, translation, describe
from scripts.build import format_backend
from barricelli.motifs import matches,disjoint

class CorrectedDiagnostics(unittest.TestCase):
 def test_stationary_periodic_and_empty_are_not_motion(self):
  for row in (np.zeros(32,dtype=int),np.tile([1,-1],16)):
   d=describe(np.tile(row,(4,1)),boundary='ring')
   self.assertEqual(d['exact_translation_fraction'],0)
   self.assertEqual(d['median_best_shift'],0)
   self.assertEqual(d['stationary_fraction'],1)
 def test_nonstationary_periodic_aliases_are_ambiguous(self):
  old=np.tile([1,-1],16); result=translation(old,-old,'ring')
  self.assertEqual(result['kind'],'ambiguous_motion'); self.assertIsNone(result['shift'])
 def test_open_motion_does_not_wrap_or_accept_boundary_loss(self):
  old=np.zeros(32,dtype=int); old[-1]=5; new=np.roll(old,1)
  self.assertEqual(translation(old,new,'ring')['shift'],1)
  self.assertEqual(translation(old,new,'open')['kind'],'no_exact_motion')
  self.assertEqual(translation(old,np.zeros_like(old),'open')['kind'],'no_exact_motion')
 def test_unique_open_motion(self):
  old=np.zeros(32,dtype=int); old[10:12]=[5,-3]
  self.assertEqual(translation(old,np.roll(old,3),'open')['shift'],3)
 def test_seam_windows_depend_on_boundary(self):
  row=np.array([1,0,0,0,0,-3])
  self.assertEqual(sum(signatures(row,boundary='open').values()),0)
  self.assertEqual(sum(signatures(row,boundary='ring').values()),3)
 def test_short_open_world_and_invalid_boundary(self):
  self.assertFalse(signatures(np.array([1,-1]),boundary='open'))
  with self.assertRaises(ValueError): signatures(np.array([1,-1]),boundary='mirror')
 def test_exact_motif_and_guard_cross_ring_seam(self):
  row=np.array([-3,0,0,0,0,0,0,1])
  self.assertEqual(matches(row,[1,-3],guard=2,boundary='ring'),[7])
  self.assertEqual(matches(row,[1,-3],boundary='open'),[])
 def test_ring_footprints_do_not_overlap_across_seam(self):
  self.assertEqual(disjoint([0,3,7],2,8,'ring'),[0,3])
 def test_native_format_probe_never_sees_shim(self):
  with patch('scripts.build.subprocess.run',return_value=SimpleNamespace(returncode=0)) as call:
   self.assertEqual(format_backend('test-cxx'),'native')
   self.assertFalse(any('compat' in a for a in call.call_args.args[0]))
 def test_failed_native_probe_selects_compatibility(self):
  with patch('scripts.build.subprocess.run',return_value=SimpleNamespace(returncode=1)):
   self.assertEqual(format_backend('test-cxx'),'compatibility')

if __name__=='__main__': unittest.main()
