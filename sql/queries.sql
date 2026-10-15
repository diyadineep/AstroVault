-- =========================================================
-- SECTION 1: JOIN QUERIES
-- =========================================================

-- 1. Display users with their organization names
SELECT
    u.user_id,
    u.first_name,
    u.last_name,
    u.email,
    o.organization_name
FROM App_User u
INNER JOIN Organization o
    ON u.org_id = o.organization_id;


-- 2. Display projects with their organization names
SELECT
    p.project_id,
    p.project_name,
    p.status,
    o.organization_name
FROM Project p
INNER JOIN Organization o
    ON p.org_id = o.organization_id;


-- 3. Display project members with project and user details
SELECT
    pm.member_id,
    p.project_name,
    u.first_name,
    u.last_name,
    pm.project_role
FROM Project_Member pm
INNER JOIN Project p
    ON pm.project_id = p.project_id
INNER JOIN App_User u
    ON pm.user_id = u.user_id;


-- 4. Display files with folder and project details
SELECT
    f.file_id,
    f.file_name,
    fo.folder_name,
    p.project_name,
    f.status
FROM File f
INNER JOIN Folder fo
    ON f.folder_id = fo.folder_id
INNER JOIN Project p
    ON fo.project_id = p.project_id;


-- 5. Display roles assigned to each user
SELECT
    u.user_id,
    u.first_name,
    u.last_name,
    r.role_name
FROM App_User u
INNER JOIN User_Role ur
    ON u.user_id = ur.user_id
INNER JOIN Role r
    ON ur.role_id = r.role_id;


-- 6. Display permissions associated with each role
SELECT
    r.role_name,
    pe.permission_name,
    pe.description
FROM Role_Permission rp
INNER JOIN Role r
    ON rp.role_id = r.role_id
INNER JOIN Permission pe
    ON rp.permission_id = pe.permission_id;


-- 7. Display files and their version history
SELECT
    f.file_id,
    f.file_name,
    fv.version_number,
    fv.uploaded_date,
    fv.change_description
FROM File f
INNER JOIN File_Version fv
    ON f.file_id = fv.file_id
ORDER BY f.file_id, fv.version_number;


-- 8. Display activity logs with user and organization names
SELECT
    al.log_id,
    u.first_name,
    u.last_name,
    o.organization_name,
    al.action_type,
    al.entity_type,
    al.log_time
FROM Activity_Log al
INNER JOIN App_User u
    ON al.user_id = u.user_id
INNER JOIN Organization o
    ON al.org_id = o.organization_id
ORDER BY al.log_time DESC;


-- =========================================================
-- SECTION 2: SUBQUERIES AND AGGREGATION
-- =========================================================

-- 9. Projects belonging to organizations in Tamil Nadu
SELECT project_id, project_name, org_id
FROM Project
WHERE org_id IN (
    SELECT organization_id
    FROM Organization
    WHERE state = 'Tamil Nadu'
);

-- 10. Users with at least one role assignment
SELECT user_id, first_name, last_name
FROM App_User u
WHERE EXISTS (
    SELECT 1
    FROM User_Role ur
    WHERE ur.user_id = u.user_id
);


-- 11. Projects whose member count exceeds the average member count per project
SELECT
    p.project_id,
    p.project_name,
    COUNT(pm.user_id) AS member_count
FROM Project p
JOIN Project_Member pm
    ON pm.project_id = p.project_id
GROUP BY p.project_id, p.project_name
HAVING COUNT(pm.user_id) > (
    SELECT AVG(member_count)
    FROM (
        SELECT COUNT(*) AS member_count
        FROM Project_Member
        GROUP BY project_id
    ) AS project_counts
);


-- =========================================
-- SECTION 3: VIEWS
-- =========================================

-- View 1: Users with their organization details
CREATE OR REPLACE VIEW vw_user_organization AS
SELECT
    u.user_id,
    u.first_name,
    u.last_name,
    u.email,
    u.status AS user_status,
    o.organization_id,
    o.organization_name,
    o.organization_type
FROM App_User u
JOIN Organization o
    ON u.org_id = o.organization_id;


-- View 2: Projects with organization details
CREATE OR REPLACE VIEW vw_project_organization AS
SELECT
    p.project_id,
    p.project_name,
    p.description,
    p.project_type,
    p.status AS project_status,
    o.organization_name,
    p.start_date,
    p.end_date
