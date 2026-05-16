CREATE INDEX IF NOT EXISTS idx_machine_state_event_machine_ts_desc
ON machine_state_event (machine_id, ts DESC);

CREATE INDEX IF NOT EXISTS idx_cycle_event_machine_start_end
ON cycle_event (machine_id, cycle_start_ts, cycle_end_ts);

CREATE INDEX IF NOT EXISTS idx_energy_enriched_machine_ts
ON energy_enriched (machine_id, ts);

CREATE INDEX IF NOT EXISTS idx_energy_enriched_cycle_id
ON energy_enriched (cycle_id);