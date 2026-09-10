# Retained A061: current development gaps against MM

2026-09-10. A061 remains the single retained algorithm. The [breadth table](mm_gap_retained_a061.md) remains authoritative for its original 34 structures; none of the three new candidates replaces it. These separate development cohorts add fresh instances, sizes, two-seed observations and a relabel. Do not pool repeated structures across hosts or select their best outcomes. No confirmation set has been exposed or claimed.

## Fresh development and regression anchors on hyde06

One seed per encoding. All A061, MM and A067 calls succeed12/12. ACL is therefore a one-observation mean; across-seed variability is unmeasured here. A067 is shown only as a rejected research policy, never substituted for A061. Positive differences favor MM.

| Class / input | n | A061 ACL | MM ACL | A061 − MM Q | A061 / MM solver s | A067 − MM Q |
|---|---:|---:|---:|---:|---:|---:|
| random_er / g0301 | 96 | 4.145833 | 4.197917 | -5 | 9.600 / 2.981 | -31 |
| barabasi_albert / g0302 | 96 | 3.020833 | 3.312500 | -28 | 9.681 / 2.248 | -38 |
| regular / g0303 | 96 | 3.822917 | 4.145833 | -31 | 6.970 / 3.378 | -46 |
| watts_strogatz / g0304 | 96 | 2.333333 | 2.000000 | +32 | 8.948 / 0.915 | +25 |
| sbm / g0305 | 96 | 2.333333 | 2.343750 | -1 | 5.921 / 1.555 | -8 |
| random_planar / g0306 | 96 | 1.583333 | 1.645833 | -6 | 7.707 / 0.557 | -6 |
| singleton control / g0307 | 96 | 2.770833 | 1.968750 | +77 | 10.059 / 2.314 | +71 |
| branch control / g0308 | 96 | 1.843750 | 1.781250 | +6 | 5.362 / 1.047 | +4 |
| barabasi_albert (relabel) / g0309 | 96 | 2.781250 | 2.854167 | -7 | 9.638 / 3.433 | -11 |
| random_er / g0007 | 160 | 8.056250 | 10.525000 | -395 | 14.705 / 27.960 | -424 |
| sbm / g0011 | 160 | 5.587500 | 5.206250 | +61 | 13.671 / 15.765 | +1 |
| wheel / g0015 | 127 | 1.622047 | 1.133858 | +62 | 6.831 / 4.495 | +4 |

Excluding the BA relabel, A061 has six lower-Q and five higher-Q outcomes on eleven structures; A067 has the same six/five split. Its gains reduce some deficits but do not convert a retained loss to a MM win in this cohort. A067 loses one qubit against both immediate controls on regular96. Fresh source-family wins do not establish class-wide dominance: WS96, SBM160, wheel and both hidden-witness controls retain gaps. The controls carry no optimality claim about MM.

## Two-seed supplement on hyde02

Each displayed mean and sample variance uses exactly two credited seeds of the named algorithm. All A061/MM attempts succeed in these panels. The same graph on another host is a separate timing cohort, not an independent structure. Individual losses remain visible as seed-specific Q differences.

| Class / input | Mean ACL A061 / MM | Sample ACL variance A061 / MM | Q differences seeds0 /1 | Mean solver s A061 / MM |
|---|---:|---:|---:|---:|
| grid / g0013 | 1.289062 / 1.039062 | 0.001099 / 0.000000 | +35 / +29 | 35.685 / 1.222 |
| random_er / g0301 | 3.963542 / 4.364583 | 0.066461 / 0.055556 | -5 / -72 | 37.056 / 11.634 |
| barabasi_albert / g0302 | 3.010417 / 3.067708 | 0.000217 / 0.119846 | -28 / +17 | 27.445 / 14.595 |
| sbm / g0305 | 2.406250 / 2.302083 | 0.010634 / 0.003472 | -1 / +21 | 29.825 / 4.681 |
| branch control / g0308 | 1.927083 / 1.807292 | 0.007812 / 0.001356 | +8 / +15 | 31.293 / 2.639 |
| barabasi_albert (relabel) / g0309 | 2.932292 / 2.921875 | 0.045627 / 0.009169 | -7 / +9 | 33.301 / 21.034 |

## Two-seed supplement on hyde03

Each displayed mean and sample variance uses exactly two credited seeds of the named algorithm. All A061/MM attempts succeed in these panels. The same graph on another host is a separate timing cohort, not an independent structure. Individual losses remain visible as seed-specific Q differences.

| Class / input | Mean ACL A061 / MM | Sample ACL variance A061 / MM | Q differences seeds0 /1 | Mean solver s A061 / MM |
|---|---:|---:|---:|---:|
| grid / g0013 | 1.285156 / 1.039062 | 0.001495 / 0.000000 | +35 / +28 | 5.615 / 0.292 |
| barabasi_albert / g0302 | 3.005208 / 3.067708 | 0.000488 / 0.119846 | -28 / +16 | 6.157 / 3.696 |
| sbm / g0305 | 2.406250 / 2.302083 | 0.010634 / 0.003472 | -1 / +21 | 5.827 / 0.953 |
| singleton control / g0307 | 2.614583 / 1.901042 | 0.048828 / 0.009169 | +77 / +60 | 5.842 / 1.396 |
| barabasi_albert (relabel) / g0309 | 2.916667 / 2.921875 | 0.036675 / 0.009169 | -7 / +6 | 5.749 / 3.031 |

## Decision implications

Sparse local structure and the hardware-derived controls remain substantial quality and runtime deficits. A shared requirement is placing contacts to several source neighbors at few physical sites. Existing MM map inspection attributes much of the grid, honeycomb and wheel excess to low-degree owners and shows more multi-contact singletons; BA also benefits from branching. The controls extend the question to different degree profiles. The seed reversal on BA96 and SBM96 prevents treating a single favorable outcome as a family-wide win. Placement and contact compatibility plausibly connect several deficits, but are not proved to explain every class.

A067 changes attachment reach but adds no MM-win structure in its panel and still spends approximately59s per call. C018 demonstrates whole-owner relocation can reach validity across structures, but starts with large chains and loses every complete quality comparison. B030 does not reach validity in either arm despite substantial local activity. These outcomes favor replacing local proposal assumptions and improving construction compactness; they do not support promotion, merely raising an arbitrary work cap, or accelerating failed local moves as the sole next step.

All failure costs, solver CPU, process wall and within-chain variance remain in the original audit rows and track reports: [A067](experiments/067_contact_coverage_results.md), [B030](tracks/b_030_results.md), [C018](tracks/c_018_results.md). Within-chain variance is not the across-seed ACL variance above. Two seeds offer descriptive evidence only. Host loads were not exclusive, and timing comparisons are paired within each host.

Source rows (unchanged original audit outputs):

- `results/codex/a067-transfer/audit001/output/rows.json` — SHA256 `13f8b0ab8cc6e945f5235a375b076e6e10b6245483956c83c05a4eadbfd3bdf3`.
- `results/codex/b030-constructor/audit001/output/rows.json` — SHA256 `baf286dc01160483bc61c98c2d6019234f7c529fab13477685e08d15c38c0665`.
- `results/codex/c018-territories/audit001/output/rows.json` — SHA256 `62898574e061436f8a5e53d5680b413ce138356ece4651688fbf64333918b59d`.
