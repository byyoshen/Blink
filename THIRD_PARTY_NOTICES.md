# Third-Party Notices

## Scope

Blink contains original build code, tests, workflow configuration, and
documentation, together with generated multi-client Rule-Sets derived from
publicly available upstream rule sources.

This file records the known upstream provenance and license or project notice
for each generated Rule-Set. It is an attribution and compliance reference,
not legal advice and not a replacement for the full upstream terms.

`Surge/*.list` files are generated artifacts. Blink does not claim to
relicense upstream rules, nor does this repository grant permissions beyond
those available from the applicable upstream authors and licenses.

The `LICENSE` file in the repository root (MIT License) covers only Blink's
original build code, tests, workflow configuration, portal source, and
documentation. It does **not** cover generated Rule-Sets, derived `Profiles/`,
or any upstream material, which remain subject to the terms recorded in this
file.

## Generated Rule-Set provenance

The `Surge/<App>.list` table below is the canonical provenance record.
`Loon/<App>.list`, `Shadowrocket/<App>.list`, and `Stash/<App>.list` are
byte-identical copies of the Surge output; `Clash/<App>.list` is the same
classical output with `USER-AGENT` lines removed (the Clash family has no
such rule type; the builder drops and counts them explicitly);
`Egern/<App>.yaml` and `QuantumultX/<App>.list` are rendered from the same
canonical rule set; all of them inherit the provenance and license
attribution of the corresponding `Surge/<App>.list` row without any
additional upstream source. The semantic view files
(`<App>-domainset.conf` / `<App>-nonip.conf` / `<App>-ip.conf`) are likewise
derived from the same canonical rules and inherit the same attribution.

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
| `Surge/GitHub.list` | v2fly/domain-list-community | https://github.com/v2fly/domain-list-community | MIT License |
| `Surge/SafePal.list` | v2fly/domain-list-community | https://github.com/v2fly/domain-list-community | MIT License |
| `Surge/Threads.list` | v2fly/domain-list-community | https://github.com/v2fly/domain-list-community | MIT License |
| `Surge/PayPal.list` | Repcz/Tool | https://github.com/Repcz/Tool | MIT License |
| `Surge/YouTube.list` | Repcz/Tool | https://github.com/Repcz/Tool | MIT License |
| `Surge/X.list` | Repcz/Tool | https://github.com/Repcz/Tool | MIT License |
| `Surge/Instagram.list` | Repcz/Tool | https://github.com/Repcz/Tool | MIT License |
| `Surge/Telegram.list` | SukkaW/Surge (non-IP rules) + SukkaW ruleset service `List/ip/telegram.conf` (IP segment) | https://github.com/SukkaW/Surge | AGPL-3.0 for these rule sources; see upstream README for exceptions |
| `Surge/Netflix.list` | blackmatrix7/ios_rule_script | https://github.com/blackmatrix7/ios_rule_script | GPL-2.0 |
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

The exact source URL, format, and selection rationale for each App are kept in
[`engine/sources/apps.yaml`](engine/sources/apps.yaml). Upstream projects may change their
licenses, notices, source content, or repository structure; source audits and
this notice must be reviewed whenever a source is added or replaced.

## Repository assets

| Asset | Origin | Notice |
| --- | --- | --- |
| `engine/portal/public/blink-logo.png` | Repository owner (original IP mascot) | Blink brand mascot (white cat, lower-left composition), created by the repository owner for identifying Blink in the portal navigation, footer, and browser tab. Owned by the repository owner; not covered by any third-party license. |
| `engine/portal/public/favicon-cat.png` | Repository owner (original IP mascot) | Circular-cropped variant of `blink-logo.png` (transparent corners), used as the browser-tab favicon for the dark theme. Owned by the repository owner; not covered by any third-party license. |
| `engine/portal/public/favicon-dog.png` | Repository owner (original IP mascot) | Circular-cropped variant of `blink-logo-2.png` (transparent corners), used as the browser-tab favicon for the light theme. Owned by the repository owner; not covered by any third-party license. |
| `engine/portal/public/blink-logo-2.png` | Repository owner (original IP mascot) | Light-theme variant of the Blink mascot (blue dog, upper-right composition), used when the portal theme is light. Owned by the repository owner; not covered by any third-party license. |
| `engine/docs/images/avatar.png` | 仓库所有者原创 IP mascot（白猫，与 portal `blink-logo.png` 相同图源） | Circular-cropped variant (transparent corners) used as the README title mark. Owned by the repository owner; not covered by any third-party license. |
| `engine/portal/public/icons/*.jpg` | Apple App Store artwork (iTunes Search API) | Official app icons of Surge, Shadowrocket, Loon, Stash, Egern, and Quantumult X, downloaded from the App Store and used only to identify each supported client in the portal. Trademarks and icons belong to their respective owners; not covered by this repository's terms. |
| `engine/portal/public/icons/clash.jpg` | https://github.com/MetaCubeX/ClashMetaForAndroid (`app/src/main/res/mipmap-xxxhdpi/ic_launcher.png`) | Clash Meta for Android app icon (GPL-3.0), re-encoded to JPEG and used only to identify the Clash client in the portal. Icon and trademark belong to the Clash Meta project; not covered by this repository's terms. |
| `engine/portal/public/app-icons/*.jpg` | Apple App Store artwork (iTunes Search API) | Official app icons of each covered App (OKX, PayPal, SafePal, ZA Bank, LINE, Telegram, WhatsApp, GitHub, Steam, Instagram, Threads, X, YouTube, Netflix, TikTok, Spotify, APTV, Starryblu, and ChatGPT for the aggregated AI Rule-Set), downloaded from the App Store and used only to identify each Rule-Set in the portal. Trademarks and icons belong to their respective owners; not covered by this repository's terms. |

## License handling principles

- Do not remove, override, or misrepresent upstream copyright, license, or
  warranty notices.
- Do not assume that converting a rule source to Surge syntax removes upstream
  license obligations.
- Before redistributing, relicensing, or using a generated Rule-Set beyond
  personal use, review the full terms of every applicable upstream source.
- The Apache, MIT, GPL, AGPL, or other terms of one source do not automatically
  apply to files derived from another source.
- The root `LICENSE` (MIT) covers only Blink's original code and documentation;
  it must not be read as covering generated Rule-Sets, derived Profiles, or
  upstream material, which remain subject to the terms recorded above unless a
  separate license audit establishes that broader licensing is appropriate.

## Source access and reproducibility

The repository publishes the source manifest, conservative build logic, and
GitHub Actions workflow used to create generated files. These materials are
provided to make the transformation reviewable; they do not replace any source
availability, attribution, or license obligations imposed by upstream authors.
