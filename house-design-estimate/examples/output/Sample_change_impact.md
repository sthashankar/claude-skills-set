# Change impact report

## What changed
- fixtures `ff-geyser6` (ff): r: [55, 370, 16, 16] → [55, 262, 16, 16]
- fixtures `ff-shower5` (ff): r: [9, 258, 36, 36] → [21, 363, 36, 36]
- fixtures `ff-vanity3` (ff): r: [9, 363, 20, 36] → [9, 258, 20, 36]
- fixtures `tf-geyser6` (tf): r: [55, 370, 16, 16] → [55, 262, 16, 16]
- fixtures `tf-shower5` (tf): r: [9, 258, 36, 36] → [21, 363, 36, 36]
- fixtures `tf-vanity3` (tf): r: [9, 363, 20, 36] → [9, 258, 20, 36]
- stacks `S1` (*): y: 312 → 392

## New problems (fix or accept before applying)
- **warn** [mep] wc gf-wc4: 2.7 m pipe run to S1, needs 175 mm under the floor _(AS/NZS 3500.2)_
- **warn** [mep] basin gf-basin5: 4.5 m pipe run to S1, needs 191 mm under the floor _(AS/NZS 3500.2)_

## Problems this change solves
- [clash] Door ff-D3 swings into shower ff-shower5
- [clash] Door tf-D3 swings into shower tf-shower5

## Knock-on improvements now possible (offer these to the user)
- Ground floor: move basin gf-basin5 in Common toilet to x 3'-0", y 25'-2" (beside stack S1): pipe run 4.5 m → 2.9 m
- First floor: move wc ff-wc4 in Master ensuite to x 0'-9", y 28'-10½" (beside stack S1): pipe run 1.8 m → 1.2 m
- Top floor: move wc tf-wc4 in Bath 3 (ensuite) to x 0'-9", y 28'-10½" (beside stack S1): pipe run 1.8 m → 1.2 m

## Pipe runs that changed
- Ground floor: wc gf-wc4 pipe run 0.66 m → 2.69 m (to S1)
- Ground floor: basin gf-basin5 pipe run 2.43 m → 4.46 m (to S1)
- Ground floor: wm gf-wm6 pipe run 1.42 m → 0.91 m (to S1)
- Ground floor: sink gf-sink7 pipe run 2.9 m → 1.12 m (to S1)
- First floor: wc ff-wc4 pipe run 0.61 m → 1.83 m (to S1)
- First floor: shower ff-shower5 pipe run 1.22 m → 0.89 m (to S1)
- Top floor: wc tf-wc4 pipe run 0.61 m → 1.83 m (to S1)
- Top floor: shower tf-shower5 pipe run 1.22 m → 0.89 m (to S1)

## Daylight and air that changed
- none

## Things within 10 ft of the change (same floor, above and below)
- gf: room gf-living Living room
- gf: room gf-wc Common toilet
- gf: room gf-util Utility and laundry
- gf: room gf-hall Hall
- gf: fixture gf-sofa1 sofa
- gf: fixture gf-wc4 wc
- gf: fixture gf-basin5 basin
- gf: fixture gf-wm6 wm
- gf: fixture gf-sink7 sink
- gf: opening gf-D2 arch
- gf: opening gf-D3 bath
- gf: opening gf-D4 door
- gf: electrical DB Main DB, RCDs, SPD
- gf: electrical INV Hybrid inverter
- ff: room ff-master Master bedroom
- ff: room ff-ens Master ensuite
- ff: room ff-hall Hall
- ff: fixture ff-wardrobe2 wardrobe
- ff: fixture ff-vanity3 vanity
- ff: fixture ff-wc4 wc
- ff: fixture ff-shower5 shower
- ff: fixture ff-geyser6 geyser
- ff: opening ff-D2 door
- ff: opening ff-D3 bath
- ff: electrical DB First-floor DB
- tf: room tf-bed3 Bedroom 3
- tf: room tf-bath3 Bath 3 (ensuite)
- tf: room tf-hall Hall
- tf: fixture tf-wardrobe2 wardrobe
- tf: fixture tf-vanity3 vanity
- tf: fixture tf-wc4 wc
- tf: fixture tf-shower5 shower
- tf: fixture tf-geyser6 geyser
- tf: opening tf-D2 door
- tf: opening tf-D3 bath
- tf: electrical DB Top-floor DB
- gf: room gf-stair Stair
- gf: room gf-dining Dining
- gf: opening gf-D5 arch
- gf: opening gf-D6 arch
- gf: electrical BAT Battery (600 mm from DB)
- ff: room ff-stair Stair
- ff: room ff-family Family lounge
- ff: fixture ff-tv8 tv
- ff: opening ff-D4 arch
- ff: opening ff-D5 arch
- tf: room tf-stair Stair
- tf: room tf-study Study / sunroom
- tf: opening tf-D4 arch
- tf: opening tf-D5 arch
- *: column 6,251.25 within 3 ft: check beam/column penetration
- *: column 6,401.25 within 3 ft: check beam/column penetration
- rf: room rf-roofS Roof over bedroom 3
- rf: room rf-roofC Roof
- rf: room rf-stair Stair head
- rf: room rf-roofN Roof over study
- rf: opening rf-D1 ext

## Cost
```
Total ¤ 1,93,34,670 → ¤ 1,93,34,670 (+0)
```

## Re-check by eye (the script cannot see everything)
- **Plumbing**: drain runs and falls to each stack, sunken slab depth, vents, cleanouts, hot water length from geyser/solar, rainwater pipes in the same box
- **Exhaust**: duct route from each wet room / kitchen, outlet ≥ 1.5 m from openable windows and boundary, cowl above parapet
- **Electrical**: switch and socket positions after the move, bathroom zones (AS/NZS 3000), DB/riser path, light points over new furniture
- **Structure**: columns and beams under/over the change, slab openings, beam penetrations for pipes, cantilevers, soft storey
- **Light and air**: window to floor ratios, cross-ventilation path, sun and glare at the new position
- **Vastu**: zone of every room or fixture that moved, main door pada, stair turn, toilets off NE/centre, nothing over the puja
- **Furniture and use**: clear space in front of fixtures, door swings, walk paths ≥ 900 mm, bed/wardrobe/TV walls
- **Acoustics and smell**: stacks and WCs away from bedroom/living walls, lagging, pipe box access
- **Floors above and below**: what sits directly over and under the change
- **Estimate**: re-run the estimate and quote the delta