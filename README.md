# 🚀 AstroVault

**A Multi-Tenant SaaS Platform for Space Research Document Management**

Built with Python, Flask and PostgreSQL

---

## 🌌 Overview

**AstroVault** is a web-based document management platform designed to help space research organizations manage projects, organize research documents and collaborate with team members through a centralized application.

The platform follows a multi-tenant approach, allowing multiple organizations to use a shared application while maintaining organization-specific data and access.

Built using **Python, Flask and PostgreSQL**, AstroVault combines backend application development with relational database design to support user management, project organization, document storage, version tracking and activity monitoring.

---

## 🎯 Problem Statement

Space research organizations work with numerous research papers, technical reports, project documents and other digital resources.

Managing these documents across multiple projects and teams can become difficult without a centralized system. It is also important to control who can access organizational information and maintain a record of document-related activities.

AstroVault addresses these challenges by providing a structured document management platform with organization-aware data handling, access control, project management and document version tracking.

---

## ✨ Key Features

- 🏢 **Organization Management:** Support organization-specific users and data.
- 🔐 **User Authentication:** Registration, login, logout and session-based access.
- 🛡️ **Role-Based Access Control:** Manage roles, permissions and user-role assignments.
- 📁 **Project Management:** Create, update and organize research projects.
- 👥 **Project Collaboration:** Assign users as project members and manage memberships.
- 🗂️ **Folder Management:** Create and organize folders, including nested folder structures.
- 📄 **File Management:** Upload, view and download research documents.
- 🔄 **File Versioning:** Upload and maintain multiple versions of documents.
- 📊 **Dashboard:** Display organizational and project-related statistics.
- 📝 **Activity Logging:** Maintain records of important user and application activities.

---

## 🏗️ Technology Stack

| **Technology** | **Purpose** |
|---|---|
| Python | Backend programming |
| Flask | Web application framework |
| PostgreSQL | Relational database management |
| SQL | Database design, queries and operations |
| SQLAlchemy | Database connectivity and integration |
| psycopg2 | PostgreSQL database adapter |
| HTML & CSS | Frontend structure and styling |
| Jinja2 | Dynamic HTML templating |
| Werkzeug | Password hashing and authentication utilities |
| Git & GitHub | Version control and project management |

---

## 🧩 System Architecture

AstroVault follows a web-based application architecture in which users interact with the Flask application, which processes requests, performs access checks and communicates with the PostgreSQL database.

```text
       Organizations / Users
                 |
                 v
        Web-Based Interface
          (HTML / CSS)
                 |
                 v
          Flask Backend
                 |
        -------------------
        |        |        |
        v        v        v
   Authentication Access  Application
                  Control   Logic
        |        |        |
        -------------------
                 |
                 v
          PostgreSQL
                 |
        -------------------
        |        |        |
        v        v        v
     User &   Projects &  Files &
     Roles    Folders     Versions
                 |
                 v
           Activity Logs
```

---

## 🗄️ Database Design

AstroVault uses a relational database consisting of **12 interconnected tables** to manage organizational information, users, permissions, projects and documents.

| **Table** | **Purpose** |
|---|---|
| `Organization` | Stores organization information |
| `App_User` | Stores user details and credentials |
| `Role` | Defines application roles |
| `Permission` | Stores available permissions |
| `User_Role` | Maps users to assigned roles |
| `Role_Permission` | Maps permissions to roles |
| `Project` | Stores research project details |
| `Project_Member` | Manages project membership |
| `Folder` | Organizes project folders and subfolders |
| `File` | Stores document metadata |
| `File_Version` | Maintains document version information |
| `Activity_Log` | Records application activities |

### DBMS Concepts Implemented

- **Relational Database Design:** Organizing application data into related tables.
- **Primary and Foreign Keys:** Establishing relationships and maintaining referential integrity.
- **Integrity Constraints:** Using NOT NULL, UNIQUE and CHECK constraints.
- **Composite Primary Keys:** Implementing keys for relationship tables.
- **SQL Joins:** Retrieving related information across multiple tables.
- **Subqueries and Aggregation:** Performing nested queries and grouped calculations.
- **Views:** Creating five views for commonly required combined information.
- **Indexes:** Improving data retrieval for frequently accessed columns.
- **Triggers and Functions:** Automatically updating timestamps when selected records are modified.
- **Transactions:** Using transaction control and rollback operations for database consistency.
- **Role-Based Access Control:** Structuring user-role and role-permission relationships.

