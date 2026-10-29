# Data sources and attribution

This repository includes small frozen observations used to reproduce the
2026-10-23 synthetic study. The versioned source lock records the URLs,
observation and release dates, units, transformations, paths and SHA256 hashes.

- US Department of the Treasury, Daily Treasury Par Yield Curve Rates. The
  project uses the 2026-10-22 observation from the official 2026 annual XML.
  Treasury rates are par yields. The model applies a simplified synthetic
  semiannual par bootstrap; the result is a discount-curve proxy rather than an
  observed Treasury zero curve.
- Board of Governors of the Federal Reserve System, H.8 Assets and Liabilities
  of Commercial Banks in the United States. The project uses the release dated
  2026-10-16 and observation dated 2026-10-07 for all US commercial banks,
  weekly Wednesday levels, not seasonally adjusted. XML USD millions are
  divided by 1,000 for stored USD billions.

The Federal Reserve Board's official
[disclaimer](https://www.federalreserve.gov/disclaimer.htm) states that, unless
otherwise indicated, information on its website is in the public domain and may
be copied and distributed without permission; it asks users to cite the Board.
The Treasury files used here are factual US government data downloaded from the
official Treasury site. Treasury's
[site policies and notices](https://home.treasury.gov/subfooter/site-policies-and-notices)
remain the controlling reference for that site.

The repository redistributes only the frozen source responses and small factual
extracts required for reproducibility. The official sources provide their
material as published and do not endorse this project. No agency seals, logos,
third-party graphics or materials marked with separate reuse restrictions are
included.

Project code and original project documentation are licensed separately under
`LICENSE`. Source attribution does not change any source-specific terms. Review
the official policies before redistributing a different or expanded extract.
