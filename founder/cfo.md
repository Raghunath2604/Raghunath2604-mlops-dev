# Unit economics: MLOps.dev (Edge AI Fleet Management SaaS)

Every number below comes from the input file. Nothing is looked up or guessed.

## One subscription_month

| line | per subscription_month |
| --- | ---: |
| Price | $149.00 |
| Cloudflare & Edge Bandwidth | -$4.50 |
| Managed Database & Cache | -$6.20 |
| Payment Processing (2.9% + $0.30) | -$4.62 |
| Telemetry & Log Storage | -$3.50 |
| **Contribution** (what each subscription_month leaves to pay the fixed costs) | **$130.18** (87%) |

## The margin that matters

Fixed costs: $300 a month (WSGI Backend Infrastructure $120, Logging & Monitoring $60, DNS, Domains & Certificates $25, Tooling & Security Automation $95).

- **Break-even: 1 subscription_months a day.** Below that you lose money every month.
- **Profit margin at your plan** (2 a day): **85%** of every sale, after every cost.
- Capacity: 50 a day.

## Year 1, month by month

| month | subscription_months a day | revenue | profit | cumulative (after $750 startup) |
| ---: | ---: | ---: | ---: | ---: |
| 1 | 0 | $894 | $481 | -$269 |
| 2 | 0 | $1,788 | $1,262 | $993 |
| 3 | 1 | $3,129 | $2,434 | $3,427 |
| 4 | 1 | $4,470 | $3,605 | $7,032 |
| 5 | 1 | $5,811 | $4,777 | $11,809 |
| 6 | 2 | $7,152 | $5,949 | $17,758 |
| 7 | 2 | $8,493 | $7,120 | $24,878 |
| 8 | 2 | $9,387 | $7,901 | $32,780 |
| 9 | 2 | $10,281 | $8,682 | $41,462 |
| 10 | 2 | $10,728 | $9,073 | $50,535 |
| 11 | 2 | $11,175 | $9,464 | $59,999 |
| 12 | 2 | $11,175 | $9,464 | $69,462 |

- **Year 1 operating profit: $70,212** on $84,483 of revenue.
- After the $750 startup spend: $69,462.
- Startup money earned back: month 2.
- Cash you need before it pays for itself: **$750**.

## What if

| scenario | margin at plan | break-even a day | year 1 profit |
| --- | ---: | ---: | ---: |
| Base plan | 85% | 1 | $70,212 |
| Price -10% | 83% | 1 | $61,764 |
| Volume -20% | 84% | 1 | $55,450 |
| Unit costs +15% | 83% | 1 | $68,611 |

No red flags in these numbers. They are only as good as the inputs: check every cost against a real quote.
