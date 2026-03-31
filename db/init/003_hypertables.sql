SELECT create_hypertable('energy_measurement', 'ts', if_not_exists => TRUE);
SELECT create_hypertable('machine_state_event', 'ts', if_not_exists => TRUE);