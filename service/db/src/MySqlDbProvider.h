#ifndef DB_SERVICE_MY_SQL_DB_PROVIDER_H
#define DB_SERVICE_MY_SQL_DB_PROVIDER_H

#include "DbProvider.h"

#include <expected>
#include <optional>
#include <string>
#include <vector>

namespace galay::mysql {
class MysqlClient;
}

class MySqlDbProvider final : public DbProvider {
public:
    MySqlDbProvider();

    std::expected<DbUserRecord, std::string> createUser(const DbCreateUserInput& input) override;
    std::expected<DbUserRecord, std::string> getUserByUsername(const std::string& username) override;
    std::expected<DbUserRecord, std::string> getUserById(std::uint64_t user_id) override;
    std::expected<DbUserRecord, std::string> updateUser(std::uint64_t user_id,
                                                        const DbUpdateUserInput& input) override;
    std::expected<DbUserRecord, std::string> updatePassword(std::uint64_t user_id,
                                                            const DbUpdatePasswordInput& input) override;
    std::expected<DbUserRecord, std::string> updateNotifications(
        std::uint64_t user_id,
        const DbUpdateNotificationsInput& input) override;
    std::expected<bool, std::string> deleteUser(std::uint64_t user_id) override;

    std::expected<DbDocumentRecord, std::string> upsertDocument(const DbUpsertDocumentInput& input) override;
    std::expected<DbDocumentRecord, std::string> getDocument(
        const std::string& project,
        const std::string& relative_path) override;
    std::expected<std::vector<DbDocumentRecord>, std::string> listDocuments(
        const DbListDocumentsInput& input) override;
    std::expected<DbDocumentRecord, std::string> markDocumentDeleted(
        const std::string& project,
        const std::string& relative_path) override;

    std::expected<DbIndexJobRecord, std::string> createIndexJob(const DbCreateIndexJobInput& input) override;
    std::expected<std::optional<DbIndexJobRecord>, std::string> fetchNextPendingIndexJob() override;
    std::expected<DbIndexJobRecord, std::string> getIndexJobById(std::uint64_t job_id) override;
    std::expected<DbIndexJobRecord, std::string> finishIndexJobSuccess(std::uint64_t job_id) override;
    std::expected<DbIndexJobRecord, std::string> finishIndexJobFailed(
        std::uint64_t job_id,
        const std::string& error_message) override;

    std::expected<DbIndexStateRecord, std::string> getIndexState() override;

private:
    struct ConnectionConfig {
        std::string m_host = "127.0.0.1";
        std::uint16_t m_port = 3306;
        std::string m_username = "root";
        std::string m_password = "password";
        std::string m_database = "gblob";
        std::string m_charset = "utf8mb4";
        std::uint32_t m_connect_timeout_ms = 5000;
    };

    static std::string getEnvOrDefault(const char* key, const std::string& fallback);
    static std::uint16_t getPortFromEnv(const char* key, std::uint16_t fallback);

    std::expected<void, std::string> connect(galay::mysql::MysqlClient& session) const;
    std::expected<void, std::string> execute(galay::mysql::MysqlClient& session, const std::string& sql) const;
    std::string sqlQuote(const std::string& value) const;
    std::expected<DbUserRecord, std::string> selectUserByClause(const std::string& clause) const;

    std::expected<DbDocumentRecord, std::string> selectDocumentByClause(const std::string& clause) const;
    std::expected<DbIndexJobRecord, std::string> selectIndexJobByClause(const std::string& clause) const;
    std::expected<void, std::string> ensureIndexStateRow(galay::mysql::MysqlClient& session) const;

    ConnectionConfig m_config;
};

#endif  // DB_SERVICE_MY_SQL_DB_PROVIDER_H
