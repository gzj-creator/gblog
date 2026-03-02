#include "MySqlDbProvider.h"

#include "galay-mysql/base/MysqlConfig.h"
#include "galay-mysql/sync/MysqlClient.h"

#include <cstdlib>
#include <optional>
#include <string>

using galay::mysql::MysqlClient;
using galay::mysql::MysqlConfig;

namespace {

bool parseMysqlBool(const std::string& raw)
{
    return !(raw == "0" || raw == "false" || raw == "FALSE");
}

std::uint64_t parseUint64OrDefault(const std::string& raw, std::uint64_t fallback)
{
    try {
        return static_cast<std::uint64_t>(std::stoull(raw));
    } catch (...) {
        return fallback;
    }
}

std::uint32_t parseUint32OrDefault(const std::string& raw, std::uint32_t fallback)
{
    try {
        return static_cast<std::uint32_t>(std::stoul(raw));
    } catch (...) {
        return fallback;
    }
}

}  // namespace

std::string MySqlDbProvider::getEnvOrDefault(const char* key, const std::string& fallback)
{
    const char* raw = std::getenv(key);
    if (raw == nullptr) {
        return fallback;
    }
    const std::string value(raw);
    return value.empty() ? fallback : value;
}

std::uint16_t MySqlDbProvider::getPortFromEnv(const char* key, std::uint16_t fallback)
{
    const char* raw = std::getenv(key);
    if (raw == nullptr) {
        return fallback;
    }

    try {
        const int value = std::stoi(raw);
        if (value <= 0 || value > 65535) {
            return fallback;
        }
        return static_cast<std::uint16_t>(value);
    } catch (...) {
        return fallback;
    }
}

MySqlDbProvider::MySqlDbProvider()
{
    m_config.m_host = getEnvOrDefault("DB_MYSQL_HOST", "127.0.0.1");
    m_config.m_port = getPortFromEnv("DB_MYSQL_PORT", 3306);
    m_config.m_username = getEnvOrDefault("DB_MYSQL_USER", "root");
    m_config.m_password = getEnvOrDefault("DB_MYSQL_PASSWORD", "password");
    m_config.m_database = getEnvOrDefault("DB_MYSQL_DATABASE", "gblob");
    m_config.m_charset = getEnvOrDefault("DB_MYSQL_CHARSET", "utf8mb4");
}

std::expected<void, std::string> MySqlDbProvider::connect(MysqlClient& session) const
{
    MysqlConfig config;
    config.host = m_config.m_host;
    config.port = m_config.m_port;
    config.username = m_config.m_username;
    config.password = m_config.m_password;
    config.database = m_config.m_database;
    config.charset = m_config.m_charset;
    config.connect_timeout_ms = m_config.m_connect_timeout_ms;

    auto conn = session.connect(config);
    if (!conn) {
        return std::unexpected("mysql connect failed: " + conn.error().message());
    }
    return {};
}

std::expected<void, std::string> MySqlDbProvider::execute(MysqlClient& session, const std::string& sql) const
{
    auto res = session.query(sql);
    if (!res) {
        return std::unexpected("mysql query failed: " + res.error().message());
    }
    return {};
}

std::string MySqlDbProvider::sqlQuote(const std::string& value) const
{
    std::string out;
    out.reserve(value.size() + 2);
    out.push_back('\'');
    for (const char ch : value) {
        if (ch == '\\' || ch == '\'') {
            out.push_back('\\');
        }
        out.push_back(ch);
    }
    out.push_back('\'');
    return out;
}

