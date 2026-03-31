CREATE TABLE IF NOT EXISTS machine (
    machine_id TEXT PRIMARY KEY,
    machine_name TEXT NOT NULL,
    manufacturer TEXT,
    model TEXT,
    machine_type TEXT
);

CREATE TABLE IF NOT EXISTS operation (
    operation_id TEXT PRIMARY KEY,
    operation_name TEXT NOT NULL,
    ideal_cycle_time_sec NUMERIC(10,2) NOT NULL
);

CREATE TABLE IF NOT EXISTS state_mapping (
    detailed_state_code TEXT PRIMARY KEY,
    detailed_state_name TEXT NOT NULL,
    state_tag TEXT NOT NULL,
    oee_loss_type TEXT
);

CREATE TABLE IF NOT EXISTS energy_measurement (
    ts TIMESTAMPTZ NOT NULL,
    machine_id TEXT NOT NULL,
    power_kw NUMERIC(10,3) NOT NULL,
    energy_kwh_cumulative NUMERIC(12,5),
    sample_interval_sec NUMERIC(10,3),
    PRIMARY KEY (ts, machine_id),
    FOREIGN KEY (machine_id) REFERENCES machine(machine_id)
);

CREATE TABLE IF NOT EXISTS machine_state_event (
    ts TIMESTAMPTZ NOT NULL,
    machine_id TEXT NOT NULL,
    detailed_state_code TEXT NOT NULL,
    state_tag TEXT NOT NULL,
    reason_code TEXT,
    is_planned_stop BOOLEAN DEFAULT FALSE,
    idle_reason TEXT,
    PRIMARY KEY (ts, machine_id),
    FOREIGN KEY (machine_id) REFERENCES machine(machine_id),
    FOREIGN KEY (detailed_state_code) REFERENCES state_mapping(detailed_state_code)
);

CREATE TABLE IF NOT EXISTS cycle_event (
    cycle_id TEXT PRIMARY KEY,
    machine_id TEXT NOT NULL,
    operation_id TEXT NOT NULL,
    cycle_start_ts TIMESTAMPTZ NOT NULL,
    cycle_end_ts TIMESTAMPTZ NOT NULL,
    actual_cycle_time_sec NUMERIC(10,3) NOT NULL,
    part_result TEXT NOT NULL,
    scrap_reason TEXT,
    FOREIGN KEY (machine_id) REFERENCES machine(machine_id),
    FOREIGN KEY (operation_id) REFERENCES operation(operation_id)
);

CREATE TABLE IF NOT EXISTS energy_enriched (
    ts TIMESTAMPTZ NOT NULL,
    machine_id TEXT NOT NULL,
    power_kw NUMERIC(10,3) NOT NULL,
    delta_energy_kwh NUMERIC(12,6),
    detailed_state_code TEXT,
    state_tag TEXT,
    cycle_id TEXT,
    PRIMARY KEY (ts, machine_id),
    FOREIGN KEY (machine_id) REFERENCES machine(machine_id),
    FOREIGN KEY (detailed_state_code) REFERENCES state_mapping(detailed_state_code),
    FOREIGN KEY (cycle_id) REFERENCES cycle_event(cycle_id)
);

CREATE TABLE IF NOT EXISTS cycle_energy_summary (
    cycle_id TEXT PRIMARY KEY,
    machine_id TEXT NOT NULL,
    operation_id TEXT NOT NULL,
    cycle_start_ts TIMESTAMPTZ NOT NULL,
    cycle_end_ts TIMESTAMPTZ NOT NULL,
    cycle_energy_kwh NUMERIC(12,6) NOT NULL,
    part_result TEXT NOT NULL,
    FOREIGN KEY (cycle_id) REFERENCES cycle_event(cycle_id),
    FOREIGN KEY (machine_id) REFERENCES machine(machine_id),
    FOREIGN KEY (operation_id) REFERENCES operation(operation_id)
);