---

## 📂 Project Structure

```text
ASTROVAULT_FINAL/
│
├── backend/
│   ├── app.py
│   ├── requirements.txt
│   │
│   ├── templates/
│   │   ├── login.html
│   │   ├── register.html
│   │   ├── dashboard.html
│   │   ├── users.html
│   │   ├── projects.html
│   │   ├── members.html
│   │   ├── folders.html
│   │   ├── files.html
│   │   ├── versions.html
│   │   └── activity.html
│   │
│   ├── static/
│   │   └── css/
│   │       ├── style.css
│   │       ├── dashboard.css
│   │       ├── users.css
│   │       ├── projects.css
│   │       ├── members.css
│   │       ├── folders.css
│   │       ├── files.css
│   │       ├── versions.css
│   │       └── activity.css
│   │
│   └── uploads/
│
├── dataset/
│   ├── organization.csv
│   ├── app_user.csv
│   ├── role.csv
│   ├── permission.csv
│   ├── user_role.csv
│   ├── role_permission.csv
│   ├── project.csv
│   ├── project_member.csv
│   ├── folder.csv
│   ├── file.csv
│   ├── file_version.csv
│   └── activity_log.csv
│
├── sql/
│   ├── schema.sql
│   ├── main.sql
│   ├── addons.sql
│   ├── addons2.sql
│   ├── indexes.sql
│   └── queries.sql
│
├── .gitignore
└── README.md
```

---

## ⚙️ Getting Started

### Prerequisites

- Python 3.x
- PostgreSQL
- Git

### 1. Clone the Repository

```bash
git clone https://github.com/diyadineep/AstroVault.git
```

### 2. Navigate to the Project

```bash
cd AstroVault
```

### 3. Set Up a Virtual Environment

```bash
cd backend
python -m venv .venv
```

Activate the environment:

**Windows:**

```bash
.venv\Scripts\activate
```

**Linux / macOS:**

```bash
source .venv/bin/activate
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Configure PostgreSQL

Create a PostgreSQL database named:

```sql
CREATE DATABASE ASTROVAULT_FINAL;
```

Execute the required SQL scripts from the `sql/` directory in the appropriate setup order to create the database schema, supporting database objects and sample data.

The `dataset/` directory contains CSV files corresponding to the database tables.

### 6. Configure Environment Variables

Create a `.env` file inside the `backend/` directory and configure your local database credentials:

```env
SECRET_KEY=your_random_secret_key

DB_USER=postgres
DB_PASSWORD=your_postgresql_password
DB_HOST=localhost
DB_PORT=5432
DB_NAME=ASTROVAULT_FINAL
```

Replace the example values with your own PostgreSQL configuration. Do not commit your `.env` file to GitHub.

### 7. Run the Application

From inside the `backend/` directory, execute:

```bash
python app.py
```

Open the application in your browser:

```text
http://127.0.0.1:5000/
```

---

## 🔐 Multi-Tenant Architecture

AstroVault uses an organization-oriented data model in which users, projects, folders and documents are associated with their respective organizations.

Organization identifiers and organization-scoped application queries help maintain separation between tenant data within the shared application.

The platform also incorporates role-based permissions to control access to protected application operations.

---

## 🛣️ Future Scope

- ☁️ Integration with Azure Blob Storage for cloud-based document storage.
- 🌐 Deployment using Azure App Service.
- 🔎 Advanced document search and filtering.
- 📊 Enhanced analytics and reporting.
- 🤝 Improved collaboration and document-sharing capabilities.
- 🔒 Additional security and access-control enhancements.

---

## 👩‍💻 Repository

**GitHub:** [AstroVault](https://github.com/diyadineep/AstroVault)