std::expected<DbUserRecord, std::string> MySqlDbProvider::selectUserByClause(const std::string& clause) const
{
    MysqlClient session;
    auto connRes = connect(session);
    if (!connRes) {
        return std::unexpected(connRes.error());
    }

    const std::string sql =
        "SELECT u.id,u.username,u.email,u.display_name,u.bio,u.website,u.github,"
        "u.password_salt,u.password_hash,"
        "COALESCE(n.email_notifications,1),"
        "COALESCE(n.new_post_notifications,1),"
        "COALESCE(n.comment_reply_notifications,1),"
        "COALESCE(n.release_notifications,1) "
        "FROM users u "
        "LEFT JOIN user_notification_settings n ON n.user_id=u.id " +
        clause +
        " LIMIT 1";

    auto queryRes = session.query(sql);
    if (!queryRes) {
        session.close();
        return std::unexpected("mysql query failed: " + queryRes.error().message());
    }

    if (queryRes->rowCount() == 0) {
        session.close();
        return std::unexpected("user not found");
    }

    const auto& row = queryRes->row(0);
    DbUserRecord user;
    user.m_id = parseUint64OrDefault(row.getString(0, "0"), 0);
    user.m_username = row.getString(1, "");
    user.m_email = row.getString(2, "");
    user.m_display_name = row.getString(3, "");
    user.m_bio = row.getString(4, "");
    user.m_website = row.getString(5, "");
    user.m_github = row.getString(6, "");
    user.m_password_salt = row.getString(7, "");
    user.m_password_hash = row.getString(8, "");
    user.m_email_notifications = parseMysqlBool(row.getString(9, "1"));
    user.m_new_post_notifications = parseMysqlBool(row.getString(10, "1"));
    user.m_comment_reply_notifications = parseMysqlBool(row.getString(11, "1"));
    user.m_release_notifications = parseMysqlBool(row.getString(12, "1"));

    session.close();
    return user;
}

std::expected<DbDocumentRecord, std::string> MySqlDbProvider::selectDocumentByClause(const std::string& clause) const
{
    MysqlClient session;
    auto connRes = connect(session);
    if (!connRes) {
        return std::unexpected(connRes.error());
    }

    const std::string sql =
        "SELECT id,project,relative_path,sha256,size_bytes,doc_version,is_deleted,"
        "DATE_FORMAT(created_at,'%Y-%m-%d %H:%i:%s'),"
        "DATE_FORMAT(updated_at,'%Y-%m-%d %H:%i:%s') "
        "FROM documents " +
        clause +
        " LIMIT 1";

    auto queryRes = session.query(sql);
    if (!queryRes) {
        session.close();
        return std::unexpected("mysql query failed: " + queryRes.error().message());
    }
    if (queryRes->rowCount() == 0) {
        session.close();
        return std::unexpected("document not found");
    }

    const auto& row = queryRes->row(0);
    DbDocumentRecord doc;
    doc.m_id = parseUint64OrDefault(row.getString(0, "0"), 0);
    doc.m_project = row.getString(1, "");
    doc.m_relative_path = row.getString(2, "");
    doc.m_sha256 = row.getString(3, "");
    doc.m_size_bytes = parseUint64OrDefault(row.getString(4, "0"), 0);
    doc.m_doc_version = parseUint64OrDefault(row.getString(5, "0"), 0);
    doc.m_is_deleted = parseMysqlBool(row.getString(6, "0"));
    doc.m_created_at = row.getString(7, "");
    doc.m_updated_at = row.getString(8, "");

    session.close();
    return doc;
}

