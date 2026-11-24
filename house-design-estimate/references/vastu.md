# Vastu rules used by the checker

Only when the user asked for Vastu (`vastu.enabled: true`).

Zones: the building is split into a 3 × 3 grid (NE, N, NW, E, centre/Brahmasthan, W, SE, S, SW), using TRUE north
(`project.north_deg` snaps to the nearest 45°). A room's zone is the zone of its centre. Results are graded
**ok** (ideal), **info** (acceptable), **warn** (avoid). Present them as advice, never as a hard fail, and always show the
trade-off (daylight, plumbing, cost) next to a Vastu suggestion. Ask the client how strictly they follow Vastu before
moving rooms for it.

| Room | Ideal | Acceptable | Avoid |
|---|---|---|---|
| Kitchen | SE | NW, E, S | NE, SW, centre, N |
| Master bedroom | SW | S, W | NE, SE, centre |
| Other bedrooms | S, W, SW, NW | N, E | NE, SE, centre |
| Puja | NE | E, N | S, SW, SE, centre; never under a stair, beside or under a toilet |
| WC / bath | NW, W (bath also E) | S, SE, N | NE, centre, SW |
| Stair | S, W, SW | NW, SE | NE, centre, N, E; turn clockwise going up |
| Living | N, E, NE | NW, W, S, centre | SW |
| Dining | W, E | N, S, centre, NW | |
| Store | SW, S, W | NW, SE | NE, centre |
| Study | W, NE, E, N | SW, S | |
| Courtyard / light well | centre | NE, N, E | SW |

Other rules checked:
- **Main door pada** (81-pada mandala, 9 per side): S face counted from the SE corner, good 3 (Vitatha) and 4
  (Grihakshat); N face from NW, good 3 Mukhya, 4 Bhallat, 5 Soma; E face from NE, good 3 Jayant, 4 Mahendra;
  W face from SW, good 3 Sugriva, 4 Pushpadanta, 5 Varuna.
- **Brahmasthan** (centre ninth) open and light: warn if a WC, bath, stair or kitchen takes > 10% of it.
- **Bed head** to the south or east (north = avoid). **Cook faces east** at the hob. **Altar** on the east or north wall
  so the devotee faces east/north.
- **Roof tanks** SW/S/W; **underground tank** N/NE; **septic** NW/W; **stacks** not in the NE; nothing wet above the puja.
- Heavier, taller mass to the SW, more openings and lower mass to the NE (manual).

Remedies when a rule cannot be met: keep the NE corner light and clutter-free, a small
water feature or planter in the NE, mirrors on north/east walls, brass pyramid or Vastu strip at a compromised
threshold, choose the next-best pada for the main door, keep toilet doors closed and lids down.
