You are the sole frontend implementation agent for Wave 4 of the Predictive Manufacturing Workflow Engine.

Read first:
- all frontend reports generated so far
- frontend_architecture.md
- design_system.md
- assumptions.md
- demo_readiness_checklist.md if available
- deterministic_demo_script.md if available

Objective:
Polish the dashboard into a presentation-grade product and implement a strong demo mode.

Required deliverables:
1) final dashboard polish
2) demo mode
3) deterministic demo path
4) frontend_qa_report.md
5) demo_script_vFinal.md
6) screenshot_ready_views_final

Required polish work:
- visual consistency across all pages
- spacing, typography, hierarchy, and alignment cleanup
- consistent naming and terminology
- consistent color semantics
- synthetic-data badges styled cleanly
- assumption/warning callouts non-intrusive but visible
- loading, empty, and error states improved
- remove obvious draft/placeholder feel from the UI

Required demo features:
- default region already selected
- default quarter already selected
- default scenario already selected
- preconfigured “best demo path”
- guided narrative cards or subtle step labels
- ability to show the story in under 3 minutes:
  1) scoped pipeline
  2) prioritized opportunities
  3) translated operational exposure
  4) maintenance-aware bottlenecks
  5) sourcing and delivery risk
  6) disruption what-if
  7) final action list

Required QA checks:
- all navigation routes work
- filter state remains consistent across pages
- no broken widgets
- no misleading labels
- no page shows inconsistent terminology
- all fallback states are understandable
- all important data is visible above the fold where needed

Required “presentation readiness” checks:
- every page has a clear title and one-sentence purpose
- every advanced page has a short interpretation block
- top recommendation is always visible quickly
- dashboard can be understood by product owners without code explanation

Success condition:
The frontend looks like a polished product prototype, not an engineering dashboard, and can carry the full hackathon presentation.