# Wedge matrix

Practice → Wedges → Wedge matrix. Choose a bag and wedges (custom names/lofts are allowed),
1–8 distinct swing labels, a sample goal and carry/total. Launch real collection or a labeled demo.
Tap a matrix cell to select its wedge and swing together, or use the direct club and swing controls.
The current swing is shown above the latest shot. Worker receipts freeze swing context at capture;
missing historical context remains unavailable. Shot feedback, table and CSV retain the recorded label.

Each planned cell shows median/IQR distance, available count, median launch and spin. Counts exclude
removed/excluded shots and missing distance. Type-7 quartiles match the bag map. Only cells reaching
the configured sample goal enter target-distance suggestions; suggestions rank absolute median error
and show variability, without interpolation or assuming a label implies a fixed travel percentage.
All included planned shots enter the matrix, independent of the range workspace filters. Corrections
and Undo update equipment grouping; swing labels are frozen, with historical swing correction a future
cleanup enhancement. Use CSV for matrix summaries and Print reference for a compact paper view.

Finish/abandon, saved review, recoverable deletion and capture ownership reuse the range lifecycle.
Collection plans, labels and shots persist in existing SQLite JSON; attempt and range CSV include
swing_label. Demo generation changes speeds by label order solely to exercise the test harness;
it is not a distance prediction for your swing. Cross-session matrix comparison follows in Analyze.

Verification: three collection API tests, three collection Node checks and the complete 146 Python
regression suite passed. Isolated browser tested custom labels/two wedges, cell selection, collection,
nearest sampled suggestion and phone layout. Physical iPad, real distance accuracy and print dialog
output remain unverified; source/session data was not modified.
