CREATE TABLE Organization (
organization_id INT PRIMARY KEY,
organization_name VARCHAR(150) NOT NULL,
organization_code VARCHAR(20) UNIQUE NOT NULL,
organization_type VARCHAR(30) NOT NULL,
phone_no VARCHAR(15) NOT NULL,
email VARCHAR(150) UNIQUE NOT NULL,
city VARCHAR(100) NOT NULL,
state VARCHAR(100) NOT NULL,
country VARCHAR(100) DEFAULT 'India',
pin_code VARCHAR(10) NOT NULL,
registration_no VARCHAR(50) UNIQUE,
website VARCHAR(200),
created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
status VARCHAR(20) DEFAULT 'Active',
CHECK (organization_type IN ('Government','Private','University Lab')),
CHECK (status IN ('Active','Inactive','Suspended'))
);


CREATE TABLE App_User (
user_id INT PRIMARY KEY,
org_id INT NOT NULL,
first_name VARCHAR(50) NOT NULL,
middle_name VARCHAR(50),
last_name VARCHAR(50) NOT NULL,
email VARCHAR(150) UNIQUE NOT NULL,
password_hash VARCHAR(255) NOT NULL,
phone_no VARCHAR(15) NOT NULL,
created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
last_login_date TIMESTAMP,
updated_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
status VARCHAR(20) DEFAULT 'Active',
profile_picture_url VARCHAR(255),
FOREIGN KEY (org_id)
        REFERENCES Organization(organization_id),
CHECK (status IN ('Active','Inactive','Suspended'))
);



CREATE TABLE Role (
role_id INT PRIMARY KEY,
role_name VARCHAR(50) UNIQUE NOT NULL,
description VARCHAR(200),
created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
status VARCHAR(20) DEFAULT 'Active',
CHECK (status IN ('Active','Inactive'))
);



CREATE TABLE Permission (
permission_id INT PRIMARY KEY,
permission_name VARCHAR(100) UNIQUE NOT NULL,
description VARCHAR(300),
status VARCHAR(20) DEFAULT 'Active',
created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
CHECK (status IN ('Active','Inactive'))
);

CREATE TABLE User_Role (
user_id INT NOT NULL,
role_id INT NOT NULL,
assigned_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
assigned_by INT,
status VARCHAR(20) DEFAULT 'Active',
PRIMARY KEY (user_id, role_id),
FOREIGN KEY (user_id) REFERENCES App_User(user_id),
FOREIGN KEY (role_id) REFERENCES Role(role_id),
FOREIGN KEY (assigned_by) REFERENCES App_User(user_id),
CHECK (status IN ('Active','Inactive'))
);

CREATE TABLE Role_Permission (
role_id INT NOT NULL,
permission_id INT NOT NULL,
assigned_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
PRIMARY KEY (role_id, permission_id),
FOREIGN KEY (role_id)
        REFERENCES Role(role_id),
FOREIGN KEY (permission_id)
        REFERENCES Permission(permission_id)
);

CREATE TABLE Project (
project_id INT PRIMARY KEY,
org_id INT NOT NULL,
project_name VARCHAR(150) NOT NULL,
description VARCHAR(500),
project_type VARCHAR(50),
start_date DATE,
end_date DATE,
status VARCHAR(30) DEFAULT 'Planning',
created_by INT NOT NULL,
created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
updated_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
FOREIGN KEY (org_id) REFERENCES Organization(organization_id),
FOREIGN KEY (created_by)
        REFERENCES App_User(user_id),
CHECK (status IN ('Planning','Active','Completed','On Hold','Cancelled')),
CHECK (end_date IS NULL OR start_date IS NULL OR end_date >= start_date)
);

CREATE TABLE Project_Member (
member_id INT PRIMARY KEY,
project_id INT NOT NULL,
user_id INT NOT NULL,
project_role VARCHAR(50) NOT NULL,
joined_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
assigned_by INT,
status VARCHAR(20) DEFAULT 'Active',
FOREIGN KEY (project_id)
        REFERENCES Project(project_id),
FOREIGN KEY (user_id)
        REFERENCES App_User(user_id),
FOREIGN KEY (assigned_by)
        REFERENCES App_User(user_id),
UNIQUE (project_id, user_id),
CHECK (status IN ('Active', 'Inactive', 'Removed'))
);

CREATE TABLE Folder (
folder_id INT PRIMARY KEY,
project_id INT NOT NULL,
parent_folder_id INT,
folder_name VARCHAR(150) NOT NULL,
description VARCHAR(300),
created_by INT NOT NULL,
created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
updated_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
status VARCHAR(20) DEFAULT 'Active',
FOREIGN KEY (project_id)
        REFERENCES Project(project_id),
FOREIGN KEY (parent_folder_id)
        REFERENCES Folder(folder_id),
FOREIGN KEY (created_by)
        REFERENCES App_User(user_id),
CHECK (status IN ('Active','Archived','Deleted'))
);

CREATE TABLE File (
file_id INT PRIMARY KEY,
folder_id INT NOT NULL,
file_name VARCHAR(200) NOT NULL,
file_type VARCHAR(50),
file_size BIGINT,
blob_path VARCHAR(500) NOT NULL,
uploaded_by INT NOT NULL,
current_version INT DEFAULT 1,
upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
updated_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
status VARCHAR(20) DEFAULT 'Active',
description VARCHAR(500),
FOREIGN KEY (folder_id)
        REFERENCES Folder(folder_id),
FOREIGN KEY (uploaded_by)
        REFERENCES App_User(user_id),
CHECK (current_version >= 1),
CHECK (status IN ('Active','Archived','Deleted'))
);

CREATE TABLE File_Version (
version_id INT PRIMARY KEY,
file_id INT NOT NULL,
version_number INT NOT NULL,
blob_path VARCHAR(500) NOT NULL,
file_size BIGINT,
uploaded_by INT NOT NULL,
uploaded_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
change_description VARCHAR(500),
is_current BOOLEAN DEFAULT TRUE,
FOREIGN KEY (file_id)
        REFERENCES File(file_id),
FOREIGN KEY (uploaded_by)
        REFERENCES App_User(user_id),
UNIQUE (file_id, version_number),
CHECK (version_number >= 1)
);

CREATE TABLE Activity_Log (
log_id INT PRIMARY KEY,
user_id INT NOT NULL,
org_id INT NOT NULL,
action_type VARCHAR(50) NOT NULL,
entity_type VARCHAR(50),
entity_id INT,
description VARCHAR(500),
log_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
ip_address VARCHAR(45),
FOREIGN KEY (user_id)
        REFERENCES App_User(user_id),
FOREIGN KEY (org_id)
        REFERENCES Organization(organization_id)
);