std::expected<DbIndexJobRecord, std::string> MySqlDbProvider::selectIndexJobByClause(
    const std::string& clause) const
{
    MysqlClient session;
    auto connRes = connect(session);
    if (!connRes) {
        return std::unexpected(connRes.error());
    }

    const std::string sql =
        "SELECT id,job_type,project,relative_path,document_id,status,attempts,trigger_source,payload_json,"
        "COALESCE(error_message,''),"
        "DATE_FORMAT(created_at,'%Y-%m-%d %H:%i:%s'),"
        "DATE_FORMAT(updated_at,'%Y-%m-%d %H:%i:%s'),"
        "COALESCE(DATE_FORMAT(started_at,'%Y-%m-%d %H:%i:%s'),''),"
        "COALESCE(DATE_FORMAT(finished_at,'%Y-%m-%d %H:%i:%s'),'') "
        "FROM index_jobs " +
        clause +
        " LIMIT 1";

    auto queryRes = session.query(sql);
    if (!queryRes) {
        session.close();
        return std::unexpected("mysql query failed: " + queryRes.error().message());
    }
    if (queryRes->rowCount() == 0) {
        session.close();
        return std::unexpected("index job not found");
    }

    const auto& row = queryRes->row(0);
    DbIndexJobRecord job;
    job.m_id = parseUint64OrDefault(row.getString(0, "0"), 0);
    job.m_job_type = row.getString(1, "");
    job.m_project = row.getString(2, "");
    job.m_relative_path = row.getString(3, "");
    const std::string docIdRaw = row.getString(4, "");
    if (!docIdRaw.empty()) {
        job.m_document_id = parseUint64OrDefault(docIdRaw, 0);
    }
    job.m_status = row.getString(5, "");
    job.m_attempts = parseUint32OrDefault(row.getString(6, "0"), 0);
    job.m_trigger_source = row.getString(7, "");
    job.m_payload_json = row.getString(8, "{}");
    job.m_error_message = row.getString(9, "");
    job.m_created_at = row.getString(10, "");
    job.m_updated_at = row.getString(11, "");
    job.m_started_at = row.getString(12, "");
    job.m_finished_at = row.getString(13, "");

    session.close();
    return job;
}

std::expected<void, std::string> MySqlDbProvider::ensureIndexStateRow(MysqlClient& session) const
{
    return execute(session,
                   "INSERT INTO index_state (id,current_version,last_success_job_id) "
                   "VALUES (1,0,NULL) ON DUPLICATE KEY UPDATE id=id");
}

std::expected<DbUserRecord, std::string> MySqlDbProvider::createUser(const DbCreateUserInput& input)
{
    MysqlClient session;
    auto connRes = connect(session);
    if (!connRes) {
        return std::unexpected(connRes.error());
    }

    const std::string insertUserSql =
        "INSERT INTO users (username,email,display_name,bio,website,github,password_salt,password_hash) VALUES (" +
        sqlQuote(input.m_username) + "," +
        sqlQuote(input.m_email) + "," +
        sqlQuote(input.m_display_name) + "," +
        sqlQuote(input.m_bio) + "," +
        sqlQuote(input.m_website) + "," +
        sqlQuote(input.m_github) + "," +
        sqlQuote(input.m_password_salt) + "," +
        sqlQuote(input.m_password_hash) + ")";

    auto execRes = execute(session, insertUserSql);
    if (!execRes) {
        session.close();
        return std::unexpected(execRes.error());
    }

    auto idRes = session.query("SELECT LAST_INSERT_ID()");
    if (!idRes) {
        session.close();
        return std::unexpected("mysql query failed: " + idRes.error().message());
    }

    if (idRes->rowCount() == 0) {
        session.close();
        return std::unexpected("failed to fetch last insert id");
    }

    const auto userId = parseUint64OrDefault(idRes->row(0).getString(0, "0"), 0);

    const std::string initSettingsSql =
        "INSERT INTO user_notification_settings (user_id,email_notifications,new_post_notifications,"
        "comment_reply_notifications,release_notifications) VALUES (" +
        std::to_string(userId) + ",1,1,1,1)";

    execRes = execute(session, initSettingsSql);
    session.close();
    if (!execRes) {
        return std::unexpected(execRes.error());
    }

    return getUserById(userId);
}

std::expected<DbUserRecord, std::string> MySqlDbProvider::getUserByUsername(const std::string& username)
{
    return selectUserByClause("WHERE u.username=" + sqlQuote(username));
}

std::expected<DbUserRecord, std::string> MySqlDbProvider::getUserById(std::uint64_t user_id)
{
    return selectUserByClause("WHERE u.id=" + std::to_string(user_id));
}

