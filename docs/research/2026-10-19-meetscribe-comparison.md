# MeetScribe comparison evidence — 2026-10-19

Scope: an English article at `/compare/meetscribe/`, using the existing
12-criterion comparison system. This is a source-based product comparison, not
a hands-on evaluation of the competitor. No installer or release pin changes.

## Load-bearing findings

- [MeetScribe's own notice](https://www.meetscribeapp.com/open-source) credits
  Meeting Minutes by Zackriya Solutions. Its repository link redirects to
  [Meetily](https://github.com/Zackriya-Solutions/meetily).
- [The upstream licence](https://raw.githubusercontent.com/Zackriya-Solutions/meetily/main/LICENSE.md)
  is MIT. The upstream README distinguishes Community from a separate PRO
  codebase. Neither fact proves that the complete MeetScribe distribution has
  a public source licence. The article says unverified, not categorically absent.
- [MeetScribe's terms](https://www.meetscribeapp.com/terms) restrict reverse
  engineering and disclaim guaranteed AI accuracy. This review does not assess
  licence compliance inside the distributed application.
- [The homepage](https://www.meetscribeapp.com/) and
  [privacy policy](https://www.meetscribeapp.com/privacy) leave audio-processing
  location unclear. The article does not infer either fully offline operation
  or a proven server-side implementation from those descriptions.
- Pricing and FAQ descriptions differ. Link to the current page and ask readers
  to confirm allowances rather than publishing an apparently definitive tariff.
- Platform links, device capture, speaker detection and live features are
  attributed to the vendor, not presented as independently tested capabilities.
  Marketing accuracy scores and compliance claims are deliberately not repeated.

## Verification

- Host inspection: official homepage, notices, terms, privacy, upstream README
  and actual licence; original Meeting Minutes URL resolves to Meetily.
- Independent Claude check: `claude-opus-5-5`, web available, confirmed attribution,
  upstream/downstream distinction and inconsistencies. Its stronger inference of
  server processing was not adopted; the article preserves uncertainty. The model
  did not echo its identifier, so the audit records the explicitly requested model.
- Independent Gemini check: `gemini-3.8-flash-high`, model echo Gemini 3.8 Flash
  (High), web available. Confirmed the same load-bearing distinctions and the
  advertised-only status of capabilities. Two independent families beyond the
  GPT host completed; a redundant GPT subprocess was not used. Both verifiers'
  categorical closed-source/server-infrastructure inferences were softened to
  what the primary pages actually establish. No licence-compliance allegation.
- Mechanical check: six new source URLs returned HTTP 200 and all configured
  passage checks passed. Four existing MeetOnTrack source URLs also returned 200.
  Reproduce with `node scripts/check-comparison-sources.cjs meetscribe-product
  meetscribe-source meetscribe-terms meetscribe-privacy meetily-source meetily-license`.
- `node scripts/build-comparisons.cjs --check` and
  `node scripts/test-comparisons.cjs`: six routes, 12 criteria, citations,
  per-vendor check dates, canonical URLs, sitemap and related links.
- Chrome review: introduction and matrix inspected, criterion jump works,
  12 rendered rows, correct canonical URL, no desktop horizontal overflow.
  Existing responsive stylesheet reused without changes; no new raster assets.
- Other comparisons retain their original source-review dates. Adding one
  competitor must not falsely refresh every other vendor's evidence date.

Publication must use only comparison files, generator/tests, sitemap, discovery
links and this evidence. Do not deploy unrelated native-app candidates or modify
the published installation commands as part of this change.
