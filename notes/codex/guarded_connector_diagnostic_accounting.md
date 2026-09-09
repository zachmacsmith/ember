# Guarded-connector diagnostic accounting (before code or outcomes)

The query uses the parent-supplied absolute deadline: start immediately before
launching each cold isolated worker, deadline=start+5s. The existing local
supervisor/watchdog supplies the separate20s process limit. Final credit requires
the complete result/hash receipt and actual process return before the query
deadline. Setup/imports, helper loading, JSON, hashing, certificates and
publication are therefore inside wall time. The parent does not renew time.

The2M allowance counts explicit scalar/item/adjacency visits plus conservative
reservations for unchanged helper bodies and bulk byte operations. These are
charged units, not measured Python instructions or ordinary routing pops.
Every explicit graph/set/heap visit is charged; a tuple/set of at most three
sites reserves its size before copying, sorting or hashing. Scanning/encoding
input and output bytes reserves one unit per4096-byte block. JSON structure
visits and graph-record item visits are charged separately. No work is hidden
in an unbounded proposal pool.

Reused `adjacency` conversion reserves16*(nodes+edges) units before each call.
The unchanged A062 journal checker reserves
`64*(source_nodes+source_edges+(journal_rows+1)*(1+ceil(log2(source_nodes+1))))`
for reduction/order/R/receipt work. Its calls to the unchanged embedding oracle
reserve separately
`8*target_edges + 16*(placed_nodes+source_edges+occupied_sites+occupied_adj_entries)+64`.
The latter sizes are obtained by charged visits. These deliberately conservative
item envelopes cover the helpers' collection traversals; they are not wall-time
guarantees or exact operation counts. Every call records reserved units and
whether it returned; clocks are checked before/after it. Interrupted helper work
stays conservatively charged, without claiming its reserved items all executed.
A reservation that exceeds remaining allowance is refused before the helper,
records needed/remaining units and stops as unknown; it does not fabricate work.

The R reconstruction, pending-demand boundaries, protected-site components,
size1–3 enumeration, full frontier guards and result preparation use explicit
metered loops. The search never runs a constructor or production proposal.
The first fully certified witness may establish existence without completing
the remaining enumeration. A negative size≤3 result requires complete enumeration;
an any-size fixed-owner obstruction requires a complete empty-boundary or
protected-component certificate. Any interruption before the relevant certificate
and timely publication is unknown. No process or allowance retry follows.
