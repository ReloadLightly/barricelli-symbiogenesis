// SPDX-License-Identifier: GPL-3.0-only
// Uninstrumented harness for Tim Taylor's retained, unchanged GPLv3 source.
// The only historical path calls its original updateWorld() functions.
// "helpers_disabled" is an explicitly imposed counterfactual rule, not a
// historical profile. There are no hooks or links to the laboratory adapter.
#define main upstream_figure_main
#include "upstream/barricelli54.cpp"
#undef main
#include <fstream>
#include <sstream>
#include <stdexcept>

int main(int argc, char** argv) {
    try {
        if (argc != 5) throw std::runtime_error("usage: oracle historical|helpers_disabled steps initial.csv output.csv");
        std::string mode = argv[1];
        if (mode != "historical" && mode != "helpers_disabled") throw std::runtime_error("unknown mode");
        int steps = std::stoi(argv[2]);
        if (steps < 0) throw std::runtime_error("negative horizon");
        std::ifstream input(argv[3]);
        std::string line, field;
        if (!input || !std::getline(input, line)) throw std::runtime_error("missing initial row");
        std::stringstream row(line);
        world.clear();
        while (std::getline(row, field, ',')) world.push_back(std::stoi(field));
        if (world.empty()) throw std::runtime_error("empty world");
        worldSize = static_cast<int>(world.size());
        nextWorld.assign(worldSize, 0);
        norm = Norm::SYMBIOTIC;
        std::ofstream output(argv[4]);
        if (!output) throw std::runtime_error("cannot open output");
        for (int t = 0; t <= steps; ++t) {
            for (int x = 0; x < worldSize; ++x) output << (x ? "," : "") << world[x];
            output << '\n';
            if (t == steps) break;
            if (mode == "historical") updateWorld();
            else {
                // Counterfactual: retain each source's direct first attempt,
                // suppress only old-row helper recursion. Ascending writes.
                for (int x = 0; x < worldSize; ++x) {
                    int target = x + world[x];
                    if (world[x] && target >= 0 && target < worldSize) nextWorld[target] = world[x];
                }
                flipWorlds();
            }
        }
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
