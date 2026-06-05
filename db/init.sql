CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE simulated_users (
    user_id           TEXT PRIMARY KEY,
    role              TEXT NOT NULL,
    home_country      TEXT NOT NULL,
    home_ip_prefix    TEXT NOT NULL,
    work_hours_start  INT  NOT NULL,
    work_hours_end    INT  NOT NULL,
    typical_user_agent TEXT NOT NULL,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE logs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ts              TIMESTAMPTZ NOT NULL,
    user_id         TEXT NOT NULL,
    source_ip       TEXT NOT NULL,
    geo_country     TEXT NOT NULL,
    action          TEXT NOT NULL,
    resource        TEXT,
    bytes_out       BIGINT NOT NULL DEFAULT 0,
    status          TEXT NOT NULL,
    user_agent      TEXT NOT NULL,
    mfa_used        BOOLEAN NOT NULL DEFAULT FALSE,
    is_anomaly_truth BOOLEAN NOT NULL DEFAULT FALSE,
    anomaly_kind    TEXT,
    anomaly_score   DOUBLE PRECISION,
    score_reasons   JSONB,
    flagged         BOOLEAN NOT NULL DEFAULT FALSE,
    investigated    BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX logs_ts_idx        ON logs (ts DESC);
CREATE INDEX logs_user_ts_idx   ON logs (user_id, ts DESC);
CREATE INDEX logs_flagged_idx   ON logs (flagged) WHERE flagged = TRUE;
CREATE INDEX logs_pending_idx   ON logs (flagged, investigated) WHERE flagged = TRUE AND investigated = FALSE;

CREATE TABLE baselines (
    user_id              TEXT PRIMARY KEY,
    typical_hours        INT[]  NOT NULL DEFAULT '{}',
    typical_countries    TEXT[] NOT NULL DEFAULT '{}',
    typical_ips          TEXT[] NOT NULL DEFAULT '{}',
    typical_user_agents  TEXT[] NOT NULL DEFAULT '{}',
    action_counts        JSONB  NOT NULL DEFAULT '{}'::jsonb,
    mean_bytes_out       DOUBLE PRECISION NOT NULL DEFAULT 0,
    stddev_bytes_out     DOUBLE PRECISION NOT NULL DEFAULT 0,
    sample_size          INT NOT NULL DEFAULT 0,
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE incidents (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    triggering_log_id    UUID NOT NULL REFERENCES logs(id),
    user_id              TEXT NOT NULL,
    severity             TEXT NOT NULL DEFAULT 'unknown',
    confidence           DOUBLE PRECISION NOT NULL DEFAULT 0,
    summary              TEXT,
    recommended_action   TEXT,
    reasoning_trace      JSONB NOT NULL DEFAULT '[]'::jsonb,
    status               TEXT NOT NULL DEFAULT 'open',
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at         TIMESTAMPTZ
);

CREATE INDEX incidents_user_idx     ON incidents (user_id);
CREATE INDEX incidents_created_idx  ON incidents (created_at DESC);
CREATE INDEX incidents_severity_idx ON incidents (severity);
