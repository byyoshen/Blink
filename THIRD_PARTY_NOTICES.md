# Third-Party Notices

## Scope

The public Blink repository distributes generated Rule-Sets, Profiles, a provenance
manifest and user-facing documentation. The build engine, portal source and audit
records are maintained privately. Earlier public Git history remains available.

This notice records upstream provenance and applicable licenses. Blink does not
relicense upstream material or override its copyright, attribution or source
availability obligations. Rule files retain the applicable upstream terms below.
Yoshen's separately licensable original rules and original portions of Profiles
are offered under CC BY-NC-SA 4.0. Original explanatory text is all rights reserved,
subject to existing grants and applicable law. The public repository LICENSE
explains these boundaries. Previously MIT-licensed material remains available
under MIT; the previous MIT grant did not cover every generated file.

## Generated Rule-Set provenance

The `Surge/<App>.list` table below is the canonical provenance record.
`Loon/<App>.list`, `Shadowrocket/<App>.list`, and `Stash/<App>.list` are
byte-identical copies of the Surge output; `mihomo/<App>.list` is the same
classical output with `USER-AGENT` lines removed (the Clash family has no
such rule type; the builder drops and counts them explicitly);
`Egern/<App>.yaml` and `QuantumultX/<App>.list` are rendered from the same
canonical rule set; `SingBox/<App>.json` is rendered from those same rules;
all of them inherit the provenance and license
attribution of the corresponding `Surge/<App>.list` row without any
additional upstream source. The semantic view files
(`<App>-domainset.conf` / `<App>-nonip.conf` / `<App>-ip.conf`) are likewise
derived from the same canonical rules and inherit the same attribution; sing-box
semantic views use the `.json` extension.