FROM Project p
JOIN Organization o
    ON p.org_id = o.organization_id;


-- View 3: File details with folder and project information
CREATE OR REPLACE VIEW vw_file_details AS
SELECT
    f.file_id,
    f.file_name,
    f.file_type,
    f.file_size,
    f.status AS file_status,
    fo.folder_name,
    p.project_name,
    f.uploaded_by,
    f.current_version,
    f.upload_date
FROM File f
JOIN Folder fo
    ON f.folder_id = fo.folder_id
JOIN Project p
    ON fo.project_id = p.project_id;


-- View 4: Project membership details
CREATE OR REPLACE VIEW vw_project_members AS
SELECT
    p.project_id,
    p.project_name,
    u.user_id,
    u.first_name,
    u.last_name,
    u.email,
    pm.project_role,
    pm.status AS membership_status
FROM Project_Member pm
JOIN Project p
    ON pm.project_id = p.project_id
JOIN App_User u
    ON pm.user_id = u.user_id;


-- View 5: File version history
CREATE OR REPLACE VIEW vw_file_version_history AS
SELECT
    f.file_id,
    f.file_name,
    fv.version_id,
    fv.version_number,
    fv.file_size,
    fv.uploaded_date,
    fv.change_description,
    fv.is_current
FROM File f
JOIN File_Version fv
    ON f.file_id = fv.file_id;

SELECT * FROM vw_user_organization;
SELECT * FROM vw_project_organization;
SELECT * FROM vw_file_details;
SELECT * FROM vw_project_members;
SELECT * FROM vw_file_version_history;



-- =========================================
-- SECTION 4: TRIGGERS
-- =========================================

-- Trigger function: automatically update the
-- updated_date column when a user record changes.

CREATE OR REPLACE FUNCTION update_user_timestamp()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_date := CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$;

-- Trigger on App_User

DROP TRIGGER IF EXISTS trg_update_user_timestamp
ON App_User;

CREATE TRIGGER trg_update_user_timestamp
BEFORE UPDATE ON App_User
FOR EACH ROW
EXECUTE FUNCTION update_user_timestamp();


-- Trigger function: automatically update the
-- updated_date column when a project changes.

CREATE OR REPLACE FUNCTION update_project_timestamp()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_date := CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$;

-- Trigger on Project

DROP TRIGGER IF EXISTS trg_update_project_timestamp
ON Project;

CREATE TRIGGER trg_update_project_timestamp
BEFORE UPDATE ON Project
FOR EACH ROW
EXECUTE FUNCTION update_project_timestamp();


-- Trigger function: automatically update the
-- updated_date column when a file changes.

CREATE OR REPLACE FUNCTION update_file_timestamp()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_date := CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$;

-- Trigger on File

DROP TRIGGER IF EXISTS trg_update_file_timestamp
ON File;

CREATE TRIGGER trg_update_file_timestamp
BEFORE UPDATE ON File
FOR EACH ROW
EXECUTE FUNCTION update_file_timestamp();



-- =========================================
-- SECTION 5: TRANSACTIONS
-- =========================================

-- Transaction 1: Create a project and assign a member
-- Replace the example IDs with valid IDs from your database.


--BEGIN;

--INSERT INTO Project (
--    project_id,
--    org_id,
--    project_name,
--    description,
--    project_type,
--    status,
--    created_by
--)
--VALUES (
--    9001,
--    1001,
--    'Transaction Demo Project',
--    'Demonstration of PostgreSQL transactions',
--    'Research',
--    'Planning',
--    2001
--);

--INSERT INTO Project_Member (
--    member_id,
--    project_id,
--    user_id,
--    project_role,
--    assigned_by,
--    status
--)
--VALUES (
--    9001,
--    9001,
--    2001,
--    'Researcher',
--    2001,
--    'Active'
--);

--COMMIT;


-- Transaction 2: Demonstrate ROLLBACK

--BEGIN;

--UPDATE Project
--SET status = 'On Hold'
--WHERE project_id = 9001;

--ROLLBACK;

-- Verify that the original status remains unchanged
SELECT project_id, project_name, status
FROM Project
WHERE project_id = 9001;































