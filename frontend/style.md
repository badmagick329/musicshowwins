# KpopWins frontend style guide

This document defines the visual and interaction direction for the public
KpopWins frontend. It applies to all pages and components built with Next.js,
Tailwind CSS, and shadcn/ui.

## Product personality

KpopWins is an energetic, fan-oriented K-pop reference site. It should feel
current, playful, vibrant, and welcoming while still making historical data easy
to trust and scan.

The visual personality is:

- energetic;
- playful;
- vibrant;
- friendly;
- lightly nostalgic;
- useful to both casual fans and dedicated fans researching an artist.

Use a restrained version of the Gen-Z anemoia aesthetic: hints of early-web,
music-magazine, sticker, ticket-stub, and fan-zine design are welcome, but the
site must not become a costume or parody of the 1990s or 2000s.

## Avoid

- Dull, dry, or overly serious database styling.
- A site that looks ten years out of date rather than intentionally nostalgic.
- Generic AI SaaS layouts, glassmorphism, or startup landing-page polish.
- Purple-to-blue gradients on a generic white background.
- Huge hero sections that push useful data below the fold.
- Rounded cards around every piece of content.
- Excessive pills, floating blobs, random emoji, or decorative clutter.
- Unmodified shadcn demo styling.
- Copyrighted artist photography, album artwork, or music-show logos.
- Using every accent and music-show color at the same time.

## Visual direction

Combine the clarity of a modern data product with the personality of a K-pop
fan publication.

Pages should use:

- bold typography;
- sharp geometry;
- warm light surfaces;
- confident blocks of color;
- visible but controlled borders;
- small editorial or nostalgic details;
- dense information presented with comfortable spacing.

Decoration should support the subject. Use abstract shapes, typographic motifs,
subtle dots or grids, ticket-like labels, and small sticker-inspired accents
instead of copyrighted imagery. Do not let nostalgia interfere with speed,
clarity, or mobile usability.

## Theme

Use a light theme only. Do not add a theme switcher or maintain a parallel dark
theme until explicitly requested.

The page should use a warm, lightly tinted background rather than pure white.
White or near-white may be used for data surfaces when contrast is needed.

## Color system

All colors must be represented by semantic CSS variables in `globals.css` and
consumed through Tailwind tokens. Do not scatter arbitrary hex values through
components.

Initial palette direction:

- page background: warm cream, approximately `#FFF8F2`;
- main surface: near-white, approximately `#FFFCF9`;
- foreground: ink black, approximately `#19171D`;
- muted foreground: warm grey, approximately `#6F6873`;
- border: dark neutral with lower-emphasis variants;
- primary brand accent: pop pink, approximately `#FF3D81`;
- secondary highlight: warm yellow, approximately `#FFD447`;
- informational accent: bright cyan, approximately `#29BBD1`;
- success: fresh green;
- warning: amber;
- danger: clear red.

The pop-pink accent is the main brand signal. Yellow and cyan are supporting
highlights, not equal competing brand colors. Large areas should remain warm and
neutral so the accents retain energy.

### Music-show identifiers

Give each show a stable interface color. These are navigation aids, not claims
about official show branding.

- Inkigayo: hot pink;
- M Countdown: electric violet;
- Music Bank: cobalt blue;
- Music Core: vivid orange;
- Show Champion: teal;
- The Show: sunflower yellow.

Use show colors for compact badges, dots, table markers, filters, and small
section accents. Always include the show name; color must never be the only way
to identify it.

## Typography

Use an expressive geometric sans-serif for display text and a highly readable
sans-serif for interface and body copy.

Preferred direction:

- headings and large rank numerals: `Space Grotesk`;
- body and interface text: `DM Sans`;
- tabular numerals for ranks, dates, and win counts.

Fonts should eventually be bundled or self-hosted rather than fetched at runtime.
Until font assets are added, use intentional local fallbacks. First-class Hangul
support is deferred; when it is introduced, add a compatible Korean family such
as Pretendard or Noto Sans KR without changing the established hierarchy.

Suggested scale:

- page title: 32–44px, 700–800 weight;
- major statistic or rank: 32–56px, 700–800 weight;
- section heading: 20–26px, 650–750 weight;
- card/list title: 16–18px, 600–700 weight;
- body: 15–16px;
- metadata: 12–14px;
- line height: approximately 1.4–1.6.

Do not use giant marketing typography. Useful content should remain visible near
the top of each page.

## Shape, borders, and depth

Default to square corners. Do not apply rounded corners globally.

Rounding is allowed only where the component benefits from it, such as:

- a compact status badge;
- an avatar or circular icon button;
- an input whose interaction is clearer with slight rounding;
- a deliberately sticker-like decorative element.

When rounding is used, keep it modest. Avoid large soft cards and oversized
pill controls.

Prefer clear borders, spacing, contrasting surfaces, and occasional small hard
shadows over diffuse floating shadows. A subtle offset shadow may be used on a
featured item or interactive control, but not on every container.

## Layout

Use a responsive centered page with a working maximum width around 1200–1280px.
Allow selected decorative backgrounds or full-width bands to extend beyond the
content column.

The persistent navigation should contain:

- Home;
- Artists;
- Songs;
- Wins;
- Shows;
- About.

Keep the header compact. It may be sticky if testing shows that it helps long
tables and lists.

The homepage should provide a balanced overview rather than one dominant hero:

- a prominent global search entry;
- recent wins;
- a preview of the artist leaderboard;
- a preview of the song leaderboard;
- clear routes into historical browsing.

