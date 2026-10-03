# Sheboygan Straits artwork

Original 18-hole lakeside links course. [Course guide](../../docs/SHEBOYGAN_STRAITS.md).
The supplied Kohler hole gallery informed open fescue dunes, clustered irregular ivory sand,
slate-blue lake water and treeless mown corridors. No source photographs were downloaded or bundled.

## Reproduction process

1. `python courses/build_sheboygan_straits.py --guides` creates the preliminary JSON and eighteen
   1536×768 schematic guides (Pillow is needed only for this design step).
2. Generate each aerial with the built-in image generation tool using its matching guide and
   [prompt.json](prompt.json). The prompt asks for fixed framing and hazard placement. Each call
   includes its hole number; dry-hole calls additionally prohibit introducing water.
3. Copy the unmodified generated PNG to `web/art/sheboygan-straits-NN-v1.png`. Final outputs are
   1774×887; the common 2:1 aspect ratio maps uniformly into the 1536×768 reference plane.
4. In a separate design environment with `opencv-python-headless` and NumPy, run
   `python courses/register_sheboygan_art.py`. It reads the finished images and writes vector
   contours, adjusted tee/pin/route registration and asset hashes into the JSON. It never edits
   raster images. Pillow/OpenCV are not application dependencies.
5. Review every image with scoring outlines. Automatic contour extraction is only a starting
   point: explicit exclusions remove reviewed rock/fescue fragments, and tee/green masks use
   locally sampled brightness. Review again after regenerating any image; do not reuse the
   current exclusions blindly. Hole 9's generated shoreline was accepted and traced as water.
6. Run geometry, full-round and UI checks; publish an immutable course version. Do not run only
   the preliminary builder and ship it: generated shapes drift, so the registration pass is required.

The sand fields range from small isolated pockets to connected scalloped complexes. Shadows and
raised lips are visual texture. Runtime scoring remains the documented flat endpoint game.
The final PNG files are in [web/art](../../web/art); all base guides are retained here.
