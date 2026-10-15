SELECT organization_id, organization_name
FROM Organization
ORDER BY organization_id;

SELECT project_id
FROM Project
WHERE project_id = 9001;

SELECT member_id
FROM Project_Member
WHERE member_id = 9001;

SELECT user_id, first_name, last_name, org_id
FROM App_User
ORDER BY user_id;


SELECT
    user_id,
    first_name,
    email,
    LEFT(password_hash, 15) AS password_preview,
    status
FROM App_User
ORDER BY user_id
LIMIT 10;

UPDATE App_User
SET password_hash = 'scrypt:32768:8:1$CnuhfFyzy23YrIdd$1625f12a5b58d005ecf1baf70a8ace13be1452db689c7739880731ec6dbc6b4d8dc22575fe83e290fee8bd6a573c0ad0c8aaf7607a1e95356da9ac363696c7f4',
    updated_date = CURRENT_TIMESTAMP
WHERE user_id = 2001
  AND status = 'Active';

SELECT
    user_id,
    email,
    status,
    LEFT(password_hash, 7) AS hash_prefix,
    last_login_date
FROM app_user
WHERE LOWER(email) = LOWER('arjun.nair@isrc.gov.in');

SELECT
    f.folder_id,
    f.folder_name,
    f.project_id,
    f.parent_folder_id,
    parent.folder_name AS parent_folder_name
FROM folder f
LEFT JOIN folder parent
    ON f.parent_folder_id = parent.folder_id
WHERE f.folder_id IN (8001, 8002)
ORDER BY f.folder_id;

SELECT
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE LOWER(table_name) = 'file_version'
ORDER BY ordinal_position;

SELECT
    version_id,
    file_id,
    version_number,
    blob_path,
    file_size,
    uploaded_by,
    uploaded_date,
    change_description,
    is_current
FROM file_version
ORDER BY file_id, version_number;

SELECT
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE LOWER(table_name) = 'activity_log'
ORDER BY ordinal_position;

-- Count all users
SELECT COUNT(*) AS total_users
FROM app_user;

-- Count users in each organization
SELECT org_id, COUNT(*) AS user_count
FROM app_user
GROUP BY org_id
ORDER BY org_id;

-- Display all user records
SELECT user_id, first_name, last_name, email, org_id, status
FROM app_user
ORDER BY user_id;

SELECT
    column_name,
    data_type,
    column_default,
    is_identity
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'file'
  AND column_name = 'file_id';

SELECT file_id, file_name, folder_id
FROM public.file
WHERE file_id = 8011;


SELECT
    column_name,
    data_type,
    column_default,
    is_identity
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'file'
  AND column_name = 'file_id';


SELECT file_id, file_name, folder_id
FROM public.file
WHERE file_id = 8011;


SELECT
    table_name,
    column_name,
    column_default,
    is_identity
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name IN (
      'file',
      'folder',
      'project',
      'app_user',
      'file_version'
  )
  AND column_name IN (
      'file_id',
      'folder_id',
      'project_id',
      'user_id',
      'version_id'
  )
ORDER BY table_name, column_name;