std::expected<DbUserRecord, std::string> MySqlDbProvider::updateUser(std::uint64_t user_id,
                                                                     const DbUpdateUserInput& input)
{
    auto currentRes = getUserById(user_id);
    if (!currentRes) {
        return std::unexpected(currentRes.error());
    }

    const DbUserRecord& current = *currentRes;
    const std::string email = input.m_email.value_or(current.m_email);
    const std::string displayName = input.m_display_name.value_or(current.m_display_name);
    const std::string bio = input.m_bio.value_or(current.m_bio);
    const std::string website = input.m_website.value_or(current.m_website);
    const std::string github = input.m_github.value_or(current.m_github);

    MysqlClient session;
    auto connRes = connect(session);
    if (!connRes) {
        return std::unexpected(connRes.error());
    }

    const std::string sql =
        "UPDATE users SET email=" + sqlQuote(email) +
        ",display_name=" + sqlQuote(displayName) +
        ",bio=" + sqlQuote(bio) +
        ",website=" + sqlQuote(website) +
        ",github=" + sqlQuote(github) +
        " WHERE id=" + std::to_string(user_id);

    auto execRes = execute(session, sql);
    session.close();
    if (!execRes) {
        return std::unexpected(execRes.error());
    }

    return getUserById(user_id);
}

std::expected<DbUserRecord, std::string> MySqlDbProvider::updatePassword(
    std::uint64_t user_id,
    const DbUpdatePasswordInput& input)
{
    MysqlClient session;
    auto connRes = connect(session);
    if (!connRes) {
        return std::unexpected(connRes.error());
    }

    const std::string sql =
        "UPDATE users SET password_salt=" + sqlQuote(input.m_password_salt) +
        ",password_hash=" + sqlQuote(input.m_password_hash) +
        " WHERE id=" + std::to_string(user_id);

    auto execRes = execute(session, sql);
    session.close();
    if (!execRes) {
        return std::unexpected(execRes.error());
    }

    return getUserById(user_id);
}

std::expected<DbUserRecord, std::string> MySqlDbProvider::updateNotifications(
    std::uint64_t user_id,
    const DbUpdateNotificationsInput& input)
{
    auto currentRes = getUserById(user_id);
    if (!currentRes) {
        return std::unexpected(currentRes.error());
    }

    const DbUserRecord& current = *currentRes;
    const bool email = input.m_email_notifications.value_or(current.m_email_notifications);
    const bool newPost = input.m_new_post_notifications.value_or(current.m_new_post_notifications);
    const bool commentReply =
        input.m_comment_reply_notifications.value_or(current.m_comment_reply_notifications);
    const bool release = input.m_release_notifications.value_or(current.m_release_notifications);

    MysqlClient session;
    auto connRes = connect(session);
    if (!connRes) {
        return std::unexpected(connRes.error());
    }

    const std::string sql =
        "INSERT INTO user_notification_settings (user_id,email_notifications,new_post_notifications,"
        "comment_reply_notifications,release_notifications) VALUES (" +
        std::to_string(user_id) + "," +
        std::to_string(email ? 1 : 0) + "," +
        std::to_string(newPost ? 1 : 0) + "," +
        std::to_string(commentReply ? 1 : 0) + "," +
        std::to_string(release ? 1 : 0) +
        ") ON DUPLICATE KEY UPDATE "
        "email_notifications=VALUES(email_notifications),"
        "new_post_notifications=VALUES(new_post_notifications),"
        "comment_reply_notifications=VALUES(comment_reply_notifications),"
        "release_notifications=VALUES(release_notifications)";

    auto execRes = execute(session, sql);
    session.close();
    if (!execRes) {
        return std::unexpected(execRes.error());
    }

    return getUserById(user_id);
}

std::expected<bool, std::string> MySqlDbProvider::deleteUser(std::uint64_t user_id)
{
    MysqlClient session;
    auto connRes = connect(session);
    if (!connRes) {
        return std::unexpected(connRes.error());
    }

    const std::string sql = "DELETE FROM users WHERE id=" + std::to_string(user_id);
    auto execRes = execute(session, sql);
    session.close();
    if (!execRes) {
        return std::unexpected(execRes.error());
    }

    return true;
}

