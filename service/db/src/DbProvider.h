#ifndef DB_SERVICE_DB_PROVIDER_H
#define DB_SERVICE_DB_PROVIDER_H

#include <cstdint>
#include <expected>
#include <optional>
#include <string>
#include <vector>

struct DbUserRecord {
    std::uint64_t m_id = 0;
    std::string m_username;
    std::string m_email;
    std::string m_display_name;
    std::string m_bio;
    std::string m_website;
    std::string m_github;
    std::string m_password_salt;
    std::string m_password_hash;
    bool m_email_notifications = true;
    bool m_new_post_notifications = true;
    bool m_comment_reply_notifications = true;
    bool m_release_notifications = true;
};

struct DbCreateUserInput {
    std::string m_username;
    std::string m_email;
    std::string m_display_name;
    std::string m_bio;
    std::string m_website;
    std::string m_github;
    std::string m_password_salt;
    std::string m_password_hash;
};

struct DbUpdateUserInput {
    std::optional<std::string> m_email;
    std::optional<std::string> m_display_name;
    std::optional<std::string> m_bio;
    std::optional<std::string> m_website;
    std::optional<std::string> m_github;
};

struct DbUpdatePasswordInput {
    std::string m_password_salt;
    std::string m_password_hash;
};

struct DbUpdateNotificationsInput {
    std::optional<bool> m_email_notifications;
    std::optional<bool> m_new_post_notifications;
    std::optional<bool> m_comment_reply_notifications;
    std::optional<bool> m_release_notifications;
};

struct DbDocumentRecord {
    std::uint64_t m_id = 0;
    std::string m_project;
    std::string m_relative_path;
    std::string m_sha256;
    std::uint64_t m_size_bytes = 0;
    std::uint64_t m_doc_version = 0;
    bool m_is_deleted = false;
    std::string m_created_at;
    std::string m_updated_at;
};

struct DbUpsertDocumentInput {
    std::string m_project;
    std::string m_relative_path;
    std::string m_sha256;
    std::uint64_t m_size_bytes = 0;
    std::optional<std::uint64_t> m_doc_version;
    std::optional<bool> m_is_deleted;
};

struct DbListDocumentsInput {
    std::optional<std::string> m_project;
    bool m_include_deleted = false;
};

struct DbIndexJobRecord {
    std::uint64_t m_id = 0;
    std::string m_job_type;
    std::string m_project;
    std::string m_relative_path;
    std::optional<std::uint64_t> m_document_id;
    std::string m_status;
    std::uint32_t m_attempts = 0;
    std::string m_trigger_source;
    std::string m_payload_json;
    std::string m_error_message;
    std::string m_created_at;
    std::string m_updated_at;
    std::string m_started_at;
    std::string m_finished_at;
};

struct DbCreateIndexJobInput {
    std::string m_job_type = "reindex";
    std::string m_project;
    std::string m_relative_path;
    std::optional<std::uint64_t> m_document_id;
    std::string m_trigger_source = "admin";
    std::string m_payload_json = "{}";
};

struct DbIndexStateRecord {
    std::uint64_t m_current_version = 0;
    std::optional<std::uint64_t> m_last_success_job_id;
    std::string m_updated_at;
};

class DbProvider {
public:
    virtual ~DbProvider() = default;

    virtual std::expected<DbUserRecord, std::string> createUser(const DbCreateUserInput& input) = 0;
    virtual std::expected<DbUserRecord, std::string> getUserByUsername(const std::string& username) = 0;
    virtual std::expected<DbUserRecord, std::string> getUserById(std::uint64_t user_id) = 0;
    virtual std::expected<DbUserRecord, std::string> updateUser(std::uint64_t user_id,
                                                                const DbUpdateUserInput& input) = 0;
    virtual std::expected<DbUserRecord, std::string> updatePassword(std::uint64_t user_id,
                                                                    const DbUpdatePasswordInput& input) = 0;
    virtual std::expected<DbUserRecord, std::string> updateNotifications(
        std::uint64_t user_id,
        const DbUpdateNotificationsInput& input) = 0;
    virtual std::expected<bool, std::string> deleteUser(std::uint64_t user_id) = 0;

    virtual std::expected<DbDocumentRecord, std::string> upsertDocument(const DbUpsertDocumentInput& input) = 0;
    virtual std::expected<DbDocumentRecord, std::string> getDocument(
        const std::string& project,
        const std::string& relative_path) = 0;
    virtual std::expected<std::vector<DbDocumentRecord>, std::string> listDocuments(
        const DbListDocumentsInput& input) = 0;
    virtual std::expected<DbDocumentRecord, std::string> markDocumentDeleted(
        const std::string& project,
        const std::string& relative_path) = 0;

    virtual std::expected<DbIndexJobRecord, std::string> createIndexJob(
        const DbCreateIndexJobInput& input) = 0;
    virtual std::expected<std::optional<DbIndexJobRecord>, std::string> fetchNextPendingIndexJob() = 0;
    virtual std::expected<DbIndexJobRecord, std::string> getIndexJobById(std::uint64_t job_id) = 0;
    virtual std::expected<DbIndexJobRecord, std::string> finishIndexJobSuccess(std::uint64_t job_id) = 0;
    virtual std::expected<DbIndexJobRecord, std::string> finishIndexJobFailed(
        std::uint64_t job_id,
        const std::string& error_message) = 0;

    virtual std::expected<DbIndexStateRecord, std::string> getIndexState() = 0;
};

#endif  // DB_SERVICE_DB_PROVIDER_H
