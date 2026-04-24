You are the sole frontend implementation agent for Wave 5 of the Predictive Manufacturing Workflow Engine.

Read first:
- frontend_audit.md
- frontend_migration_plan.md
- all wave reports
- assumptions.md
- contracts.md

Objective:
Finalize the frontend implementation, ensure clarix migration is complete, and produce a clean handoff package for the team.

Required deliverables:
1) final clarix migration completion note
2) frontend_handoff.md
3) component_map_final.md
4) data_binding_map_final.md
5) known_limitations_frontend.md

Tasks:
1) confirm which clarix components/pages survived into final product
2) remove or isolate deprecated frontend pieces
3) document the final routing map
4) document the final data-binding map:
   - which page consumes which tables
   - what v1/v2 fallback logic exists
5) document known frontend limitations clearly
6) identify any remaining brittle areas for the team
7) ensure codebase is clean enough for final live use

Required sections in frontend_handoff.md:
- how to run the frontend
- where the main pages live
- where the shared components live
- where the data adapters live
- how filters work
- how demo mode works
- what assumptions the frontend surfaces
- how to extend pages after the hackathon

Validation requirements:
- final clarix migration status is explicit
- handoff docs are sufficient for another teammate to continue
- deprecated pieces are not left ambiguous
- frontend is stable enough for final presentation use

Success condition:
The frontend is not only polished, but maintainable and understandable for the rest of the team.