std::expected<DbDocumentRecord, std::string> MySqlDbProvider::upsertDocument(const DbUpsertDocumentInput& input)
{
    if (input.m_project.empty() || input.m_relative_path.empty()) {
        return std::unexpected("project/relative_path required");
    }

    std::uint64_t targetVersion = input.m_doc_version.value_or(0);
    if (!input.m_doc_version.has_value()) {
        auto existingRes = getDocument(input.m_project, input.m_relative_path);
        if (existingRes) {
            targetVersion = existingRes->m_doc_version + 1;
        } else {
            targetVersion = 1;
        }
    }

    const bool targetDeleted = input.m_is_deleted.value_or(false);

    MysqlClient session;
    auto connRes = connect(session);
    if (!connRes) {
        return std::unexpected(connRes.error());
    }

    const std::string sql =
        "INSERT INTO documents (project,relative_path,sha256,size_bytes,doc_version,is_deleted) VALUES (" +
        sqlQuote(input.m_project) + "," +
        sqlQuote(input.m_relative_path) + "," +
        sqlQuote(input.m_sha256) + "," +
        std::to_string(input.m_size_bytes) + "," +
        std::to_string(targetVersion) + "," +
        std::to_string(targetDeleted ? 1 : 0) +
        ") ON DUPLICATE KEY UPDATE "
        "sha256=VALUES(sha256),"
        "size_bytes=VALUES(size_bytes),"
        "doc_version=VALUES(doc_version),"
        "is_deleted=VALUES(is_deleted),"
        "updated_at=CURRENT_TIMESTAMP";

    auto execRes = execute(session, sql);
    session.close();
    if (!execRes) {
        return std::unexpected(execRes.error());
    }

    return getDocument(input.m_project, input.m_relative_path);
}

std::expected<DbDocumentRecord, std::string> MySqlDbProvider::getDocument(
    const std::string& project,
    const std::string& relative_path)
{
    return selectDocumentByClause("WHERE project=" + sqlQuote(project) + " AND relative_path=" +
                                  sqlQuote(relative_path));
}

std::expected<std::vector<DbDocumentRecord>, std::string> MySqlDbProvider::listDocuments(
    const DbListDocumentsInput& input)
{
    MysqlClient session;
    auto connRes = connect(session);
    if (!connRes) {
        return std::unexpected(connRes.error());
    }

    std::string where = "WHERE 1=1";
    if (input.m_project.has_value() && !input.m_project->empty()) {
        where += " AND project=" + sqlQuote(*input.m_project);
    }
    if (!input.m_include_deleted) {
        where += " AND is_deleted=0";
    }

    const std::string sql =
        "SELECT id,project,relative_path,sha256,size_bytes,doc_version,is_deleted,"
        "DATE_FORMAT(created_at,'%Y-%m-%d %H:%i:%s'),"
        "DATE_FORMAT(updated_at,'%Y-%m-%d %H:%i:%s') "
        "FROM documents " +
        where +
        " ORDER BY project ASC,relative_path ASC";

    auto queryRes = session.query(sql);
    if (!queryRes) {
        session.close();
        return std::unexpected("mysql query failed: " + queryRes.error().message());
    }

    std::vector<DbDocumentRecord> docs;
    docs.reserve(static_cast<size_t>(queryRes->rowCount()));
    for (std::size_t i = 0; i < queryRes->rowCount(); ++i) {
        const auto& row = queryRes->row(i);
        DbDocumentRecord doc;
        doc.m_id = parseUint64OrDefault(row.getString(0, "0"), 0);
        doc.m_project = row.getString(1, "");
        doc.m_relative_path = row.getString(2, "");
        doc.m_sha256 = row.getString(3, "");
        doc.m_size_bytes = parseUint64OrDefault(row.getString(4, "0"), 0);
        doc.m_doc_version = parseUint64OrDefault(row.getString(5, "0"), 0);
        doc.m_is_deleted = parseMysqlBool(row.getString(6, "0"));
        doc.m_created_at = row.getString(7, "");
        doc.m_updated_at = row.getString(8, "");
        docs.push_back(std::move(doc));
    }

    session.close();
    return docs;
}

