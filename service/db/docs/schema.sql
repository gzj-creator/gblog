CREATE DATABASE IF NOT EXISTS gblob CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE gblob;

CREATE TABLE IF NOT EXISTS users (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    username VARCHAR(64) NOT NULL,
    email VARCHAR(255) NOT NULL,
    display_name VARCHAR(128) NOT NULL DEFAULT '',
    bio TEXT NOT NULL,
    website VARCHAR(255) NOT NULL DEFAULT '',
    github VARCHAR(255) NOT NULL DEFAULT '',
    password_salt VARCHAR(64) NOT NULL,
    password_hash VARCHAR(128) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uk_users_username (username),
    UNIQUE KEY uk_users_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS user_notification_settings (
    user_id BIGINT UNSIGNED NOT NULL,
    email_notifications TINYINT(1) NOT NULL DEFAULT 1,
    new_post_notifications TINYINT(1) NOT NULL DEFAULT 1,
    comment_reply_notifications TINYINT(1) NOT NULL DEFAULT 1,
    release_notifications TINYINT(1) NOT NULL DEFAULT 1,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id),
    CONSTRAINT fk_user_notification_settings_user
      FOREIGN KEY (user_id) REFERENCES users(id)
      ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS documents (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    project VARCHAR(64) NOT NULL,
    relative_path VARCHAR(512) NOT NULL,
    sha256 VARCHAR(128) NOT NULL DEFAULT '',
    size_bytes BIGINT UNSIGNED NOT NULL DEFAULT 0,
    doc_version BIGINT UNSIGNED NOT NULL DEFAULT 1,
    is_deleted TINYINT(1) NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uk_documents_project_path (project, relative_path),
    KEY idx_documents_project_deleted (project, is_deleted),
    KEY idx_documents_updated_at (updated_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS index_jobs (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    job_type VARCHAR(32) NOT NULL DEFAULT 'reindex',
    project VARCHAR(64) NOT NULL DEFAULT '',
    relative_path VARCHAR(512) NOT NULL DEFAULT '',
    document_id BIGINT UNSIGNED NULL,
    status VARCHAR(16) NOT NULL DEFAULT 'pending',
    attempts INT UNSIGNED NOT NULL DEFAULT 0,
    trigger_source VARCHAR(32) NOT NULL DEFAULT 'admin',
    payload_json TEXT NOT NULL,
    error_message TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    started_at TIMESTAMP NULL DEFAULT NULL,
    finished_at TIMESTAMP NULL DEFAULT NULL,
    PRIMARY KEY (id),
    KEY idx_index_jobs_status_created (status, created_at),
    KEY idx_index_jobs_project_path (project, relative_path),
    KEY idx_index_jobs_document_id (document_id),
    CONSTRAINT fk_index_jobs_document_id
      FOREIGN KEY (document_id) REFERENCES documents(id)
      ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS index_state (
    id TINYINT UNSIGNED NOT NULL,
    current_version BIGINT UNSIGNED NOT NULL DEFAULT 0,
    last_success_job_id BIGINT UNSIGNED NULL,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    CONSTRAINT fk_index_state_last_success_job
      FOREIGN KEY (last_success_job_id) REFERENCES index_jobs(id)
      ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT INTO index_state (id, current_version, last_success_job_id)
VALUES (1, 0, NULL)
ON DUPLICATE KEY UPDATE id = id;
