# Boulder Beach artwork

Eighteen original coastal aerial images were generated with the built-in image generation tool on
2026-10-03. No satellite imagery or real-course artwork was copied. Only published Blue yardages
and pars inform the course; all routing, shorelines, bunkers and other lies are original.

`courses/build_pebble_boulder.py --guides` creates fresh schematic references from the same geometry
as the playable package (Pillow is an optional design dependency). Each numbered guide was passed
to the image tool with the recorded [prompt](prompt.json). Final images are in `web/art/`.
The guide frame is 1536×768; the generated PNGs use the same 2:1 aspect ratio and map uniformly to
that reference frame. There is one continuous image per hole, without repeated material tiles.

Reviewed all eighteen generated images, sampled registered boundaries in the game and validated
safe routes, tee/green positions, hazard centers, equal world scale and image aspect ratios.
AI edge detail is decorative; Map display → Show scoring boundaries exposes the authoritative
saved polygons. Detailed terrain off uses those same polygons directly. Shore rocks, tree shadows
and whitewater do not create additional collision or penalty rules.

Version 1 geometry and artwork must stay immutable for saved rounds. Future material or layout
corrections require a new course/version identity. See [course guide](../../docs/PEBBLE_BOULDER.md).

Course renamed from Pebble Boulder to Boulder Beach on 2026-10-03. The original generation
prompt and screenshots are historical evidence and retain the name used when they were created.

The original guide registration was found to drift from finished artwork on 2026-10-03.
New rounds now use the fully retraced v2 package; the original v1 remains frozen. This supersedes
the initial sampled-boundary review above. See [all 36 reviewed holes](../course-registration/README.md).