std::expected<DbDocumentRecord, std::string> MySqlDbProvider::markDocumentDeleted(
    const std::string& project,
    const std::string& relative_path)
{
    auto current = getDocument(project, relative_path);
    if (!current) {
        return std::unexpected(current.error());
    }

    DbUpsertDocumentInput input;
    input.m_project = project;
    input.m_relative_path = relative_path;
    input.m_sha256 = current->m_sha256;
    input.m_size_bytes = current->m_size_bytes;
    input.m_doc_version = current->m_doc_version + 1;
    input.m_is_deleted = true;
    return upsertDocument(input);
}

std::expected<DbIndexJobRecord, std::string> MySqlDbProvider::createIndexJob(const DbCreateIndexJobInput& input)
{
    MysqlClient session;
    auto connRes = connect(session);
    if (!connRes) {
        return std::unexpected(connRes.error());
    }

    std::string documentIdSql = "NULL";
    if (input.m_document_id.has_value()) {
        documentIdSql = std::to_string(*input.m_document_id);
    }

    const std::string sql =
        "INSERT INTO index_jobs (job_type,project,relative_path,document_id,status,attempts,trigger_source,payload_json,error_message)"
        " VALUES (" +
        sqlQuote(input.m_job_type.empty() ? "reindex" : input.m_job_type) + "," +
        sqlQuote(input.m_project) + "," +
        sqlQuote(input.m_relative_path) + "," +
        documentIdSql + ",'pending',0," +
        sqlQuote(input.m_trigger_source.empty() ? "admin" : input.m_trigger_source) + "," +
        sqlQuote(input.m_payload_json.empty() ? "{}" : input.m_payload_json) + ",'' )";

    auto execRes = execute(session, sql);
    if (!execRes) {
        session.close();
        return std::unexpected(execRes.error());
    }

    auto idRes = session.query("SELECT LAST_INSERT_ID()");
    if (!idRes) {
        session.close();
        return std::unexpected("mysql query failed: " + idRes.error().message());
    }
    if (idRes->rowCount() == 0) {
        session.close();
        return std::unexpected("failed to fetch index job id");
    }

    const auto jobId = parseUint64OrDefault(idRes->row(0).getString(0, "0"), 0);
    session.close();
    return getIndexJobById(jobId);
}

std::expected<std::optional<DbIndexJobRecord>, std::string> MySqlDbProvider::fetchNextPendingIndexJob()
{
    MysqlClient session;
    auto connRes = connect(session);
    if (!connRes) {
        return std::unexpected(connRes.error());
    }

    auto txRes = execute(session, "START TRANSACTION");
    if (!txRes) {
        session.close();
        return std::unexpected(txRes.error());
    }

    auto selectRes = session.query(
        "SELECT id FROM index_jobs WHERE status='pending' ORDER BY id ASC LIMIT 1 FOR UPDATE");
    if (!selectRes) {
        execute(session, "ROLLBACK");
        session.close();
        return std::unexpected("mysql query failed: " + selectRes.error().message());
    }

    if (selectRes->rowCount() == 0) {
        execute(session, "COMMIT");
        session.close();
        return std::optional<DbIndexJobRecord>{};
    }

    const auto jobId = parseUint64OrDefault(selectRes->row(0).getString(0, "0"), 0);

    auto updateRes = execute(session,
                             "UPDATE index_jobs SET status='running',attempts=attempts+1,"
                             "started_at=CURRENT_TIMESTAMP,finished_at=NULL,error_message='',"
                             "updated_at=CURRENT_TIMESTAMP WHERE id=" +
                                 std::to_string(jobId));
    if (!updateRes) {
        execute(session, "ROLLBACK");
        session.close();
        return std::unexpected(updateRes.error());
    }

    auto commitRes = execute(session, "COMMIT");
    session.close();
    if (!commitRes) {
        return std::unexpected(commitRes.error());
    }

    auto jobRes = getIndexJobById(jobId);
    if (!jobRes) {
        return std::unexpected(jobRes.error());
    }
    return std::optional<DbIndexJobRecord>{*jobRes};
}

