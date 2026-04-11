02_PROJECT_BASELINE
===================

Single reference table with one row per project.
  project_master.csv              — Contract value, estimated cost, built-in margin,
                                    approved/rejected CO totals, project type, GC,
                                    revised contract value, schedule growth.
  Every subsequent step joins back to this file via project_id.
