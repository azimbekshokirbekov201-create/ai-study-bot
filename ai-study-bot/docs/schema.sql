BEGIN;

CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL, 
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> f9244853068d

CREATE TABLE achievements (
    id BIGSERIAL NOT NULL, 
    code VARCHAR(50) NOT NULL, 
    title_uz VARCHAR(160) NOT NULL, 
    title_en VARCHAR(160) NOT NULL, 
    CONSTRAINT pk_achievements PRIMARY KEY (id), 
    CONSTRAINT uq_achievements_code UNIQUE (code)
);

CREATE TABLE admin_audit_logs (
    id BIGSERIAL NOT NULL, 
    actor VARCHAR(100) NOT NULL, 
    action VARCHAR(60) NOT NULL, 
    target VARCHAR(100) NOT NULL, 
    details JSONB NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    CONSTRAINT pk_admin_audit_logs PRIMARY KEY (id)
);

CREATE INDEX ix_admin_audit_logs_actor ON admin_audit_logs (actor);

CREATE INDEX ix_admin_audit_logs_created_at ON admin_audit_logs (created_at);

CREATE TABLE application_errors (
    id UUID NOT NULL, 
    error_type VARCHAR(100) NOT NULL, 
    location VARCHAR(200) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    CONSTRAINT pk_application_errors PRIMARY KEY (id)
);

CREATE INDEX ix_application_errors_created_at ON application_errors (created_at);

CREATE TABLE broadcasts (
    id UUID NOT NULL, 
    actor VARCHAR(100) NOT NULL, 
    text VARCHAR(3500) NOT NULL, 
    status VARCHAR(20) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    CONSTRAINT pk_broadcasts PRIMARY KEY (id)
);

CREATE TABLE global_ai_usage (
    day DATE NOT NULL, 
    reserved_tokens INTEGER NOT NULL, 
    CONSTRAINT pk_global_ai_usage PRIMARY KEY (day)
);

CREATE TABLE subjects (
    id BIGSERIAL NOT NULL, 
    code VARCHAR(50) NOT NULL, 
    title_uz VARCHAR(160) NOT NULL, 
    title_en VARCHAR(160) NOT NULL, 
    active BOOLEAN NOT NULL, 
    CONSTRAINT pk_subjects PRIMARY KEY (id), 
    CONSTRAINT uq_subjects_code UNIQUE (code)
);

CREATE TABLE update_receipts (
    update_id BIGSERIAL NOT NULL, 
    processed_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    CONSTRAINT pk_update_receipts PRIMARY KEY (update_id)
);

CREATE INDEX ix_update_receipts_processed_at ON update_receipts (processed_at);

CREATE TABLE users (
    id BIGSERIAL NOT NULL, 
    telegram_id BIGINT NOT NULL, 
    display_name VARCHAR(128) NOT NULL, 
    username VARCHAR(64), 
    language VARCHAR(2) NOT NULL, 
    goals VARCHAR(1000) NOT NULL, 
    cefr_level VARCHAR(2) NOT NULL, 
    registered_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    last_seen_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    state VARCHAR(40) NOT NULL, 
    state_data JSONB NOT NULL, 
    rate_window TIMESTAMP WITH TIME ZONE NOT NULL, 
    rate_count INTEGER NOT NULL, 
    announcements_enabled BOOLEAN NOT NULL, 
    blocked BOOLEAN NOT NULL, 
    CONSTRAINT pk_users PRIMARY KEY (id), 
    CONSTRAINT ck_users_language CHECK (language IN ('uz', 'en')), 
    CONSTRAINT uq_users_telegram_id UNIQUE (telegram_id)
);

CREATE INDEX ix_users_last_seen_at ON users (last_seen_at);

