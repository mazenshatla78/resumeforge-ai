# ResumeForge AI — Page-by-Page Reference Map

## Reference: TealHQ (primary, same category)
| Teal element | ResumeForge AI equivalent | Adapted pattern |
|---|---|---|
| Hero: "Build Your Resume. Land 6X more Interviews." + subtitle + CTA | Landing hero | Strong headline, subhead, primary CTA "Analyze My Resume", secondary "See How It Works", product preview card |
| Tabbed product preview (AI Resumes / Job Tracker / ATS Checker) | Hero product preview card | Single animated score card with matched/missing keywords |
| "How it Works" 4 numbered steps (Sign up, Search, Apply, Grow) | How it works section | 3 numbered steps: Upload, Analyze, Get package |
| Feature grid (Job Tracker, AI Resumes, ATS Checker, ...) | Features section | 6 feature cards with icons |
| "Need to level up faster?" CTA band | Final CTA section | Gradient CTA band |
| Footer: Tools / Templates / Resources / Comparisons / Company columns | Footer | Product / Resources / Contact columns |

## Reference: Linear (dashboard, nav, polish)
| Linear element | ResumeForge AI equivalent | Adapted pattern |
|---|---|---|
| Minimal top nav with logo + links + CTA | Top nav | Logo + Features/How/About/Contact + Sign in/Sign up |
| Sidebar navigation with icons + active state | App sidebar | Icon + label nav, active bg-brand-50 |
| Clean data tables, status badges | Admin tables | Bordered tables with status badges |
| Subtle borders, neutral surfaces, crisp typography | Design system | Ink scale neutrals, brand accent, Inter |
| Command-palette feel (not implemented) | — | Documented as future |

## Reference: Framer (landing composition, pricing)
| Framer element | ResumeForge AI equivalent | Adapted pattern |
|---|---|---|
| Bold hero typography, scroll reveals | Landing hero | Large extrabold headline, fade-in/slide-up |
| Pricing cards with toggle | (Pricing is in-app billing) | Monthly/annual emphasis |
| Section rhythm with generous spacing | All landing sections | py-20 sections, max-w containers |
| Gradient CTA bands | Final CTA | brand→purple gradient band |

## ResumeForge AI pages
- `/` Landing (hero, problems, how-it-works, testimonials, FAQ, CTA, footer)
- `/login`, `/signup` Dedicated auth pages
- `/dashboard` (in-app) Overview, stats, recent activity
- `/dashboard/analyze` Upload + multi-stage processing
- `/dashboard/analysis/:id` Score, strengths/weaknesses, recommendations, tabs
- `/dashboard/history` Searchable history
- `/dashboard/billing` Plan + upgrade
- `/dashboard/profile` Account + danger zone
- `/admin/*` Admin platform
- `/about`, `/contact`, `/privacy`

## Implemented (not copied)
- Original color palette (brand blue #1d5ae6 + purple accent #8b5cf6 on ink neutrals)
- Original SVG logo (document + AI spark)
- Original copy and feature descriptions
- Original component classes
