# Ad & Funnel Playbook — Instagram → Skool

The complete process for getting a stranger from an Instagram ad (or organic post) to a paid Skool member, in a way that doesn't get the ad account or the Instagram profile banned.

---

## The core rule that governs everything below

Meta doesn't review what's *inside* your Skool community. It reviews the **ad creative** and, to a lesser extent, the **landing page the ad links to**. So the entire compliance strategy is:

> Keep the ad + landing page framed as generic "creator economy / digital agency business coaching." Never say OnlyFans, never show adult-adjacent imagery, never use words like "OFM" in ad copy. The specific niche (subscription-platform creator management) only shows up once someone is already inside the paid Skool community.

This isn't a loophole to hide something illegal — the business itself is legal (Module 1 covers this). It's the same reason a course teaching "high-ticket sales" doesn't name the specific product being sold in the ad copy. You're advertising a business-skills product; the ad should read like one.

Three risk tiers, pick where you start:

| Tier | What it is | Meta ad-review risk |
|---|---|---|
| **Safest** | Organic content + Linktree/bio link only, no paid ads | None — no ad review happens |
| **Moderate** | Paid Meta ads, fully generic framing (below) | Some rejection/review friction, manageable |
| **High risk — avoid** | Paid ads mentioning OnlyFans/OFM directly, or linking straight to anything adult-adjacent | Ad account + Business Manager ban, can cascade to the organic profile |

Start at "Safest" for the first 2-4 weeks (matches `launch-plan-30-day.md`), then layer in "Moderate" paid ads once organic proves the offer converts.

---

## Part 1 — Skool setup (the destination)

1. Create the Skool community (see `skool-setup-guide.md` for full detail). Name it **Krown Management** — a business/education name, nothing adult-adjacent.
2. Connect Stripe under Skool's payment settings — this is what actually processes the $97 charge.
3. Set the community to **Paid**, **one-time payment**, $97.
4. Build the 8 course modules from `course-content.md`.
5. Publish `terms-of-service.html` and `privacy-policy.html` (once you've filled in the placeholders) somewhere linkable — either host them via GitHub Pages (see below) or paste the text into Skool's own about/terms section.
6. Test the full checkout yourself with a real card before sending any traffic to it.

**Your Skool community URL** (e.g. `skool.com/krown-management`) is the final destination every link in this playbook points to.

---

## Part 2 — The "ad-safe" landing page

Don't send ad traffic straight to `sales-page.html` as it currently reads — it's accurate and fine for organic/bio traffic, but for **paid ads specifically**, Meta's reviewers (and later, automated re-scans) do check the destination URL's content. Build a second, deliberately generic version:

- Headline: something like *"The Digital Agency Blueprint — Learn to Manage Online Creators & Talent"* rather than anything OFM-specific.
- Body copy: talks about "managing online creator accounts," "growth marketing," "client management" — all true, just framed at the general "creator economy" level rather than naming the platform.
- No screenshots of OnlyFans dashboards, no adult-adjacent imagery.
- Same $97 price, same "Join on Skool" button.
- This page still funnels to the exact same Skool checkout — it's just the front door that ad traffic sees before deciding to click through.

This already exists as `sales-page-ads.html` — use its URL as the destination for any paid Meta ad. Keep `sales-page.html` (which does mention the OFM niche) for organic/bio traffic only, never as an ad destination.

---

## Part 3 — Meta Ads Manager setup (once you're ready for paid)

1. **Business Manager**: create one at business.facebook.com under the Krown Management name, with a real business email (not a personal Gmail).
2. **Facebook Page**: required to run Instagram ads — create a Krown Management Page even if you mainly post on Instagram; link the Instagram account to it.
3. **Ad account**: add a payment method (card). Start with a *separate* ad account if possible rather than one tied to years of unrelated personal activity — cleaner signal for reviewers.
4. **Domain verification** (optional but recommended): verify the domain your landing page lives on inside Business Manager — adds legitimacy signal.
5. **Pixel**: install the Meta Pixel on the ad-safe landing page (not required to start, but needed later for retargeting/lookalike audiences).

## Part 4 — Campaign structure

- **Objective**: "Leads" or "Sales/Conversions" (Conversions once the pixel has enough data; Leads or Traffic to start).
- **Targeting**: interest-based — entrepreneurship, digital marketing, "start a business," side hustle content — broad business-audience targeting, not OF-related interests (which barely exist as ad targeting options anyway and would be a red flag if they did).
- **Creative**: talking-head video of your mate (from the promo playbook) reframed with generic hooks — "How I built a 6-figure creator management agency," no mention of the platform.
- **Budget**: start small ($10-20/day) to keep review low-friction; scaling too fast on a new ad account increases scrutiny.
- **CTA button**: "Learn More" or "Sign Up" → the ad-safe landing page → Skool checkout.

## Part 5 — Risk mitigation while running paid ads

- Keep the **organic Instagram profile's own content** compliant too (per `instagram-promo-playbook.md`'s "don't post" list) — Meta's reviewers sometimes check the Page/profile behind an ad, not just the ad itself.
- Expect some ad rejections even when compliant — resubmit with copy tweaks rather than assuming a ban.
- Never link an ad directly to an OnlyFans profile, and never mention subscriber/creator platforms by name in ad copy or the ad-safe landing page.
- If an ad account does get disabled, don't immediately create a new one on the same login — read Meta's specific rejection reason first, fix it, and appeal; repeated fresh accounts is its own red flag.
- Keep paid ads and organic content as two separate, redundant channels — if paid ever gets shut down, organic + Linktree keeps the business running.

---

## The full funnel, end to end

```
Instagram ad (generic "digital agency" framing)  ──┐
                                                      ├──► ad-safe landing page ──► Skool checkout ($97) ──► course + community access
Instagram organic post/Reel → bio link (Linktree) ──┘
```

Both paths land in the same place. Paid ads are an accelerant once the organic version is proven to convert — they're not a replacement for it.