CREATE TABLE ai_conversations (
    id BIGSERIAL NOT NULL, 
    user_id BIGINT NOT NULL, 
    mode VARCHAR(30) NOT NULL, 
    role VARCHAR(12) NOT NULL, 
    content TEXT NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    CONSTRAINT pk_ai_conversations PRIMARY KEY (id), 
    CONSTRAINT fk_ai_conversations_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX ix_ai_history ON ai_conversations (user_id, mode, created_at);

CREATE TABLE ai_requests (
    id UUID NOT NULL, 
    user_id BIGINT NOT NULL, 
    day DATE NOT NULL, 
    kind VARCHAR(30) NOT NULL, 
    status VARCHAR(16) NOT NULL, 
    reserved_tokens INTEGER NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    CONSTRAINT pk_ai_requests PRIMARY KEY (id), 
    CONSTRAINT fk_ai_requests_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX ix_ai_requests_user_id ON ai_requests (user_id);

CREATE TABLE ai_usage (
    user_id BIGINT NOT NULL, 
    day DATE NOT NULL, 
    requests INTEGER NOT NULL, 
    reserved_tokens INTEGER NOT NULL, 
    input_tokens INTEGER NOT NULL, 
    output_tokens INTEGER NOT NULL, 
    CONSTRAINT pk_ai_usage PRIMARY KEY (user_id, day), 
    CONSTRAINT fk_ai_usage_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE broadcast_deliveries (
    broadcast_id UUID NOT NULL, 
    user_id BIGINT NOT NULL, 
    status VARCHAR(16) NOT NULL, 
    attempts INTEGER NOT NULL, 
    CONSTRAINT pk_broadcast_deliveries PRIMARY KEY (broadcast_id, user_id), 
    CONSTRAINT fk_broadcast_deliveries_broadcast_id_broadcasts FOREIGN KEY(broadcast_id) REFERENCES broadcasts (id) ON DELETE CASCADE, 
    CONSTRAINT fk_broadcast_deliveries_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX ix_broadcast_deliveries_status ON broadcast_deliveries (status);

CREATE TABLE lessons (
    id BIGSERIAL NOT NULL, 
    subject_id BIGINT NOT NULL, 
    code VARCHAR(100) NOT NULL, 
    topic VARCHAR(80) NOT NULL, 
    level VARCHAR(2), 
    title_uz VARCHAR(160) NOT NULL, 
    title_en VARCHAR(160) NOT NULL, 
    body_uz TEXT NOT NULL, 
    body_en TEXT NOT NULL, 
    audio_script TEXT, 
    premium_only BOOLEAN NOT NULL, 
    active BOOLEAN NOT NULL, 
    CONSTRAINT pk_lessons PRIMARY KEY (id), 
    CONSTRAINT fk_lessons_subject_id_subjects FOREIGN KEY(subject_id) REFERENCES subjects (id) ON DELETE RESTRICT, 
    CONSTRAINT uq_lessons_code UNIQUE (code)
);

CREATE INDEX ix_lessons_subject_id ON lessons (subject_id);

CREATE INDEX ix_lessons_topic ON lessons (topic);

CREATE TABLE payments (
    id UUID NOT NULL, 
    user_id BIGINT NOT NULL, 
    provider VARCHAR(30) NOT NULL, 
    invoice_payload VARCHAR(128) NOT NULL, 
    currency VARCHAR(3) NOT NULL, 
    amount INTEGER NOT NULL, 
    duration_days INTEGER NOT NULL, 
    status VARCHAR(12) NOT NULL, 
    provider_charge_id VARCHAR(256), 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    paid_at TIMESTAMP WITH TIME ZONE, 
    CONSTRAINT pk_payments PRIMARY KEY (id), 
    CONSTRAINT ck_payments_status CHECK (status IN ('pending','paid','refunded')), 
    CONSTRAINT ck_payments_amount CHECK (amount > 0), 
    CONSTRAINT fk_payments_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
    CONSTRAINT uq_payments_invoice_payload UNIQUE (invoice_payload), 
    CONSTRAINT uq_payments_provider_charge_id UNIQUE (provider_charge_id)
);

CREATE INDEX ix_payments_user_id ON payments (user_id);

CREATE TABLE quiz_attempts (
    id UUID NOT NULL, 
    user_id BIGINT NOT NULL, 
    subject_id BIGINT, 
    challenge_key VARCHAR(100), 
    kind VARCHAR(20) NOT NULL, 
    language VARCHAR(2) NOT NULL, 
    status VARCHAR(12) NOT NULL, 
    question_count INTEGER NOT NULL, 
    correct_count INTEGER NOT NULL, 
    points INTEGER NOT NULL, 
    current_position INTEGER NOT NULL, 
    started_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    deadline TIMESTAMP WITH TIME ZONE NOT NULL, 
    completed_at TIMESTAMP WITH TIME ZONE, 
    CONSTRAINT pk_quiz_attempts PRIMARY KEY (id), 
    CONSTRAINT ck_quiz_attempts_status CHECK (status IN ('active','completed','expired','abandoned')), 
    CONSTRAINT fk_quiz_attempts_subject_id_subjects FOREIGN KEY(subject_id) REFERENCES subjects (id) ON DELETE SET NULL, 
    CONSTRAINT fk_quiz_attempts_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
    CONSTRAINT uq_quiz_attempts_user_id_challenge_key UNIQUE (user_id, challenge_key)
);

CREATE INDEX ix_attempt_user_started ON quiz_attempts (user_id, started_at);

CREATE TABLE reward_events (
    id BIGSERIAL NOT NULL, 
    user_id BIGINT NOT NULL, 
    source_key VARCHAR(150) NOT NULL, 
    points INTEGER NOT NULL, 
    awarded_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    CONSTRAINT pk_reward_events PRIMARY KEY (id), 
    CONSTRAINT fk_reward_events_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
    CONSTRAINT uq_reward_events_user_id_source_key UNIQUE (user_id, source_key)
);

CREATE INDEX ix_rewards_period ON reward_events (awarded_at, user_id);

CREATE TABLE user_achievements (
    user_id BIGINT NOT NULL, 
    achievement_id BIGINT NOT NULL, 
    awarded_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    CONSTRAINT pk_user_achievements PRIMARY KEY (user_id, achievement_id), 
    CONSTRAINT fk_user_achievements_achievement_id_achievements FOREIGN KEY(achievement_id) REFERENCES achievements (id) ON DELETE CASCADE, 
    CONSTRAINT fk_user_achievements_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE user_progress (
    id BIGSERIAL NOT NULL, 
    user_id BIGINT NOT NULL, 
    subject_id BIGINT NOT NULL, 
    topic VARCHAR(80) NOT NULL, 
    level VARCHAR(2) NOT NULL, 
    answered INTEGER NOT NULL, 
    correct INTEGER NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    CONSTRAINT pk_user_progress PRIMARY KEY (id), 
    CONSTRAINT fk_user_progress_subject_id_subjects FOREIGN KEY(subject_id) REFERENCES subjects (id) ON DELETE CASCADE, 
    CONSTRAINT fk_user_progress_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
    CONSTRAINT uq_user_progress_user_id_subject_id_topic_level UNIQUE (user_id, subject_id, topic, level)
);

CREATE TABLE questions (
    id BIGSERIAL NOT NULL, 
    code VARCHAR(100) NOT NULL, 
    subject_id BIGINT NOT NULL, 
    lesson_id BIGINT, 
    topic VARCHAR(80) NOT NULL, 
    level VARCHAR(2), 
    difficulty INTEGER NOT NULL, 
    prompt_uz TEXT NOT NULL, 
    prompt_en TEXT NOT NULL, 
    correct_option INTEGER NOT NULL, 
    explanation_uz TEXT NOT NULL, 
    explanation_en TEXT NOT NULL, 
    active BOOLEAN NOT NULL, 
    premium_only BOOLEAN NOT NULL, 
    CONSTRAINT pk_questions PRIMARY KEY (id), 
    CONSTRAINT ck_questions_correct_option CHECK (correct_option BETWEEN 0 AND 3), 
    CONSTRAINT ck_questions_difficulty CHECK (difficulty BETWEEN 1 AND 3), 
    CONSTRAINT fk_questions_lesson_id_lessons FOREIGN KEY(lesson_id) REFERENCES lessons (id) ON DELETE SET NULL, 
    CONSTRAINT fk_questions_subject_id_subjects FOREIGN KEY(subject_id) REFERENCES subjects (id) ON DELETE RESTRICT, 
    CONSTRAINT uq_questions_code UNIQUE (code)
);

CREATE INDEX ix_question_selection ON questions (subject_id, topic, level, active);

CREATE TABLE subscriptions (
    id BIGSERIAL NOT NULL, 
    user_id BIGINT NOT NULL, 
    payment_id UUID, 
    source VARCHAR(20) NOT NULL, 
    starts_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    ends_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    revoked_at TIMESTAMP WITH TIME ZONE, 
    CONSTRAINT pk_subscriptions PRIMARY KEY (id), 
    CONSTRAINT fk_subscriptions_payment_id_payments FOREIGN KEY(payment_id) REFERENCES payments (id) ON DELETE RESTRICT, 
    CONSTRAINT fk_subscriptions_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
    CONSTRAINT uq_subscriptions_payment_id UNIQUE (payment_id)
);

CREATE INDEX ix_subscription_entitlement ON subscriptions (user_id, ends_at, revoked_at);

CREATE TABLE attempt_questions (
    attempt_id UUID NOT NULL, 
    position INTEGER NOT NULL, 
    question_id BIGINT, 
    subject_id BIGINT NOT NULL, 
    topic VARCHAR(80) NOT NULL, 
    level VARCHAR(2), 
    prompt TEXT NOT NULL, 
    options JSONB NOT NULL, 
    explanation TEXT NOT NULL, 
    correct_option INTEGER NOT NULL, 
    difficulty INTEGER NOT NULL, 
    CONSTRAINT pk_attempt_questions PRIMARY KEY (attempt_id, position), 
    CONSTRAINT fk_attempt_questions_attempt_id_quiz_attempts FOREIGN KEY(attempt_id) REFERENCES quiz_attempts (id) ON DELETE CASCADE, 
    CONSTRAINT fk_attempt_questions_question_id_questions FOREIGN KEY(question_id) REFERENCES questions (id) ON DELETE SET NULL, 
    CONSTRAINT fk_attempt_questions_subject_id_subjects FOREIGN KEY(subject_id) REFERENCES subjects (id) ON DELETE RESTRICT
);

CREATE TABLE question_options (
    question_id BIGINT NOT NULL, 
    position INTEGER NOT NULL, 
    text_uz VARCHAR(500) NOT NULL, 
    text_en VARCHAR(500) NOT NULL, 
    CONSTRAINT pk_question_options PRIMARY KEY (question_id, position), 
    CONSTRAINT ck_question_options_position CHECK (position BETWEEN 0 AND 3), 
    CONSTRAINT fk_question_options_question_id_questions FOREIGN KEY(question_id) REFERENCES questions (id) ON DELETE CASCADE
);

CREATE TABLE quiz_answers (
    attempt_id UUID NOT NULL, 
    position INTEGER NOT NULL, 
    selected_option INTEGER NOT NULL, 
    correct BOOLEAN NOT NULL, 
    points INTEGER NOT NULL, 
    answered_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    CONSTRAINT pk_quiz_answers PRIMARY KEY (attempt_id, position), 
    CONSTRAINT ck_quiz_answers_selected_option CHECK (selected_option BETWEEN 0 AND 3), 
    CONSTRAINT fk_quiz_answers_attempt_id_position_attempt_questions FOREIGN KEY(attempt_id, position) REFERENCES attempt_questions (attempt_id, position) ON DELETE CASCADE
);

INSERT INTO alembic_version (version_num) VALUES ('f9244853068d') RETURNING alembic_version.version_num;

-- Running upgrade f9244853068d -> ed3a120fe282

ALTER TABLE payments ADD COLUMN terms_version VARCHAR(40);

ALTER TABLE payments ADD COLUMN terms_accepted_at TIMESTAMP WITH TIME ZONE;

UPDATE alembic_version SET version_num='ed3a120fe282' WHERE alembic_version.version_num = 'f9244853068d';

COMMIT;

