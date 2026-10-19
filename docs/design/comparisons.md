# Comparison section

Scope: extend the existing landing with an English comparison hub and five
vendor-specific articles. Read mode, with installation as the secondary action.
Audience: people choosing an AI meeting assistant, especially those evaluating
open source, local control, multilingual meetings and usable work context.
The owner delegated criteria selection and explicitly requires open-source status.

## Direction contract

THESIS: a sourced decision aid, not a winner scoreboard. Start with the practical
trade-off, compare the same criteria, and keep detailed qualifications beside each claim.
OWN-WORLD: inherit the existing Geologica/Newsreader typography, forest-green
links, tinted paper background, hairline separators and plain rectangular CTAs.
STORY: choose the relevant competitor, read who each tool fits, inspect the
matrix, read qualifications, then choose an installation or vendor homepage.
FIRST VIEWPORT: breadcrumb, left-aligned product-pair title, short verdict,
dated publisher disclosure, two equal installation links and a matrix jump.
FORM: tightly specified comparison article inside the existing site, not a new
visual world. No concept seed or new illustration is needed for this extension.
FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance

## Content rules

- MeetScribe, Granola, Fireflies.ai, Bluedot and tl;dv each get a distinct recommendation,
  trade-off explanation, repository evidence and test scenario.
- Open source means a licence for the application, not a free plan, SDK, API or MCP.
- Distinguish audio retention, local capture, local ASR, cloud AI and offline use.
- No invented quality scores, security certifications or missing-feature claims.
- Source omissions are labelled unverified, not translated into a categorical No.
- Compare the pinned public Mac v0.1.9 / Windows v0.1.4 packages, not future code.
- Refer readers to product homepages for current pricing; do not mix annual and monthly quote amounts.
- Do not publish private meeting data or reuse competitor screenshots as ours.

## Verification

Static source coverage, generated-file consistency, direct routes, titles,
canonical URLs, sitemap, JSON-LD, accessible table labels, keyboard navigation,
desktop/mobile layout, unchanged install commands and successful Pages deployment.
Screenshots are review artifacts only and remain outside Git.

## 2026-10-19 owner refinement

All matrix cells now have an explicit mark, a text label and a short visible
qualifier. Five states: supported, unavailable, limited/conditional, not verified,
and different approach. Neutral differences and missing evidence are not losses.
Unknown source rights must never become a red cross. MeetOnTrack's beta/setup
limitations stay visible, but the product name in headings is simply MeetOnTrack.
Detailed explanations are retained inside native keyboard-accessible details.
Owner clarification: no source/deep links in published comparisons. Only official
product homepages may be linked from comparison content. Source URLs remain in
the repository evidence dataset, not HTML or JSON-LD. Pages stages only generated
comparison HTML, excluding the evidence JSON. Summaries are labelled “Details”,
not “Details & sources”. Tests enforce this policy across all comparison pages.

Official product identity icons are pinned by URL and checksum and staged into
the site artifact, not committed as binary media or fetched by visitors from
competitor servers. Our existing SVG identity is reused. Icons are decorative
beside visible product names. Marks use consistent inline SVG plus text, not color
alone. The visual system and responsive matrix remain unchanged.

Comparisons are direct-link pages: no navigation, homepage teaser, footer or
related-article links lead to them. Sitemap discovery is retained; this is not
a request to make the pages private or noindex. The hub retains a non-clickable
product directory. Regression tests enforce the absence of visible comparison links.

Verification: 72 explicit verdicts reviewed against the unchanged evidence text
by `claude-opus-5-5`; no material contradiction found. Five official logo URLs
matched identity links in vendor HTML, returned 200 and passed PNG/checksum checks.
Chrome inspection covered the wide matrix and a real 390px iframe viewport.
Native details retain visible qualifiers and keyboard-operable summaries. Status
text contrast was calculated on paper and mint: all combinations exceed 4.5:1.
The review caught stale CSS caching (fixed with a content-hash URL) and the mobile
caption's intrinsic width (explicit block width). Mechanical detector warnings
were inherited shared styles / existing italic typography, not newly added effects.

## Design-system inheritance and verification

Verified 2026-10-16 as an ordinary extension of the established site. The visual
authority is the incumbent `docs/index.html` and `docs/styles.css`; there is no
root `PRODUCT.md` or `DESIGN.md`. This handoff records the observed inheritance
in the surface brief and preserves the existing system files.

- Color roles are reused: tinted paper (`#f3f4ef`) for the page, dark ink
  (`#15221d`) for headings, forest (`#174c3e`) for links and primary actions,
  mint (`#dceae3`) for the open-source criterion, and the existing hairline
  (`#b9c7bf`) for section and row separators. Reading copy retains the existing
  muted green-gray (`#43514b`). The comparison adds no palette tokens.
- Typography retains Geologica for navigation, body copy and headings, with
  Newsreader at weight 500 for forest-colored emphasis. The italic Newsreader
  title line is established site identity. Article-specific heading sizes and
  line heights adapt that pairing to reading rather than replacing it.
- Layout retains the centered 1180px maximum container, 20px desktop side
  gutters and 12px narrow-screen gutters. The comparison intro is left aligned
  within a 900px measure; prose uses 70–75ch limits. Hairlines and whitespace
  organize the content without introducing raised comparison cards.
- Installation actions reuse the shared forest-filled, white-text buttons,
  3px corners, 14px semibold labels and 50px platform-action minimum height.
  They sit side by side on desktop and become full-width stacked actions at
  the inherited 540px breakpoint. Shared visible-focus outlines remain in use.
- The comparison matrix extends those roles into a fixed three-column desktop
  table, with a forest header, 22% criterion column, hairline rows and mint
  open-source row. At 740px and below it becomes a sequence of criterion blocks:
  each product cell repeats its visible column label, while the semantic table
  header remains available to assistive technology. Recommendation pairs,
  comparison links and criteria lists also collapse to a single column.

Evidence reviewed: the incumbent homepage and stylesheet (including the
stylesheet diff against `HEAD`), the comparison hub, and generated Granola,
Fireflies.ai, Bluedot and tl;dv articles. All five comparison routes load the
shared stylesheet and existing font pairing. Visual inspection covered the
following valid local review artifacts, which are not shipping assets:

- `/tmp/meetontrack-comparison-desktop.jpg`: desktop article introduction,
  platform actions and recommendation pair.
- `/tmp/meetontrack-comparison-matrix-desktop.jpg`: desktop matrix and sources.
- `/tmp/meetontrack-comparison-mobile.jpg`: narrow article introduction,
  navigation and stacked actions.
- `/tmp/meetontrack-comparison-matrix-mobile.jpg`: stacked criterion and product
  labels, source links and highlighted open-source block.
- `/tmp/meetontrack-comparison-method-desktop.jpg`: methodology, primary-source
  list and continuation into related comparisons.

Inherited detector warnings are reported, not repaired: the shared stylesheet
already contains the brand pulse ring, dormant marquee-animation declarations,
and legacy or overridden shadow declarations for evidence and terminal surfaces.
The comparison introduces no new animation or shadow rules. Its visible brand
pulse and italic Newsreader emphasis match the incumbent identity; these are not
new visual drift. The finish review requested one Fireflies.ai phrasing correction,
which was applied without a visual change. The reviewed extension preserves the
observed system; this documentation pass changes only this surface brief and
does not bootstrap root design artifacts or repair unrelated existing drift.
