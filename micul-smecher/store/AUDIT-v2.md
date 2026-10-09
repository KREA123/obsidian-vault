# Audit: SOUL landing v2 (2026-10-09)

Screenshots: `store/audit/v2-1440-hero.png`, `v2-1440-full.png`, `v2-390-hero.png`, `v2-390-full.png`.
Measured locally: 17,272 px tall at 1440, 18,418 px at 390. About 0.7 MB transferred, 22 requests, no horizontal scroll, no CLS. One external failure: the Google Fonts CSS. Without it the page falls back to system fonts, so the brand type disappears.

## Keep
- The giant S·O·U·L wordmark with the device as its O. This is the signature.
- Live eyes (`eyes.js`) mapped onto the black glass of every render, following the pointer or finger.
- The "birth yours" roll, with the rarity, the odds and a chip-id certificate. The odds table is computed from the engine.
- The colour carousel and the family render with five live pairs of eyes.
- Copy that lands: "your ai has a brain. give it a soul.", "it looks back.", "you pick the body. the eyes pick themselves.", "hold the glass.", "the boring bits.", "good questions."
- Honesty: concept-render tags, no pre-orders, the CE explanation, the legal footer, EN/RO with every string.

## Weak
- The hero is static after load. Scroll only nudges the letters, so there is no reveal.
- The colours are a sideways carousel of small cards, not a configurator. There is no single big object you can change.
- No section on material or form. The 31.5 mm profile, the bead-blasted aluminium and the MĂRGĂRITAR shape never get a close-up.
- The AI copy is out of date. It treats "No AI / Claude / ChatGPT / API key" as four equal cards, and never says that SOUL Memory lives on the device or that we never sell AI.
- The hold-the-glass demo is a tap on a picture. Nothing shows what you said or what it answered.
- The desk section talks about approving Claude's requests (Hardware Buddy), a claim the current product story doesn't need.
- The "EU servers" promise conflicts with on-device memory and bring-your-own-AI.
- There is no "what's in the box", and the specs are mixed in with the promises.
- The waitlist has no language choice and isn't shaped for a Shopify customer form.
- No structured data and no announcement of the pre-launch status above the fold.
- Fonts come from a third-party CDN: an extra connection, and they fail behind strict proxies.
- About 1,000 lines of JS inline and render-blocking. The eye engine (113 KB) loads synchronously.
- 18 k px on mobile is long, with some repetition between alive, hold and claude.

## Top 15 upgrades for v3
1. **Scroll-driven hero.** A sticky stage where scrolling wakes SOUL, parts the letters, lifts and turns the stone, then hands over to the headline. Static when reduced motion is on.
2. **Pre-launch bar.** "Pre-launch · not CE-certified yet · waitlist only, nothing is charged", up top and honest.
3. **"The object" section.** Side render with dimension callouts (90 × 101 × 31.5 mm, 2.8″ round glass) plus the material story.
4. **A real 5-colour configurator.** One big transparent cut-out with live eyes, a swatch radiogroup with arrow keys, instant swap via a preloaded crossfade, and a background tint per colour. The choice carries into the waitlist.
5. **A better birth ritual.** Roll a sample, *or type a chip id* to see exactly what that chip would be born as (the same `rollFromChipId` as the firmware). Shareable deep link `#born=<chip>`, rarity filters on the collection, and an honest odds table.
6. **"Your AI, embodied", rewritten exactly.** Your own Claude (account/API key + the Claude app connector), your own ChatGPT (own key now; Sign in with ChatGPT pending OpenAI approval), or offline. SOUL Memory on the device. We never sell or include AI.
7. **A scripted hold-the-glass demo.** Press and hold (or Space) to show the mic ring and a live transcript; release for thinking, then the answer. A switch picks Claude, ChatGPT or offline, and it's labelled "scripted demo".
8. **SoulOS glimpse.** Glass UI and standby as eyes on pure black, an OS screen strip, and a link to the live os.html.
9. **Privacy as a section of its own.** No camera, listens only while held, memory on the device that you can read and delete, no streaks or guilt.
10. **Specs plus "in the box"** in a clean two-column layout, with planned contents labelled as planned.
11. **Shopify-ready markup.** Every block is wrapped in `<!-- section: name -->`. The waitlist uses Shopify's `contact[email]`, `contact[tags]` and `form_type=customer` names, with a local mock success state.
12. **Self-hosted, subset woff2 brand fonts** (Bricolage Grotesque + Martian Mono, with Romanian diacritics), preloaded. No third-party requests.
13. **Performance.** LCP image preloaded with AVIF/WebP `srcset`. All JS `defer`red in external files. Eyes paused when off-screen *and* when the tab is hidden. Every image has width and height (no CLS).
14. **Accessibility.** Skip link, focus rings, a keyboard path for every toy (roll, configurator, hold, chip input), ARIA live regions, `prefers-reduced-motion`, and pinch-zoom allowed.
15. **SEO and sharing.** Meta description, OG, JSON-LD (Organization + FAQPage), all copy in EN/RO, and no fake stats, reviews or press.
