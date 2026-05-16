DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'chk_operation_ideal_cycle_time_positive'
    ) THEN
        ALTER TABLE operation
        ADD CONSTRAINT chk_operation_ideal_cycle_time_positive
        CHECK (ideal_cycle_time_sec > 0);
    END IF;
END
$$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'chk_energy_measurement_power_non_negative'
    ) THEN
        ALTER TABLE energy_measurement
        ADD CONSTRAINT chk_energy_measurement_power_non_negative
        CHECK (power_kw >= 0);
    END IF;
END
$$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'chk_energy_measurement_sample_interval_positive'
    ) THEN
        ALTER TABLE energy_measurement
        ADD CONSTRAINT chk_energy_measurement_sample_interval_positive
        CHECK (sample_interval_sec IS NULL OR sample_interval_sec > 0);
    END IF;
END
$$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'chk_cycle_event_time_order'
    ) THEN
        ALTER TABLE cycle_event
        ADD CONSTRAINT chk_cycle_event_time_order
        CHECK (cycle_end_ts > cycle_start_ts);
    END IF;
END
$$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'chk_cycle_event_actual_cycle_time_positive'
    ) THEN
        ALTER TABLE cycle_event
        ADD CONSTRAINT chk_cycle_event_actual_cycle_time_positive
        CHECK (actual_cycle_time_sec > 0);
    END IF;
END
$$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'chk_cycle_event_part_result_valid'
    ) THEN
        ALTER TABLE cycle_event
        ADD CONSTRAINT chk_cycle_event_part_result_valid
        CHECK (part_result IN ('good', 'scrap'));
    END IF;
END
$$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'chk_cycle_energy_summary_time_order'
    ) THEN
        ALTER TABLE cycle_energy_summary
        ADD CONSTRAINT chk_cycle_energy_summary_time_order
        CHECK (cycle_end_ts > cycle_start_ts);
    END IF;
END
$$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'chk_cycle_energy_summary_energy_non_negative'
    ) THEN
        ALTER TABLE cycle_energy_summary
        ADD CONSTRAINT chk_cycle_energy_summary_energy_non_negative
        CHECK (cycle_energy_kwh >= 0);
    END IF;
END
$$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'chk_cycle_energy_summary_part_result_valid'
    ) THEN
        ALTER TABLE cycle_energy_summary
        ADD CONSTRAINT chk_cycle_energy_summary_part_result_valid
        CHECK (part_result IN ('good', 'scrap'));
    END IF;
END
$$;