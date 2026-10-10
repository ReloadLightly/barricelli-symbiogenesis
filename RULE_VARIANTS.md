# Inspectable discovery profiles

R8 uses the existing independently implemented numerical engine, with W192 and ascending iteration. These are named research profiles; the fixed `barricelli1954_reference` figures and W511 `galloway_published` remain separate. No historical software is relabelled as a new discovery.

| R8 profile | Boundary | Inspectable difference |
| --- | --- | --- |
| `r8_galloway_B` | ring | Published-style B collision arithmetic in a smaller designed world. |
| `r8_galloway_A` | ring | At an initially empty collision destination, nearest occupied distances sum without B's subtraction of one. |
| `r8_galloway_0` | ring | Every unequal-value collision erases its destination. |
| `r8_galloway_AB_halves` | ring | Destination in left half uses A; right half uses B. |
| `r8_galloway_AB_quarters` | ring | Four equal destination regions alternate A/B/A/B. |
| `r8_galloway_AB_temporal` | ring | Updates alternate A/B, starting with A. Environment phase enters recurrence checks. |
| `r8_conditional` | open | Unchanged Taylor conditional arithmetic with new sampled initial rows and dimensions. |
| `r8_exclusion` | open | Unchanged Taylor exclusion arithmetic with new sampled initial rows and dimensions. |

For the Galloway family, writes use the next row while helper lookups and nearest occupied searches use the old row. Opposite-value collisions at a destination occupied in the old row erase; otherwise A/B use a signed sum of nearest distances, determined by neighboring signs. There are at most three attempts per source, including helper recursion after collision. A heterogeneous region is an externally imposed environment, not an organism property. The exact code is [adapter.cpp](engine/adapter.cpp); Taylor arithmetic remains in [the attributed GPL source](engine/upstream/barricelli54.cpp). Source/oracle verification and limitations are in [PROVENANCE.md](PROVENANCE.md).

The starting alphabet, density and mask are design parameters. `iid` samples independently. `block8_jitter` repeats a sampled eight-cell block, replaces5% of positions with fresh samples, then applies the density mask. Spatial masks are the full world, central half, two quarter-width patches, or alternating eight-cell bands. This deliberately tests sensitivity to imposed initial organization. Exact integer starting rows and PCG64 seeds are retained. Neither the rule profiles nor the starting block imply evolved heredity.

Discovery uses one fixed cell palette and exact unsmoothed pixels. Artistic selection happens afterward; it cannot change archive measurements. Reproduction is a separate ancestry/recovery question, never inferred from matching colors or repeated domains.
