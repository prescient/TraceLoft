# Sheboygan Straits

A complete original 18-hole lakeside links course, inspired by Whistling Straits' open dunes,
pale bunker complexes and Lake Michigan shoreline. Blue tees: **7,142 yards, par 72**.
Select **Play → Sheboygan Straits → Set up round**, choose demo or live input, then Launch round.
The course includes bag/club tagging, historical dispersion, a scorecard, per-hole guides,
explicit Next hole, saved review, and Mulligan/Misread corrections through the existing Play engine.

## Sources and scope

Visual inspiration: [official Straits hole-by-hole guide](https://www.kohlerwisconsin.com/golf/whistling-straits/the-straits/the-straits-hole-by-hole).
Pars and Blue tee yardages: [official Straits scorecard](https://www.kohlerwisconsin.com/content/dam/kohler-destinations/pdf_resource/dk/golf/whistling-straits/scorecard-the-straits.pdf),
accessed 2026-10-03. Front nine 3,597; back nine 3,545. These are route yardages; direct map
measurements may be shorter on bends. This is original routing and AI-generated artwork, not a
geographic reconstruction. No official photos, logo, course rating or slope are bundled.

## Course card

| Hole | Name | Par | Blue yards | Sand areas |
|---|---|---:|---:|---:|
| 1 | Dune Departure | 4 | 405 | 21 |
| 2 | Fescue Passage | 5 | 533 | 24 |
| 3 | Gull Shelf | 3 | 180 | 11 |
| 4 | Iron Shore | 4 | 451 | 23 |
| 5 | Serpent Marsh | 5 | 563 | 21 |
| 6 | Devils Pocket | 4 | 378 | 19 |
| 7 | Wreckers Point | 3 | 205 | 13 |
| 8 | Bunker Coast | 4 | 470 | 23 |
| 9 | Homeward Hollow | 4 | 412 | 23 |
| 10 | Split Decision | 4 | 376 | 17 |
| 11 | Sand Cathedral | 5 | 563 | 25 |
| 12 | Little Cauldron | 3 | 138 | 12 |
| 13 | Lakeside Ledge | 4 | 389 | 20 |
| 14 | Blind Bargain | 4 | 360 | 16 |
| 15 | Northwind | 4 | 464 | 23 |
| 16 | Temptation Bay | 5 | 545 | 27 |
| 17 | Needle Point | 3 | 223 | 14 |
| 18 | Straits Reckoning | 4 | 487 | 22 |

There are **354 separate scoring sand areas**, including connected bunker complexes. Their
lobed shapes, staggered positions, narrow landing zones and fescue shoulders make misses more
costly than on Boulder Beach. Lake edges and two inland ponds are water hazards. The pale sand
areas use the configured sand reduction; golden fescue uses the existing nature rule.

## Geometry and game rules

Each finished aerial has traced, simplified polygons for sand, water, fairway, tee, green and
nature, plus its own uniform yard scale and tee/pin placement. Map display → Show scoring
boundaries reveals the exact game edges. The artwork is not a physical terrain model: small
textured lips/shadows and simplified polygon edges can differ slightly. Bunker depth, dunes,
wind, elevation, green slopes and intermediate ball-path collisions are not simulated.

The existing endpoint rules apply: default sand reduction 20%, rough 7%, nature 30%; adjustable
lie variation; water/OB replay with +1 penalty. Flat putting uses the selected Stimp/model.
A gimme adds one putt; Mulligan/Misread restore the latest scored shot's prior state even after
completion. Both retain an audit; misreads also exclude from analysis. See
[Boulder Beach controls](PEBBLE_BOULDER.md) for the shared round contract.

## Delivery and verification

- [x] Eighteen original aerials, Blue scorecard, valid registered surface polygons and hazard probes.
- [x] Course library/setup, compact hole guides, shared live/demo and historical review.
- [x] Complete 18-hole API round with approaches, putting, scoring, save/reload, review and restore.
- [x] Sand recovery, water penalty, mulligan/misread, hole reopening and stale/paused input checks.
- [x] Visual review of all eighteen artwork/boundary overlays.

Generation guides and the exact base prompt are in [design notes](../designs/sheboygan-straits/README.md).
Saved rounds freeze their own course package; later course versions must not rewrite their geometry.

UI journeys verified at 1366×1024, 1536×960 and 390×844 CSS viewports. Production course library
and all eighteen artwork URLs verified after restart. See [work log](../WORK_LOG.md) for test counts.
