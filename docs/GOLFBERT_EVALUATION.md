# Golfbert course-data candidate

Reviewed 2026-10-02. **Research only: no integration, account, subscription or provider selection.**
Keep the existing course importer; consider Golfbert as an optional source alongside OpenStreetMap.

## Why it looks useful

Golfbert documents course search, hole listings, tee boxes, scorecards and per-hole surface polygons.
Polygon examples include labeled surfaces and latitude/longitude vertices, which could supply the
fairway, green and hazard geometry that is often missing from OSM. Its official FAQ claims over
12,500 US courses; coverage and freshness for a particular course still need checking. We have not
called the authenticated API or independently verified its geometry.

An adapter could follow our existing workflow: search course → select hole/tee → retrieve geometry
and metadata → project into local yards → review/edit → publish a versioned course. Preserve source
IDs, coordinate transforms and attribution. Structural checks do not establish geographic accuracy.

This is primarily a geometry source. Satellite imagery, elevation, current pin positions and rights
to create AI artwork need separate verification; the FAQ's suggestion to use a satellite map layer
does not establish that imagery is included or licensed for redistribution.

## Pricing snapshot

These are the advertised plans observed on the review date, not a purchase recommendation.

| Plan | Advertised price | Included access |
| --- | --- | --- |
| Sample Course | Free | Riverbend Golf Complex, course ID 4803; 1,000 calls/week |
| Single Golf Course | $9/month | One course; 10,000 calls/month |
| All Golf Courses | $399/month | Catalog access; 100,000 calls/month |
| Static Data Purchase | $120,000 one-time | Full snapshot; custom datasets/pricing also offered |

The paid API plans advertise $0.005 per extra call. Recheck pricing, quotas and the applicable
contract before subscribing. A static purchase does not by itself establish open redistribution rights.

## Licensing questions to resolve first

The published license, last modified 2/5/2026, needs clarification for TraceLoft's intended use:

- Sections 2.4–2.5 describe internal-business use and restrict third-party access/distribution,
  while section 2.7 also discusses applications used by others. Get written confirmation that a
  distributed, open-source application is permitted, including any user-supplied-key arrangement.
- Section 2.5 limits offline downloading to reasonable mobile use for one or two courses and
  prohibits bulk downloading. Confirm local PC/iPad caching and how many courses can be retained.
- Section 4.4 requires stopping use/storage and expunging licensed materials after termination.
  TraceLoft currently freezes course geometry into round history: clarify historical replay,
  database backups and derived geometry retention before adopting this source.
- Section 4.1 describes a one-year initial term and annual renewal with 60 days' notice. Confirm
  cancellation terms rather than assuming the monthly price means cancel-anytime access.
- Confirm whether licensed geometry can be sent to an AI provider and used for derived course art,
  and whether that artwork may be distributed. Keep imagery rights separate.

Until resolved, do not bundle licensed course data in the public repository or distribute it with
TraceLoft. An optional adapter with credentials kept on the local Python service is a possible design,
but bringing your own key does not automatically resolve license restrictions.

## Possible evaluation after terms are accepted

1. Use the free Riverbend sample to inspect actual payloads, surface coverage, tees and scorecards.
2. Convert one hole through an isolated adapter and the existing review workbench.
3. Check coordinate alignment, yardages, surface labels and missing rule boundaries independently.
4. Establish permitted cache, backup, historical-round and distribution behavior before integration.

No subscription or authenticated API evaluation is authorized by recording these notes.

## Sources

- [Plans and pricing](https://golfbert.com/api/plans)
- [API overview](https://golfbert.com/api/overview)
- [Official API client endpoint documentation](https://github.com/golfbert/gf-api-java-client/blob/master/docs/GolfbertApi.md)
- [FAQ and coverage claims](https://golfbert.com/api/faq)
- [Content and API license](https://golfbert.com/api/license)

Some direct page fetches returned 404 during research; the plans, FAQ and license were readable
through the site's browser navigation. Pricing and coverage above are provider claims observed then.