std::expected<DbIndexJobRecord, std::string> MySqlDbProvider::getIndexJobById(std::uint64_t job_id)
{
    return selectIndexJobByClause("WHERE id=" + std::to_string(job_id));
}

std::expected<DbIndexJobRecord, std::string> MySqlDbProvider::finishIndexJobSuccess(std::uint64_t job_id)
{
    MysqlClient session;
    auto connRes = connect(session);
    if (!connRes) {
        return std::unexpected(connRes.error());
    }

    auto txRes = execute(session, "START TRANSACTION");
    if (!txRes) {
        session.close();
        return std::unexpected(txRes.error());
    }

    auto ensureRes = ensureIndexStateRow(session);
    if (!ensureRes) {
        execute(session, "ROLLBACK");
        session.close();
        return std::unexpected(ensureRes.error());
    }

    auto updateJobRes = execute(session,
                                "UPDATE index_jobs SET status='success',error_message='',"
                                "finished_at=CURRENT_TIMESTAMP,updated_at=CURRENT_TIMESTAMP "
                                "WHERE id=" +
                                    std::to_string(job_id));
    if (!updateJobRes) {
        execute(session, "ROLLBACK");
        session.close();
        return std::unexpected(updateJobRes.error());
    }

    auto updateStateRes = execute(session,
                                  "UPDATE index_state SET current_version=current_version+1,"
                                  "last_success_job_id=" +
                                      std::to_string(job_id) +
                                      ",updated_at=CURRENT_TIMESTAMP WHERE id=1");
    if (!updateStateRes) {
        execute(session, "ROLLBACK");
        session.close();
        return std::unexpected(updateStateRes.error());
    }

    auto commitRes = execute(session, "COMMIT");
    session.close();
    if (!commitRes) {
        return std::unexpected(commitRes.error());
    }

    return getIndexJobById(job_id);
}

std::expected<DbIndexJobRecord, std::string> MySqlDbProvider::finishIndexJobFailed(
    std::uint64_t job_id,
    const std::string& error_message)
{
    MysqlClient session;
    auto connRes = connect(session);
    if (!connRes) {
        return std::unexpected(connRes.error());
    }

    auto execRes = execute(session,
                           "UPDATE index_jobs SET status='failed',error_message=" +
                               sqlQuote(error_message) +
                               ",finished_at=CURRENT_TIMESTAMP,updated_at=CURRENT_TIMESTAMP "
                               "WHERE id=" +
                               std::to_string(job_id));
    session.close();
    if (!execRes) {
        return std::unexpected(execRes.error());
    }

    return getIndexJobById(job_id);
}

std::expected<DbIndexStateRecord, std::string> MySqlDbProvider::getIndexState()
{
    MysqlClient session;
    auto connRes = connect(session);
    if (!connRes) {
        return std::unexpected(connRes.error());
    }

    auto ensureRes = ensureIndexStateRow(session);
    if (!ensureRes) {
        session.close();
        return std::unexpected(ensureRes.error());
    }

    auto queryRes = session.query(
        "SELECT current_version,last_success_job_id,"
        "DATE_FORMAT(updated_at,'%Y-%m-%d %H:%i:%s') FROM index_state WHERE id=1 LIMIT 1");
    if (!queryRes) {
        session.close();
        return std::unexpected("mysql query failed: " + queryRes.error().message());
    }
    if (queryRes->rowCount() == 0) {
        session.close();
        return std::unexpected("index state not found");
    }

    const auto& row = queryRes->row(0);
    DbIndexStateRecord state;
    state.m_current_version = parseUint64OrDefault(row.getString(0, "0"), 0);
    const std::string lastJobRaw = row.getString(1, "");
    if (!lastJobRaw.empty()) {
        state.m_last_success_job_id = parseUint64OrDefault(lastJobRaw, 0);
    }
    state.m_updated_at = row.getString(2, "");

    session.close();
    return state;
}
