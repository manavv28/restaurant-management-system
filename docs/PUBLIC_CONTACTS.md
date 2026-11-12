# Public business-contact enrichment

The initial audit found 8,700 of 10,404 listings with contact numbers and 1,704 without. Of those gaps, 226 already had reviewed IndiaRestros identity matches. The documented commercial-use public API was checked for those records; no private provider-account contacts or addresses were accessed.

The collector uses four bounded readers with one shared request rate below 86/minute, honors HTTP 429 and checkpoints minimal facts and response hashes. It does not collect photographs, descriptions, consumer accounts or marketing lists. Business contacts are used for the directory, never unsolicited messaging.

Publication requires unchanged provider identity, matching coordinates within 80 metres, source dates within 90 days and no explicit conflicting brand/area in original source links. Accept one unambiguous Indian business phone, or a uniquely corroborated number across sources. Conflicts and missing data stay unfilled. Owner-managed venues, existing contacts and fictional samples cannot be overwritten. Contact changes and provenance are recorded atomically in ingestion_logs; replay adds no duplicate contacts. Existing menus are unaffected.

A fresh review selected 47 contacts, now published in production. Contact coverage increased from 8,700 to 8,747 of 10,404 listings; 1,657 remain without a usable number. Rejected: 49 records with conflicting areas, 104 with conflicting numbers, 12 with conflicting brands and 14 without a usable number. An isolated rehearsal added exactly the 47 reviewed contacts, replayed with zero additions and preserved all 357,604 rehearsal menu rows (including one local preservation fixture). This is not independent confirmation that a number is currently correct.

The restaurant detail API shows contact source/date only while the current number matches its audit evidence. Changing a number does not leave the old evidence attached to it.

## Reproduce

Export reviewed targets with id, name, area, source_id, latitude, longitude, external_id and expected_name. Use the backend virtual environment:

```sh
PYTHONPATH=backend python scripts/catalog/collect_public_contacts.py \
 --targets reviewed-missing-contacts.json --output work/contact-collection
```

Review the report and generated SQL, rehearse publication against an isolated database, then execute bounded transactions. Keep the plan hash and publication results. A directory containing publication.json is immutable; use a new directory for a new import. Raw snapshots and phone lists remain local work artifacts; only aggregate reports belong in Git.
