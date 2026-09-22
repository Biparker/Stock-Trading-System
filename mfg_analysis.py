#!/usr/bin/env python3
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Raw data from screen_manufacturing.py run
# (ticker, sub, price, mktcap_b, pe, fwdpe, de, margin, revgr, beta, analyst, upside, r7, r30, r90, vol)
rows = [
    ('BA',  'Aero/Defense',     216.25, 170.5, 85.5, 51.7, 828.7,  2.46,  14.0,  1.20, 1.63,  24.9, -2.07, -1.98,   4.31, 2.23),
    ('RTX', 'Aero/Defense',     187.97, 253.1, 35.2, 24.8,  57.2,  8.03,   8.7,  0.31, 1.87,  14.8,  3.38,  7.28,  -3.06, 1.76),
    ('LMT', 'Aero/Defense',     505.31, 116.5, 24.5, 15.7, 276.4,  6.38,   0.3,  0.11, 2.62,  23.5,  2.37, -3.73, -17.65, 1.72),
    ('NOC', 'Aero/Defense',     503.94,  71.6, 15.8, 16.7, 102.7, 10.80,   4.4, -0.12, 1.96,  37.9, -0.67, -7.97, -27.38, 1.72),
    ('GD',  'Aero/Defense',     353.00,  95.5, 22.2, 19.4,  37.7,  8.07,  10.3,  0.34, 2.12,  11.4,  2.81,  2.88,   1.17, 1.74),
    ('CAT', 'Ind. Machinery',  1070.00, 492.8, 53.4, 35.5, 230.8, 13.33,  22.2,  1.60, 2.11, -11.1,  4.67, 23.85,  46.79, 2.91),
    ('DE',  'Ind. Machinery',   634.35, 171.2, 35.9, 27.8, 376.0, 10.10, -11.1,  0.93, 2.12,   1.6,  5.97, 12.38,  11.15, 2.22),
    ('EMR', 'Ind. Machinery',   143.78,  80.5, 33.4, 20.0,  69.2, 13.35,   2.9,  1.25, 1.89,  14.4, -4.28,  8.74,   9.06, 2.21),
    ('ETN', 'Ind. Machinery',   425.32, 165.2, 41.7, 27.0, 110.5, 13.99,  16.8,  1.19, 1.63,   7.1, -2.40, 11.38,  16.67, 2.84),
    ('PH',  'Ind. Machinery',   971.01, 122.4, 35.9, 28.5,  65.6, 16.58,  10.6,  1.14, 1.68,   6.6,  0.92, 13.11,   5.69, 1.83),
    ('HON', 'Div. Industrial',  223.91,  70.9, 17.9, 25.6, 257.4, 10.89,   2.4,  0.84, 2.04, 112.0, -1.85,  3.06,  -1.33, 2.03),
    ('GE',  'Div. Industrial',  368.99, 385.5, 46.0, 42.5, 116.5, 17.86,  24.7,  1.38, 1.50,  -3.9,  3.90, 29.02,  26.07, 2.50),
    ('MMM', 'Div. Industrial',  161.46,  84.2, 31.0, 17.0, 396.5, 11.14,   1.3,  1.09, 2.28,   5.8, -1.08,  6.40,  11.73, 1.48),
    ('ITW', 'Div. Industrial',  268.38,  77.2, 24.9, 22.0, 283.2, 19.32,   4.6,  1.03, 3.25,   3.5,  1.16,  7.59,   3.01, 1.38),
    ('ROK', 'Div. Industrial',  493.80,  54.9, 51.2, 33.8, 113.4, 12.36,  11.9,  1.56, 2.25,  -5.7,  3.29, 13.16,  34.26, 2.36),
]

print()
print("Manufacturing Sector — Filter Analysis at Adjusted D/E Limit (4.0)")
print("=" * 75)

for de_max, pe_max, label in [(2.5, 40, "CURRENT filters (pe<=40, de<=2.5)"),
                               (4.0, 40, "ADJUSTED filters (pe<=40, de<=4.0)")]:
    passers = []
    for r in rows:
        t, sub, price, mc, pe, fpe, de, mar, rg, beta, an, up, r7, r30, r90, vol = r
        mc_ok  = mc  >= 10
        pe_ok  = pe  >  0
        pro_ok = mar >  0
        pelim  = (pe <= pe_max) if pe > 0 else True
        delim  = (de <= de_max) if de > 0 else True
        ok = all([mc_ok, pe_ok, pro_ok, pelim, delim])
        if ok:
            passers.append(r)

    print()
    print(f"  {label}")
    print(f"  Passed: {len(passers)}/15 -- {[r[0] for r in passers]}")
    if passers:
        print()
        print(f"  {'Ticker':<5} {'Sub':<18} {'P/E':>5} {'FwdPE':>6} {'D/E':>6} {'Margin%':>8} {'Upside%':>8} {'90d%':>6} {'Beta':>5} {'Analyst':>7} {'Vol%':>5}")
        print("  " + "-" * 80)
        for r in passers:
            t, sub, price, mc, pe, fpe, de, mar, rg, beta, an, up, r7, r30, r90, vol = r
            print(f"  {t:<5} {sub:<18} {pe:>5.1f} {fpe:>6.1f} {de:>6.1f} {mar:>8.2f} {up:>8.1f} {r90:>6.2f} {beta:>5.2f} {an:>7.2f} {vol:>5.2f}")

print()
print("Key Observations:")
print("  - ALL 15 manufacturing names fail the D/E <= 2.5 limit")
print("  - Manufacturing is structurally capital-intensive; D/E 50-400 is industry-normal")
print("  - At D/E <= 4.0 (still strict), still 0 pass because most D/E is 50-800+")
print("  - The D/E metric as applied to manufacturing is not a useful discriminator")
print("  - Better filter for manufacturing: Interest Coverage > 3x, or Gross Margin > 8%")
print()
print("Best candidates by quality (ignoring D/E):")
quality = sorted(rows, key=lambda r: (-r[6+1], r[4], r[9]))  # sort by margin desc, pe asc, beta asc
quality_filtered = [(r[0], r[1], r[4], r[5], r[6], r[7], r[10], r[11], r[14], r[15])
                    for r in rows if r[4] > 0 and r[4] <= 40 and r[7] > 0]
quality_filtered.sort(key=lambda x: (-x[7], x[2]))  # sort by upside desc
print(f"  {'Ticker':<5} {'Sub':<18} {'P/E':>5} {'FwdPE':>6} {'D/E':>6} {'Margin%':>8} {'Analyst':>7} {'Upside%':>8} {'90d%':>6} {'Vol%':>5}")
print("  " + "-" * 80)
for r in quality_filtered:
    t, sub, pe, fpe, de, mar, an, up, r90, vol = r
    print(f"  {t:<5} {sub:<18} {pe:>5.1f} {fpe:>6.1f} {de:>6.1f} {mar:>8.2f} {an:>7.2f} {up:>8.1f} {r90:>6.2f} {vol:>5.2f}")
