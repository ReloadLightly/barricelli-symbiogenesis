// SPDX-License-Identifier: GPL-3.0-only
// Research adapter, 2026-10-10. Taylor's numerical functions are included
// with observation hooks. Galloway behavior is independently authored here.
#define main taylor_original_main
#include "instrumented_reference.cpp"
#undef main
#include <fstream>
#include <sstream>
#include <limits>
#include <stdexcept>
#include <sys/resource.h>

int wrap(int p) { int r=p%worldSize; return r<0?r+worldSize:r; }
int ring_nearest(int j,int direction) {
 for(int d=0;d<worldSize;++d) if(world[wrap(j+direction*d)]!=0) return d;
 throw std::runtime_error("nearest lookup on empty row");
}
// Published effective collision norm B; optional research A/0 declared in config.
std::string collision_rule="B";
void galloway_shift(int source,int delta,int depth) {
 int value=world[source]; if(value==0) return;
 int dest=wrap(source+delta);
 CopyScope observed(source,dest,depth+1);
 if(nextWorld[dest]!=0 && nextWorld[dest]!=value) {
  std::string local_rule=collision_rule;
  if(collision_rule=="AB_halves") local_rule=dest<worldSize/2?"A":"B";
  if(collision_rule=="AB_quarters") local_rule=(dest/(worldSize/4))%2==0?"A":"B";
  if(collision_rule=="AB_temporal") local_rule=current_step%2==0?"A":"B";
  if(world[dest]!=0 || local_rule=="0") nextWorld[dest]=0;
  else {
   int u=ring_nearest(dest,1),v=ring_nearest(dest,-1);
   int a=world[wrap(dest+u)],b=world[wrap(dest-v)];
   int distance=u+v-(local_rule=="B"?1:0);
   observed.is_mutation=true;
   nextWorld[dest]=distance*((a>0 && b>0)||(a<0 && b<0)?1:-1);
  }
 } else nextWorld[dest]=value;
 observed.finish();
 // In the sketch helper lookup uses the OLD row, and offsets from ORIGINAL
 // source. Equal-valued helpers also recurse. MAX_REPRODUCTIONS=2 means
 // THREE attempts (initial plus two recursive calls), including after collision.
 int helper=world[wrap(source+delta)];
 if(helper!=0 && depth+1<=2) {
  HelperScope helper_scope(dest); galloway_shift(source,helper,depth+1);
 }
}
void update_galloway() {
 for(int i=0;i<worldSize;++i) if(world[i]!=0) galloway_shift(i,world[i],0);
 flipWorlds();
}
int main(int argc,char**argv) {
 // profile norm steps initial-file trajectory-file statistics-file trace-file trace-steps
 if(argc!=9) { std::cerr<<"adapter requires 8 arguments\n"; return 2; }
 try {
  std::string profile=argv[1],rule=argv[2]; int steps=std::stoi(argv[3]);
  std::ifstream in(argv[4]); if(!in) throw std::runtime_error("initial file missing");
  std::string line,token; std::getline(in,line); std::stringstream row(line);
  world.clear(); while(std::getline(row,token,',')) world.push_back(token=="x"?X_MARK:std::stoi(token));
  worldSize=world.size(); if(worldSize<1 || steps<0) throw std::runtime_error("invalid dimensions");
  nextWorld.assign(worldSize,0); target_writers.assign(worldSize,-1);
  bool galloway=profile=="galloway_published" || (profile=="research" && rule.rfind("galloway_",0)==0);
  use_world_depth_cap=!galloway;
  if(profile=="galloway_published" && (worldSize!=511 || rule!="galloway_B")) throw std::runtime_error("published profile requires width511 and effective B norm");
  if(profile!="barricelli1954_reference" && profile!="research" && profile!="galloway_published") throw std::runtime_error("unknown profile");
  if(rule=="basic") norm=Norm::BASIC; else if(rule=="symbiotic") norm=Norm::SYMBIOTIC;
  else if(rule=="exclusion") norm=Norm::EXCLUSION; else if(rule=="conditional") norm=Norm::CONDITIONAL;
  else if(galloway && (rule=="galloway_B" || rule=="galloway_A" || rule=="galloway_0" || rule=="galloway_AB_halves" || rule=="galloway_AB_quarters" || rule=="galloway_AB_temporal")) collision_rule=rule.substr(9);
  else throw std::runtime_error("unknown norm");
  if(rule=="galloway_AB_quarters" && (worldSize<4 || worldSize%4)) throw std::runtime_error("quarter environment requires width divisible by four");
  if(rule=="galloway_AB_halves" && worldSize%2) throw std::runtime_error("matched half environment requires even width");
  if(galloway && std::find(world.begin(),world.end(),X_MARK)!=world.end()) throw std::runtime_error("99999 reserved for exclusion marker");
  trace_steps=std::stoi(argv[8]);
  if(trace_steps>0) { event_stream.open(argv[7]); event_stream<<"time,source,target,depth,value,before,after,outcome,previous_writer,helpers\n"; }
  std::ofstream trajectory(argv[5]); if(!trajectory) throw std::runtime_error("output missing");
  auto emit=[&]() { for(int j=0;j<worldSize;++j) { if(j) trajectory<<','; trajectory<<world[j]; } trajectory<<'\n'; };
  auto start=std::chrono::steady_clock::now(); emit();
  for(current_step=0;current_step<steps;++current_step) {
   std::fill(target_writers.begin(),target_writers.end(),-1);
   if(galloway) update_galloway(); else updateWorld(); emit();
  }
  double seconds=std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();
  struct rusage usage; getrusage(RUSAGE_SELF,&usage);
  std::ofstream stats(argv[6]);
  stats<<"{\n\"engine_seconds\":"<<seconds<<",\"max_rss_kib\":"<<usage.ru_maxrss
       <<",\"attempted_copies\":"<<attempt_count<<",\"accepted_outcomes\":"<<accepted_count
       <<",\"collisions\":"<<collision_count<<",\"newly_produced_values\":"<<produced_count
       <<",\"erasures\":"<<erasure_count<<",\"fresh_writes\":"<<fresh_count
       <<",\"same_value_outcomes\":"<<same_count<<",\"out_of_bounds\":"<<out_count
       <<",\"depth_cap\":"<<cap_count<<"}\n";
  return 0;
 } catch(const std::exception& e) { std::cerr<<e.what()<<'\n'; return 2; }
}
