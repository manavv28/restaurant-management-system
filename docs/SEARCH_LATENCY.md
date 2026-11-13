# PRD search latency correction

The first public PRD rollout passed functional checks, but five sequential warm probes recorded a median 13.5-second verdict in the managed test environment. This does not meet the PRD target and was not described as deployment-ready.

Production EXPLAIN ANALYZE separated the work:

- Dish/radius lookup: approximately 437 ms execution (232 ms planning in that diagnostic).
- Nearby unpriced venues: approximately 649 ms execution.
- Full citywide coverage aggregation: approximately 9,903 ms execution. Most time was spent fetching wide menu/evidence heap rows, plus a full maximum-date scan and distinct sort.

Corrections:

1. Production verdicts never invoke the full coverage calculation. They return an existing public counter snapshot or null; live menus, evidence expiry, dietary conditions and offers still use current database rows. Coverage remains available from its separate endpoint.
2. Coverage uses an explicit, timestamped public-only snapshot cached for at most 60 seconds after computation. This is not a cache of prices, personal searches or offer eligibility. The UI shows the snapshot timestamp.
3. Partial covering indexes support counts over available menu IDs/restaurant IDs and active evidence IDs/expiry. An observed-at index supports the catalogue's latest-observation lookup. Private-table permissions and data remain unchanged.
4. Streams advertise identity encoding, no transformation and no proxy buffering. Middleware preserves these explicit stream headers. Test infrastructure that fulfills a fetched response may still buffer it; observed transport latency is not equated with backend processing time.
5. Approved research candidates are considered even when the first nearby unpriced venues have no approved source. Scheduling remains limited to three jobs and existing reviewed sources, with cooldown/backoff preserved.

Regression tests prohibit citywide calculation from the production verdict path, check timestamped counter caching, validate stream headers and exercise research with additional unsourced nearby venues. Local PostgreSQL validation passed 216 tests, including the existing payment/concurrency, security, publication and migration checks. Hosted and post-deployment evidence are required before reporting the final performance result.

The concierge stream also avoids an unrelated unpriced-directory lookup once priced matches exist; the directory remains available and the fallback still runs when no priced match exists. Search-match and run audit writes share the final commit on the priced fast path. After indexing, the same production coverage EXPLAIN measured about 2,007 ms instead of 9,903 ms; the aggregate is still kept out of verdicts.

Research status polling refreshes the verdict after each newly successful source check, even if another job is retrying. It does not wait for every source to reach a terminal state. A browser regression covers a successful publication while the overall request remains running.

## Public observations and research responsiveness

After the fast-path/index release, five sequential warm public original-brief queries returned 15 real-source matches, with verdict times 1,900 / 1,900 / 1,958 / 1,651 / 1,764 ms (median **1,900 ms**). First events were 835 / 889 / 892 / 688 / 797 ms (median **835 ms**). These are a bounded network sample, not a representative p95 or a 100-user load test, and the 600 ms first-event target was not met in this sample. A broad initial query remains more expensive than the specific dish query; do not apply the 1.9 s figure to every search or cold start.

Actual research jobs 78–80 refreshed existing public menu facts and added 230 explicit dietary labels. During publication, the API's own async background task used synchronous SQLAlchemy operations on the request loop; status and coverage proxy requests reset. The follow-up runs that entire bounded research operation in a thread with a separate event loop. A regression deliberately blocks the worker's synchronous portion and proves health still responds. The immersive map now renders while the initial search is pending, rather than disappearing behind a loading screen. This correction does not promise immediate responses when the database or Free service is otherwise overloaded.

Post-fix live release `7128e15efd4d`: a Jain Hakka-noodles request correctly returned no cached dietary match, then queued three reviewed Andheri sources. Jobs 81–83 all succeeded. Four concurrent research-status/health rounds returned HTTP 200 throughout; research polls took 811 / 1,094 / 837 / 646 ms and health probes 1,024 / 1,347 / 866 / 635 ms. The initial missing-match verdict took 7,077 ms; on-demand research does not make an absent Jain declaration true. This verifies responsiveness during these particular jobs, not continuous uptime or load capacity.