The candidate configs under `Profiles/` reference the same upstream rule
URLs (no rule content is copied), and their General/DNS skeletons follow
the layout of the [Repcz/Tool](https://github.com/Repcz/Tool) client
templates (MIT License); policy-group semantics originate from the
repository owner's own configuration. Beyond the per-App URLs, `Profiles/`
also references shared infrastructure Rule-Sets hosted by
`ruleset.skk.moe` (SukkaW's ruleset service, AGPL-3.0),
Repcz/Tool Quantumult X Rule-Sets (MIT), and ConnersHua/RuleGo
(license as declared in that repository). All of these remain remote
references — no rule content is copied into `Profiles/`.

| Generated file | Upstream project | Upstream URL | Known license or project notice |
| --- | --- | --- | --- |
| `Surge/OKX.list` | v2fly/domain-list-community | https://github.com/v2fly/domain-list-community | MIT License |
| `Surge/WhatsApp.list` | v2fly/domain-list-community | https://github.com/v2fly/domain-list-community | MIT License |
| `Surge/LINE.list` | v2fly/domain-list-community | https://github.com/v2fly/domain-list-community | MIT License |
| `Surge/GitHub.list` | v2fly/domain-list-community + Blink repo-maintained supplement (GitHub Packages hosts from `api.github.com/meta`) | https://github.com/v2fly/domain-list-community | MIT License |
| `Surge/SafePal.list` | v2fly/domain-list-community | https://github.com/v2fly/domain-list-community | MIT License |
| `Surge/Threads.list` | v2fly/domain-list-community | https://github.com/v2fly/domain-list-community | MIT License |
| `Surge/AWSConsole.list` | v2fly/domain-list-community (`data/aws`; `aws-cn` include denied) | https://github.com/v2fly/domain-list-community | MIT License |
| `Surge/DouYin.list` | v2fly/domain-list-community (`data/douyin`) + Blink repo-maintained supplement | https://github.com/v2fly/domain-list-community | MIT License |
| `Surge/PayPal.list` | Repcz/Tool | https://github.com/Repcz/Tool | MIT License |
| `Surge/YouTube.list` | Repcz/Tool | https://github.com/Repcz/Tool | MIT License |
| `Surge/X.list` | Repcz/Tool | https://github.com/Repcz/Tool | MIT License |
| `Surge/Instagram.list` | Repcz/Tool | https://github.com/Repcz/Tool | MIT License |
| `Surge/Telegram.list` | SukkaW/Surge (non-IP rules) + SukkaW ruleset service `List/ip/telegram.conf` (IP segment) | https://github.com/SukkaW/Surge | AGPL-3.0 for these rule sources; see upstream README for exceptions |
| `Surge/Netflix.list` | Repcz/Tool (`us-west-2.amazonaws.com` excluded) | https://github.com/Repcz/Tool | MIT License |
| `Surge/TikTok.list` | Repcz/Tool | https://github.com/Repcz/Tool | MIT License |
| `Surge/Spotify.list` | Repcz/Tool | https://github.com/Repcz/Tool | MIT License |
| `Surge/AI.list` | Repcz/Tool | https://github.com/Repcz/Tool | MIT License |
| `Surge/Steam.list` | Repcz/Tool | https://github.com/Repcz/Tool | MIT License |
| `Surge/ZABank.list` | Blink repo-maintained supplement | `engine/sources/supplement/ZABank.list` | No upstream source; original repo-maintained rules |
| `Surge/APTV.list` | Blink repo-maintained supplement (personal list) | `engine/sources/supplement/APTV.list` | Rules maintained by the repository owner (originally kept in a private list); no third-party license |
| `Surge/Disney.list` | Repcz/Tool | https://github.com/Repcz/Tool | MIT License |
| `Surge/PrimeVideo.list` | Repcz/Tool | https://github.com/Repcz/Tool | MIT License |
| `Surge/HBO.list` | Repcz/Tool | https://github.com/Repcz/Tool | MIT License |
| `Surge/Facebook.list` | Repcz/Tool | https://github.com/Repcz/Tool | MIT License |
| `Surge/Google.list` | Repcz/Tool | https://github.com/Repcz/Tool | MIT License |
| `Surge/ParamountPlus.list` | blackmatrix7/ios_rule_script | https://github.com/blackmatrix7/ios_rule_script | GPL-2.0 |
| `Surge/Hulu.list` | blackmatrix7/ios_rule_script | https://github.com/blackmatrix7/ios_rule_script | GPL-2.0 |
| `Surge/Twitch.list` | blackmatrix7/ios_rule_script | https://github.com/blackmatrix7/ios_rule_script | GPL-2.0 |
| `Surge/NBA.list` | Blink repo-maintained supplement | `engine/sources/supplement/NBA.list` | No upstream source; original repo-maintained rules |
| `Surge/Suno.list` | Blink repo-maintained supplement | `engine/sources/supplement/Suno.list` | No upstream source; original repo-maintained rules |
| `Surge/Starryblu.list` | Blink repo-maintained supplement | `engine/sources/supplement/Starryblu.list` | No upstream source; original repo-maintained rules |

The exact upstream URLs and content fingerprints are published in `manifest.json`.
Source definitions and selection rationale are maintained in the private engine.
Paths beginning with `engine/` in this notice or manifest describe private records,
not downloadable files in the current public tree. Upstream projects may change their
licenses, notices, source content, or repository structure; source audits and
this notice must be reviewed whenever a source is added or replaced.

## Portal assets (maintained in the private engine)

| Asset | Origin | Notice |
| --- | --- | --- |
| `engine/portal/src/components/Brand.tsx` (inline rock-creature `Mark` SVG) | Repository owner (original brand mark) | The Blink mark: the owner's rock creature (angular body, three legs, one slanted eye cutout), drawn as a single-colour SVG that follows the text colour, so it renders black on the light theme and reversed white on the dark theme; an optically simplified variant is used at 16 px and below. Used in the top bar, the first-visit client picker, the footer, the boarding-pass ticket and next to the "Blink" wordmark. Owned by the repository owner; not covered by any third-party license. |
| `engine/portal/public/favicon.ico`, `favicon-dark.png`, `favicon-light.png`, `apple-touch-icon.png`, `apple-touch-icon-v2.png`, `icon-192.png`, `icon-512.png` | Repository owner (original brand mark) | Browser-tab, home-screen and web-app icon exports of the rock-creature mark (the simplified variant on the favicons). Since 2026-10-08 the home-screen and web-app icons (`apple-touch-icon.png`, `apple-touch-icon-v2.png`, `icon-192.png`, `icon-512.png`) are a near-black creature on a white tile. Owned by the repository owner; not covered by any third-party license. |
| `engine/portal/public/og-image.jpg` | Repository owner (original brand mark and illustration) | Link-preview card (1200×630, dark ground) showing the rock-creature lockup, the tagline and the portal's outpost watercolour. Owned by the repository owner; not covered by any third-party license. |
| `engine/portal/public/art/*.webp` | Original work made for Blink | Five watercolour scenes of the rock creature (the outpost, listening for signals, the routes, fellow explorers' star charts, the dawn departure), each in a light and a dark version, painted procedurally for this portal by an offline script written for Blink (pigment layering, deckled edges, granulation, wet-in-wet blooms, line and wash). Stills are flattened onto the page colour; the departure scene also ships as aligned transparent layers. Since 2026-10-08 they appear only in the optional intro film, opened from the end of the Sources page and loaded on demand. Owned by the repository owner; not covered by any third-party license. |
| `engine/docs/images/avatar.png` | Repository owner (original brand mark) | Rounded-square export of the rock-creature mark (white on black), kept as a title mark for documentation. Owned by the repository owner; not covered by any third-party license. |
| `engine/portal/public/icons/*.jpg` | Apple App Store artwork (iTunes Search API) | Official app icons of Surge, Shadowrocket, Loon, Stash, Egern, and Quantumult X, downloaded from the App Store and used only to identify each supported client in the portal. Trademarks and icons belong to their respective owners; not covered by this repository's terms. |
| `engine/portal/public/icons/mihomo.jpg` | https://github.com/clash-verge-rev/clash-verge-rev (`src-tauri/icons/icon.png`, `main` branch) | The Clash Verge Rev app icon (a white cat head on a pink-to-violet gradient), used to identify the mihomo client in the portal at the repository owner's choice (2026-10-09). The round icon is squared by extending its own gradient to the corners; the cat is unchanged. Clash Verge Rev is GPL-3.0; icon and trademark belong to the Clash Verge Rev project; not covered by this repository's terms. |
| `engine/portal/public/icons/singbox.jpg` | https://sing-box.sagernet.org/assets/icon.svg (SagerNet/sing-box documentation site) | The sing-box project's own icon (a taped box), placed at 400/512 on a square tile filled with the icon's own background gradient (#242F37 to #0D1317) and exported to JPEG, used only to identify the sing-box client in the portal. The project's code is GPL-3.0-or-later; a separate license for the icon was not found. Icon and trademark belong to the SagerNet project; not covered by this repository's terms. |
| `engine/portal/public/app-icons/*.jpg` | Apple App Store artwork (iTunes Search API) | Official app icons of each covered App (OKX, PayPal, SafePal, ZA Bank, LINE, Telegram, WhatsApp, GitHub, AWS Console, Steam, X, Instagram, Threads, Facebook, YouTube, Netflix, TikTok, Spotify, APTV, Disney+, Paramount+, Hulu, Prime Video, HBO Max, Twitch, Google, NBA, Suno, Starryblu, ChatGPT for the aggregated AI Rule-Set, and 抖音 (DouYin, China storefront, Beijing Douyin Technology Co., Ltd.)), downloaded from the App Store and used only to identify each Rule-Set in the portal. Seven of them (HBO Max, Instagram, Netflix, Spotify, Suno, Threads, TikTok) came with a baked-in rounded bezel; it is trimmed off (2.7 % per side) so the portal's own corner mask applies, with the artwork otherwise unchanged. Trademarks and icons belong to their respective owners; not covered by this repository's terms. |
| `engine/portal/public/stickers/*.webp` | The Daydream Archivist, cloud-head sticker set (https://daydream-archivist-room.vigozhao.chatgpt.site) | Nine stickers (288 px WebP) shown as the traveller persona on the completion page, the persona card and the boarding-pass ticket. The site publishes no license file; the repository owner confirmed with the author on 2026-10-02 that they may be used, and the portal credits the set wherever the stickers appear (the persona card, the ticket image and the footer). Not covered by this repository's terms. |
| `engine/portal/public/paint/*.webp` | Painting Loaders (https://painterly.design-tools.workers.dev), drawn with p5.brush 2.2.2 (https://github.com/acamposuribe/p5.brush, MIT License, Copyright (c) 2023-2026 Alejandro Campos Uribe) | Twelve watercolour stills (1080 px WebP) used as the painting band of the boarding-pass ticket, one chosen at random. Each was rendered once, offline, from the painting's "Copy code" on the site, unchanged, at twice its native size; neither the painting code nor p5.brush ships with the portal. The site publishes no license file; the repository owner confirmed with the author on 2026-10-02 that it may be used, and the ticket image names the painting and credits Painting Loaders under the card. Not covered by this repository's terms. |
| `engine/portal/src/fonts/PaperMono-subset.woff2` | Paper Mono by Lost Coast Labs / Paper Design (https://paper.design/mono, https://github.com/paper-design/paper-mono), based on Geist Mono | SIL Open Font License 1.1, no Reserved Font Name; the license text ships next to the font as `PaperMono-LICENSE.txt`. Subset to Basic Latin plus a few typographic signs (13 KB WOFF2) and used for rule text, URLs, policy-group names and numbers. Chinese and interface text use the system font stack. |

## License handling principles

- Do not remove, override, or misrepresent upstream copyright, license, or
  warranty notices.
- Do not assume that converting a rule source to Surge syntax removes upstream
  license obligations.
- Before redistributing, relicensing, or using a generated Rule-Set beyond
  personal use, review the full terms of every applicable upstream source.
- The Apache, MIT, GPL, AGPL, or other terms of one source do not automatically
  apply to files derived from another source.
- The public LICENSE applies its CC BY-NC-SA grant only to separately licensable
  original portions. It cannot override third-party GPL/AGPL or other obligations.

## Source access and reproducibility

The public manifest records upstream URLs and content fingerprints, canonical
fingerprints, and generated output hashes. Anyone can compare a downloaded output
with its recorded SHA256. Builder, source-definition and supplement paths now refer
to private files, so a full independent rebuild is not possible from the current
public tree alone. Earlier public source remains available in Git history, but
must not be assumed to reproduce later outputs.

ParamountPlus, Hulu and Twitch currently retain their GPL-2.0 sources; Telegram
retains its AGPL-3.0 sources. This repository split does not migrate these sources,
settle corresponding-source questions, or remove upstream license obligations.
No claim is made that publishing hashes alone fulfills such obligations. Those
four Apps require separate follow-up review by the maintainer.
