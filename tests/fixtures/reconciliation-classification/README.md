# Frozen classification regression evidence

These public CQC location classification caches were copied from repository
commit `a0d5b5df564a1d553cc7a9effcca91483a91ab0a`. The regression reclassifies
their registration and deregistration dates against the explicit historical
16 September 2026 publication date. Its asserted 127/61 entries and resulting
classification split describe that fixture, not today's live source.

Operational nightly caches change as real source records change. Keeping this
regression fixture separate prevents a later real collection from rewriting
the test's reference population. The test still checks the complete historical
split, including the 40 formerly misclassified registration dates.

Contains public sector information licensed under the Open Government Licence
v3.0; CQC source information: https://www.cqc.org.uk/about-us/transparency/using-cqc-data.
