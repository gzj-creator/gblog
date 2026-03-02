#ifndef BLOG_DB_SERVICE_H
#define BLOG_DB_SERVICE_H

#include <map>
#include <optional>
#include <string>
#include <vector>

struct ProjectInfo {
    std::string m_id;
    std::string m_name;
    std::string m_description;
    std::string m_long_description;
    std::vector<std::string> m_features;
    std::string m_language;
    std::string m_license;
    std::string m_github;
};

struct BlogPost {
    std::string m_id;
    std::string m_title;
    std::string m_excerpt;
    std::string m_content;
    std::string m_date;
    std::string m_category;
    std::string m_category_name;
    std::vector<std::string> m_tags;
    std::string m_reading_time;
    bool m_featured;
};

struct DocItem {
    std::string m_id;
    std::string m_title;
    std::string m_description;
    std::string m_category;
    std::string m_content;
    int m_order;
};

class DbService {
public:
    DbService();

    std::string allProjectsToJson() const;
    std::string projectToJson(const ProjectInfo& project) const;
    std::optional<ProjectInfo> getProjectById(const std::string& id) const;

    std::string allPostsToJson() const;
    std::string postToJson(const BlogPost& post) const;
    std::optional<BlogPost> getPostById(const std::string& id) const;

    std::string allDocsToJson() const;
    std::string docToJson(const DocItem& doc) const;
    std::optional<DocItem> getDocById(const std::string& id) const;

private:
    static std::string escapeJson(const std::string& str);
    static std::string vectorToJsonArray(const std::vector<std::string>& vec);

    std::map<std::string, ProjectInfo> m_projects;
    std::vector<BlogPost> m_posts;
    std::vector<DocItem> m_docs;
};

#endif  // BLOG_DB_SERVICE_H
