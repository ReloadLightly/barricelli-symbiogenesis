# SPDX-License-Identifier: GPL-3.0-only
"""Thin tests for fixture fidelity, encountered collision edges and assay meaning."""
import csv,json,pathlib,subprocess,tempfile,unittest
import numpy as np
from barricelli.run import ROOT,read_csv,validate,recurrence
from barricelli.motifs import matches
class Fidelity(unittest.TestCase):
 def simulate(self,profile,norm,row,steps=1):
  with tempfile.TemporaryDirectory() as td:
   td=pathlib.Path(td); np.savetxt(td/'initial.csv',np.array(row)[None,:],fmt='%d',delimiter=',')
   subprocess.run([str(ROOT/'build/simulator'),profile,norm,str(steps),str(td/'initial.csv'),str(td/'trajectory.csv'),str(td/'stats.json'),str(td/'events.csv'),'1'],check=True)
   with (td/'events.csv').open() as stream: events=list(csv.DictReader(stream))
   return read_csv(td/'trajectory.csv'),json.loads((td/'stats.json').read_text()),events
 def test_all_historical_fixtures(self):
  for figure in range(1,23):
   with self.subTest(figure=figure):
    config=json.loads((ROOT/f'configs/figure{figure:02d}.json').read_text()); expected=read_csv(ROOT/config['initial_state_file'])
    actual,_,_=self.simulate(config['model'],config['norm'],expected[0],config['steps'])
    np.testing.assert_array_equal(actual,expected)
 def test_galloway_erasure_allows_later_reuse(self):
  row=np.zeros(511,dtype=int); row[8:12]=[2,1,7,-1]
  arr,stats,events=self.simulate('galloway_published','galloway_B',row)
  self.assertEqual(arr[1,10],-1)
  arrivals=[e for e in events if e['target']=='10']
  self.assertEqual([e['outcome'] for e in arrivals],['copy','excluded','copy'])
 def test_equal_helper_recurses_three_attempts(self):
  row=np.zeros(511,dtype=int); row[:2]=1
  arr,stats,events=self.simulate('galloway_published','galloway_B',row)
  self.assertEqual(stats['attempted_copies'],4)
  self.assertEqual(len([e for e in events if e['source']=='0']),3)
  self.assertEqual(arr[1,1],1); self.assertEqual(arr[1,2],1)
 def test_ring_wrap_and_old_row_mutation(self):
  row=np.zeros(511,dtype=int); row[0]=-1
  arr,_,_=self.simulate('galloway_published','galloway_B',row)
  self.assertEqual(arr[1,510],-1)
  row[:]=0; row[8]=2; row[11]=-1
  arr,stats,_=self.simulate('galloway_published','galloway_B',row)
  self.assertEqual(arr[1,10],-2); self.assertEqual(stats['newly_produced_values'],1)
 def test_exclusion_marker_not_empty_and_does_not_reproduce(self):
  arr,stats,_=self.simulate('research','exclusion',[0,1,-1,0])
  self.assertEqual(arr[1,1],-1)
  arr,stats,_=self.simulate('research','exclusion',[99999,0,0])
  np.testing.assert_array_equal(arr[1],[0,0,0]); self.assertEqual(stats['attempted_copies'],0)
 def test_historical_open_boundary(self):
  arr,stats,_=self.simulate('research','symbiotic',[-1,0,0])
  self.assertFalse(arr[1].any()); self.assertEqual(stats['out_of_bounds'],1)
 def test_constituent_collision_norms(self):
  arr,stats,_=self.simulate('research','galloway_B',[1]); self.assertEqual(stats['accepted_outcomes'],3)
  row=np.zeros(128,dtype=int); row[8]=2; row[11]=-1
  for norm,expected in [('galloway_A',-3),('galloway_B',-2),('galloway_0',0),('galloway_AB_halves',-3),('galloway_AB_quarters',-3)]:
   arr,_,_=self.simulate('research',norm,row); self.assertEqual(arr[1,10],expected)
  row[:]=0; row[88]=2; row[91]=-1
  arr,_,_=self.simulate('research','galloway_AB_halves',row); self.assertEqual(arr[1,90],-2)
 def test_recurrence_includes_environment_phase(self):
  arr=np.array([[1],[1],[1]],dtype=np.int32)
  self.assertEqual(recurrence(arr,2)['period'],2)
  self.assertEqual(recurrence(arr,1)['period'],1)
  conf={'model':'research','norm':'galloway_AB_quarters','steps':1,'width':3,'boundary':'ring','modifications':['test']}
  with self.assertRaises(ValueError): validate(conf)
 def test_template_translations_and_domain_guard(self):
  row=np.array([0,0,1,-1,1,-1,1,-1,0,0])
  self.assertEqual(matches(row,[1,-1,1,-1]),[2,4])
  self.assertEqual(matches(row,[1,-1,1,-1],guard=2),[])
 def test_profiles_do_not_silently_mix(self):
  conf=json.loads((ROOT/'configs/figure07.json').read_text()); conf['steps']=48
  with self.assertRaises(ValueError): validate(conf)
  conf=json.loads((ROOT/'configs/galloway_published.json').read_text()); conf['width']=512
  with self.assertRaises(ValueError): validate(conf)
if __name__=='__main__': unittest.main()
