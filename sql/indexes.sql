
-- =========================================
-- ASTROVAULT: INDEXES
-- =========================================

-- 1. Find users by organization
CREATE INDEX IF NOT EXISTS idx_app_user_org
ON App_User(org_id);

-- 2. Find projects by organization
CREATE INDEX IF NOT EXISTS idx_project_org
ON Project(org_id);

-- 3. Find project members by user
CREATE INDEX IF NOT EXISTS idx_project_member_user
ON Project_Member(user_id);

-- 4. Find folders belonging to a project
CREATE INDEX IF NOT EXISTS idx_folder_project
ON Folder(project_id);

-- 5. Find folders by parent folder
CREATE INDEX IF NOT EXISTS idx_folder_parent
ON Folder(parent_folder_id);

-- 6. Find files inside a folder
CREATE INDEX IF NOT EXISTS idx_file_folder
ON File(folder_id);

-- 7. Find file versions
CREATE INDEX IF NOT EXISTS idx_file_version_file
ON File_Version(file_id);

-- 8. Find activity logs by organization
CREATE INDEX IF NOT EXISTS idx_activity_org
ON Activity_Log(org_id);

-- 9. Sort activity logs by time
CREATE INDEX IF NOT EXISTS idx_activity_log_time
ON Activity_Log(log_time);

-- 10. Find user-role assignments by role
CREATE INDEX IF NOT EXISTS idx_user_role_role
ON User_Role(role_id);

SELECT
    tablename,
    indexname
FROM pg_indexes
WHERE schemaname = 'public'
ORDER BY tablename, indexname;


-- Organization-based lookups
CREATE INDEX IF NOT EXISTS idx_app_user_org_id
    ON app_user (org_id);

CREATE INDEX IF NOT EXISTS idx_project_org_id
    ON project (org_id);

CREATE INDEX IF NOT EXISTS idx_activity_log_org_id
    ON activity_log (org_id);

CREATE INDEX IF NOT EXISTS idx_activity_log_user_id
    ON activity_log (user_id);

-- Folder and file lookups
CREATE INDEX IF NOT EXISTS idx_folder_project_id
    ON folder (project_id);

CREATE INDEX IF NOT EXISTS idx_folder_parent_folder_id
    ON folder (parent_folder_id);

CREATE INDEX IF NOT EXISTS idx_file_folder_id
    ON file (folder_id);

-- Project membership lookups
CREATE INDEX IF NOT EXISTS idx_project_member_user_id
    ON project_member (user_id);

-- Role and permission lookups
CREATE INDEX IF NOT EXISTS idx_user_role_role_id
    ON user_role (role_id);

CREATE INDEX IF NOT EXISTS idx_role_permission_permission_id
    ON role_permission (permission_id);