Use cards only when they create meaningful grouping. Prefer section bands,
dividers, tables, and aligned lists over a dashboard made entirely of cards.

## Data density and hierarchy

Use comfortable information density: more lively and breathable than an admin
table, but more efficient than a marketing site.

Each page should make its primary question obvious:

- Home: what is happening and where can I explore?
- Artist page: who is this artist and what have they won?
- Song page: which wins belong to this song?
- Wins page: who won, where, and when?
- Leaderboard: who ranks highest and why?

Dates, win totals, and rank numbers should align consistently. Use tabular
numerals where possible.

## Leaderboards and tables

Use the shadcn table primitives as an accessible structural base, then style
them specifically for KpopWins. They must not look like untouched HTML or a
default component-library example.

Desktop leaderboard tables should provide:

- an obvious rank column;
- a strong artist or song label;
- a clearly aligned win count;
- restrained row hover feedback;
- show or year context where relevant;
- visible but light row separation.

The top three may receive stronger treatment through rank blocks, typography,
small accent fills, or restrained gold/silver/bronze cues. Do not turn them into
three unrelated oversized cards unless a particular page benefits from that
layout.

On narrow screens, convert tables into stacked records. Do not rely on
horizontal scrolling for the primary mobile experience. Preserve the same
information hierarchy and keep rank and win count immediately visible.

Charts are planned for a later phase. When added, they must use the same tokens,
show colors, typography, and restrained decoration as the rest of the site.

## Components

Build reusable patterns for:

- site header and primary navigation;
- global search;
- section heading with optional action;
- artist and song result rows;
- leaderboard table and mobile leaderboard record;
- latest-win row and mobile win record;
- music-show badge;
- rank marker;
- metric/statistic block;
- filter and year selector;
- empty, loading, error, and no-results states;
- compact buttons and form controls;
- quiet site footer.

Use shadcn primitives where they improve behavior and consistency. Adapt their
appearance to this guide instead of treating their defaults as the design.

## Motion

Use subtle transitions and small page-entrance effects.

Allowed:

- short fades with a 2–6px vertical movement;
- hover and pressed states;
- small color or border transitions;
- restrained transitions when filters or result groups change.

Typical duration should be about 120–220ms. Avoid bouncing, continuous motion,
large parallax effects, long stagger sequences, and animation required to
understand content.

Respect the user's reduced-motion preference using straightforward CSS or
framework support.

## Background and decoration

The background may include one subtle atmospheric treatment at a time:

- a faint dot or grid pattern;
- a soft warm color wash;
- a small halftone area;
- an abstract geometric accent;
- a ticket, label, or sticker-inspired detail.

Keep patterns faint behind data. High-energy decoration belongs around section
boundaries, headings, or empty space—not underneath dense text and tables.

## Imagery and intellectual property

Do not use artist photos, album covers, music-show logos, screenshots, or other
copyrighted promotional imagery unless a reliable usage policy is established.

Create identity through typography, color, layout, icons, and original abstract
decoration. Do not create fake album artwork or imagery that could be mistaken
for official material.

## Content voice

Use a friendly fan-community voice that remains clear and trustworthy.

- Prefer direct, warm language.
- Use familiar K-pop terminology where it helps.
- Avoid corporate product language and exaggerated marketing copy.
- Do not write as though the site represents artists, labels, or broadcasters.
- Keep data labels concise and unambiguous.
- Use exclamation marks sparingly rather than making every message loud.

The eventual donation link should be quiet and secondary, placed in the footer
or About page rather than competing with core content.

## Responsive behavior

Design mobile and desktop views together rather than shrinking the desktop page
afterward.

- Replace dense tables with stacked records on mobile.
- Keep search and primary navigation easy to reach.
- Avoid tiny tap targets and tightly packed inline filters.
- Preserve useful content near the top of the screen.
- Reduce decoration before reducing readability.

## Accessibility baseline

Use practical accessible defaults from the beginning:

- semantic HTML and native controls;
- readable contrast;
- visible focus states supplied by shadcn or the browser;
- text labels in addition to color and icons;
- descriptive links and buttons;
- reduced-motion support;
- sensible heading order.

Do not add a custom keyboard-navigation system or other complex accessibility
infrastructure during the initial frontend phase. Do not remove useful native
keyboard behavior from standard controls.

## Implementation requirements

- Use Next.js App Router, TypeScript, Tailwind CSS, and shadcn/ui.
- Keep visual tokens in CSS variables and expose them through Tailwind.
- Build reusable components rather than repeating long utility strings.
- Keep server and client components intentional; do not add client-side code for
  static presentation.
- Do not add a dark-mode implementation until requested.
- Do not add copyrighted remote images as placeholders.
- Keep loading, empty, error, and mobile states within the same visual system.
- Treat this guide as authoritative over generated component defaults.

## Final review checklist

Before considering a page complete, check:

- Does it feel energetic, playful, and recognizably related to K-pop?
- Does the nostalgia feel intentional and restrained rather than dated?
- Can a casual fan understand the page quickly?
- Can a dedicated fan scan ranks, dates, shows, and totals efficiently?
- Is the page free from generic SaaS and default shadcn styling?
- Are square corners the default?
- Are colors tokenized and used with hierarchy?
- Are music-show colors accompanied by text?
- Does the mobile layout become a deliberate stacked experience?
- Is decoration supporting rather than obstructing the data?
- Is all imagery safe to use?
- Are the tone and labels friendly, clear, and trustworthy?
