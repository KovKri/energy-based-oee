CREATE TABLE IF NOT EXISTS regression_dashboard_summary (
    model_scope TEXT PRIMARY KEY CHECK (model_scope IN ('primary', 'secondary')),
    display_order SMALLINT NOT NULL UNIQUE,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    target_name TEXT NOT NULL,
    target_label TEXT NOT NULL,
    model_type TEXT NOT NULL,

    n_obs INTEGER NOT NULL,
    pseudo_r2 DOUBLE PRECISION,

    significant_features TEXT NOT NULL,
    non_significant_features TEXT,

    headline TEXT NOT NULL,
    explanation TEXT NOT NULL,
    technical_note TEXT NOT NULL
);