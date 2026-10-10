// SPDX-License-Identifier: GPL-3.0-only
// Observation hooks added 2026-10-10. They never alter world/nextWorld.
#include <fstream>
#include <map>
#include <chrono>
long long attempt_count=0, accepted_count=0, collision_count=0, produced_count=0, erasure_count=0;
long long fresh_count=0, same_count=0, out_count=0, cap_count=0;
int current_step=0, trace_steps=0;
bool use_world_depth_cap=true;
std::ofstream event_stream;
std::vector<int> helper_stack, target_writers;
struct CopyScope {
 int source,target,level,before,value; bool finished=false,active,is_mutation=false;
 CopyScope(int i,int j,int depth):source(i),target(j),level(depth),value(world[i]) {
  active=value!=0 && value!=X_MARK;
  before=(j>=0 && j<worldSize)?nextWorld[j]:0;
  if(active) ++attempt_count;
 }
 void finish() {
  if(finished || !active) { finished=true; return; } finished=true;
  bool inside=target>=0 && target<worldSize;
  int after=inside?nextWorld[target]:0;
  std::string outcome;
  if(use_world_depth_cap && level>worldSize) { ++cap_count; outcome="depth_cap"; }
  else if(!inside) { ++out_count; outcome="out_of_bounds"; }
  else {
   bool collision=before!=0 && before!=value;
   if(collision) ++collision_count;
   if(is_mutation) { ++produced_count; outcome="mutation"; }
   else if(after==value) { ++accepted_count; if(before==value) { ++same_count; outcome="same"; } else { ++fresh_count; outcome="copy"; } }
   else if(after==X_MARK || after==0) outcome="excluded";
   else { ++produced_count; outcome="mutation"; }
   if(before!=0 && before!=X_MARK && (after==0 || after==X_MARK)) ++erasure_count;
  }
  if(event_stream.is_open() && current_step<trace_steps) {
   event_stream << current_step << ',' << source << ',' << target << ',' << level << ',' << value << ',' << before << ',' << after << ',' << outcome << ',';
   if(inside) event_stream << target_writers[target]; else event_stream << -1;
   event_stream << ",\"";
   for(size_t k=0;k<helper_stack.size();++k) {
    if(k) event_stream << ';'; int p=helper_stack[k]; event_stream << p << ':' << world[p];
   }
   event_stream << "\"\n";
  }
  if(inside && (!use_world_depth_cap || level<=worldSize)) target_writers[target]=source;
 }
 ~CopyScope() { finish(); }
};
struct HelperScope {
 HelperScope(int j) { helper_stack.push_back(j); }
 ~HelperScope() { helper_stack.pop_back(); }
};
