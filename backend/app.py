
import os
from functools import wraps


import uuid
from werkzeug.utils import secure_filename


from dotenv import load_dotenv
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    jsonify,
    send_from_directory,
)
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from sqlalchemy.engine import URL
from werkzeug.security import generate_password_hash, check_password_hash

load_dotenv()

# --------------------------------------------------
# FLASK APPLICATION CONFIGURATION
# --------------------------------------------------

app = Flask(__name__)

app.config["SECRET_KEY"] = os.getenv(
    "SECRET_KEY",
    "change-this-to-a-random-secret-key",
)

database_url = URL.create(
    drivername="postgresql+psycopg2",
    username=os.getenv("DB_USER", "postgres"),
    password=os.getenv("DB_PASSWORD", ""),
    host=os.getenv("DB_HOST", "localhost"),
    port=int(os.getenv("DB_PORT", "5432")),
    database=os.getenv("DB_NAME", "ASTROVAULT_FINAL"),
)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


# --------------------------------------------------
# DATABASE HELPER FUNCTIONS
# --------------------------------------------------

def query_all(sql, params=None):
    """Execute a SELECT query and return all rows."""
    with db.engine.connect() as connection:
        return connection.execute(
            text(sql),
            params or {},
        ).all()


def execute_sql(sql, params=None):
    """Execute an INSERT, UPDATE, DELETE, or other SQL statement."""
    with db.engine.begin() as connection:
        return connection.execute(
            text(sql),
            params or {},
        )

def user_has_permission(permission_name):
    if not session.get("user_id") or not session.get("org_id"):
        return False

    sql = """
        SELECT 1
        FROM user_role ur
        JOIN role r
            ON r.role_id = ur.role_id
        JOIN role_permission rp
            ON rp.role_id = r.role_id
        JOIN permission p
            ON p.permission_id = rp.permission_id
        JOIN app_user u
            ON u.user_id = ur.user_id
        WHERE ur.user_id = :user_id
          AND u.org_id = :org_id
          AND u.status = 'Active'
          AND ur.status = 'Active'
          AND r.status = 'Active'
          AND p.status = 'Active'
          AND p.permission_name = :permission_name
        LIMIT 1
    """

    rows = query_all(sql, {
        "user_id": session["user_id"],
        "org_id": session["org_id"],
        "permission_name": permission_name
    })

    return len(rows) > 0

# --------------------------------------------------
# LOGIN CHECK
# --------------------------------------------------

def login_required(f=None):
    """
    Supports both existing styles:

        if not login_required():
            return redirect(url_for("login"))

    and:

        @login_required
    """

    if f is None:
        if not session.get("user_id"):
            flash("Please log in first.", "error")
            return False

        return True

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please log in first.", "error")
            return redirect(url_for("login"))

        return f(*args, **kwargs)

    return decorated_function


# --------------------------------------------------
# ACTIVITY LOGGING HELPER
# --------------------------------------------------


def log_activity(
    action_type,
    entity_type=None,
    entity_id=None,
    description=None,
):
    """Record an action performed by the logged-in user."""

    if "user_id" not in session or "org_id" not in session:
        return

    execute_sql(
        """
        INSERT INTO activity_log (
            user_id,
            org_id,
            action_type,
            entity_type,
            entity_id,
            description,
            log_time,
            ip_address
        )
        VALUES (
            :user_id,
            :org_id,
            :action_type,
            :entity_type,
            :entity_id,
            :description,
            CURRENT_TIMESTAMP,
            :ip_address
        )
        """,
        {
            "user_id": session["user_id"],
            "org_id": session["org_id"],
            "action_type": action_type,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "description": description,
            "ip_address": request.remote_addr,
        },
    )


# --------------------------------------------------
# HOME AND DATABASE CONNECTION TEST
# --------------------------------------------------

@app.route("/")
def home():
    session.clear()
    return redirect(url_for("login"))


@app.route("/db-test")
def db_test():
    try:
        with db.engine.connect() as connection:
            connection.execute(text("SELECT 1"))

        return jsonify({
            "status": "success",
            "message": "PostgreSQL connection successful",
        })

    except Exception:
        app.logger.exception("Database connection failed")

        return jsonify({
            "status": "error",
            "message": "Database connection failed",
        }), 500

# --------------------------------------------------
# REGISTRATION
# --------------------------------------------------

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        first_name = request.form.get("first_name", "").strip()
        last_name = request.form.get("last_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone_no = request.form.get("phone_no", "").strip()
        org_text = request.form.get("org_id", "").strip()
        password = request.form.get("password", "")

        if not all([
            first_name, last_name, email,
            phone_no, org_text, password
        ]):
            flash("Please fill in all required fields.", "error")
            return redirect(url_for("register"))

        if len(password) < 8:
            flash(
                "Password must contain at least 8 characters.",
                "error"
            )
            return redirect(url_for("register"))

        try:
            org_id = int(org_text)

            with db.engine.begin() as connection:
                organization = connection.execute(text("""
                    SELECT organization_id
                    FROM organization
                    WHERE organization_id = :org_id
                      AND status = 'Active'
                """), {"org_id": org_id}).first()

                if not organization:
                    flash(
                        "Organization not found or inactive.",
                        "error"
                    )
                    return redirect(url_for("register"))

                existing = connection.execute(text("""
                    SELECT user_id
                    FROM app_user
                    WHERE LOWER(email) = :email
                """), {"email": email}).first()

                if existing:
                    flash(
                        "That email is already registered.",
                        "error"
                    )
                    return redirect(url_for("register"))

                new_id = connection.execute(text("""
                    SELECT COALESCE(MAX(user_id), 2000) + 1
                    FROM app_user
                """)).scalar_one()

                connection.execute(text("""
                    INSERT INTO app_user (
                        user_id,
                        org_id,
                        first_name,
                        last_name,
                        email,
                        password_hash,
                        phone_no,
                        status
                    )
                    VALUES (
                        :id,
                        :org,
                        :first,
                        :last,
                        :email,
                        :password,
                        :phone,
                        'Active'
                    )
                """), {
                    "id": new_id,
                    "org": org_id,
                    "first": first_name,
                    "last": last_name,
                    "email": email,
                    "password": generate_password_hash(password),
                    "phone": phone_no,
                })

            flash(
                "Registration successful. Please log in.",
                "success"
            )
            return redirect(url_for("login"))

        except ValueError:
            flash("Organization ID must be a number.", "error")

        except Exception:
            app.logger.exception("Registration failed")
            flash(
                "Registration failed. Check the terminal.",
                "error"
            )

        return redirect(url_for("register"))

    return render_template("register.html")


# --------------------------------------------------
# LOGIN
# --------------------------------------------------

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        try:
            user_rows = query_all("""
                SELECT
                    user_id,
                    first_name,
                    email,
                    password_hash,
                    org_id,
                    status
                FROM app_user
                WHERE LOWER(email) = :email
            """, {"email": email})

            user = user_rows[0] if user_rows else None

            if (
                user
                and user[5] == "Active"
                and check_password_hash(user[3], password)
            ):
                session.clear()
                session["user_id"] = user[0]
                session["org_id"] = user[4]
                session["user_name"] = user[1]

                execute_sql("""
                    UPDATE app_user
                    SET last_login_date = CURRENT_TIMESTAMP,
                        updated_date = CURRENT_TIMESTAMP
                    WHERE user_id = :id
                """, {"id": user[0]})

                return redirect(url_for("dashboard"))

            flash(
                "Invalid email or password, or account inactive.",
                "error"
            )

        except Exception:
            app.logger.exception("Login failed")
            flash(
                "Unable to log in. Check the terminal.",
                "error"
            )

    return render_template("login.html")


# --------------------------------------------------
# LOGOUT
# --------------------------------------------------

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))


# --------------------------------------------------
# DASHBOARD
# --------------------------------------------------

@app.route("/dashboard")
def dashboard():
    if not login_required():
        return redirect(url_for("login"))

    try:
        user_rows = query_all("""
            SELECT first_name, last_name, email, org_id
            FROM app_user
            WHERE user_id = :id
              AND status = 'Active'
        """, {"id": session["user_id"]})

        if not user_rows:
            session.clear()
            flash("Your account is unavailable.", "error")
            return redirect(url_for("login"))

        role_rows = query_all("""
            SELECT r.role_name
            FROM user_role ur
            JOIN role r ON r.role_id = ur.role_id
            WHERE ur.user_id = :user_id
            AND ur.status = 'Active'
            AND r.status = 'Active'
            ORDER BY r.role_id
            LIMIT 1
        """, {"user_id": session["user_id"]})

        user_role = role_rows[0][0] if role_rows else "No role assigned"

        
        org_id = session["org_id"]

        total_orgs = query_all("""
            SELECT COUNT(*)
            FROM organization
            WHERE organization_id = :org_id
        """, {"org_id": org_id})[0][0]

        total_users = query_all("""
            SELECT COUNT(*)
            FROM app_user
            WHERE org_id = :org_id
        """, {"org_id": org_id})[0][0]

        total_projects = query_all("""
            SELECT COUNT(*)
            FROM project
            WHERE org_id = :org_id
        """, {"org_id": org_id})[0][0]

        total_files = query_all("""
            SELECT COUNT(*)
            FROM "file" f
            JOIN folder fo ON fo.folder_id = f.folder_id
            JOIN project p ON p.project_id = fo.project_id
            WHERE p.org_id = :org_id
        """, {"org_id": org_id})[0][0]


        projects_data = query_all("""
            SELECT
                project_id,
                project_name,
                project_type,
                status
            FROM project
            WHERE org_id = :org_id
            ORDER BY created_date DESC NULLS LAST, project_id DESC
            LIMIT 5
        """, {"org_id": session["org_id"]})

        recent_files = query_all("""
            SELECT
                f.file_id,
                f.file_name,
                f.file_type,
                f.upload_date
            FROM "file" f
            JOIN folder fo ON fo.folder_id = f.folder_id
            JOIN project p ON p.project_id = fo.project_id
            WHERE p.org_id = :org_id
            ORDER BY f.upload_date DESC NULLS LAST, f.file_id DESC
            LIMIT 5
        """, {"org_id": session["org_id"]})

        activities = query_all("""
            SELECT
                action_type,
                description,
                log_time
            FROM activity_log
            WHERE org_id = :org_id
            ORDER BY log_time DESC NULLS LAST, log_id DESC
            LIMIT 5
        """, {"org_id": session["org_id"]})

        return render_template(
            "dashboard.html",
            user=user_rows[0],
            user_role=user_role,
            total_orgs=total_orgs,
            total_users=total_users,
            total_projects=total_projects,
            total_files=total_files,
            projects=projects_data,
            recent_files=recent_files,
            activities=activities
        )

    except Exception:
        app.logger.exception("Dashboard failed")
        return (
            "Unable to load dashboard. Check the VS Code terminal.",
            500
        )


# --------------------------------------------------
# USER MANAGEMENT
# --------------------------------------------------

@app.route("/users")
def users():
    if not login_required():
        return redirect(url_for("login"))


    try:
        
        
        users_list = query_all("""
            SELECT
                u.user_id,
                u.first_name,
                u.middle_name,
                u.last_name,
                u.email,
                u.phone_no,
                u.status,
                o.organization_name
            FROM app_user u
            JOIN organization o
                ON o.organization_id = u.org_id
            WHERE u.org_id = :org_id
            ORDER BY u.user_id
        """, {"org_id": session["org_id"]})

        organizations = query_all("""
            SELECT organization_id, organization_name
            FROM organization
            WHERE organization_id = :org_id
            AND status = 'Active'
            ORDER BY organization_name
        """, {"org_id": session["org_id"]})

        roles = query_all("""
            SELECT role_id, role_name
            FROM role
            WHERE status = 'Active'
            ORDER BY role_id
        """)

        return render_template(
            "users.html",
            users=users_list,
            users_list=users_list,
            organizations=organizations,
            roles=roles
        )

    except Exception:
        app.logger.exception("Users page failed")
        return "Unable to load users. Check the terminal.", 500


# --------------------------------------------------
# ADD USER
# --------------------------------------------------


@app.route("/users/add", methods=["POST"])
def add_user():
    if not login_required():
        return redirect(url_for("login"))

    if not user_has_permission("MANAGE_USERS"):
        flash("You do not have permission to manage users.", "error")
        return redirect(url_for("dashboard"))


    try:
        user_id = int(request.form["user_id"])
        org_id = int(request.form["org_id"])
        role_id = int(request.form["role_id"])

        first_name = request.form["first_name"].strip()
        middle_name = request.form.get("middle_name", "").strip() or None
        last_name = request.form["last_name"].strip()
        email = request.form["email"].strip().lower()
        phone = request.form.get("phone_no", "").strip()
        password = request.form.get("password", "")
        status = request.form.get("status", "Active")

        if not all([first_name, last_name, email, password]):
            flash("Please complete all required fields.", "error")
            return redirect(url_for("users"))

        if len(password) < 8:
            flash("Password must contain at least 8 characters.", "error")
            return redirect(url_for("users"))

        if status not in ("Active", "Inactive"):
            flash("Invalid user status.", "error")
            return redirect(url_for("users"))

        if org_id != session["org_id"]:
            flash("You can only add users to your organization.", "error")
            return redirect(url_for("users"))

        # Check for an existing email before inserting.
        existing_email = query_all("""
            SELECT user_id
            FROM app_user
            WHERE LOWER(email) = :email
        """, {"email": email})

        if existing_email:
            flash("That email is already registered.", "error")
            return redirect(url_for("users"))

        valid_role = query_all("""
            SELECT role_id
            FROM role
            WHERE role_id = :role_id
            AND status = 'Active'
        """, {"role_id": role_id})

        if not valid_role:
            flash("Please select a valid active role.", "error")
            return redirect(url_for("users"))

        execute_sql("""
            INSERT INTO app_user (
                user_id,
                org_id,
                first_name,
                middle_name,
                last_name,
                email,
                password_hash,
                phone_no,
                status
            )
            VALUES (
                :id,
                :org,
                :first,
                :middle,
                :last,
                :email,
                :password,
                :phone,
                :status
            )
        """, {
            "id": user_id,
            "org": org_id,
            "first": first_name,
            "middle": middle_name,
            "last": last_name,
            "email": email,
            "password": generate_password_hash(password),
            "phone": phone or None,
            "status": status
        })

        execute_sql("""
            INSERT INTO user_role (
                user_id,
                role_id,
                assigned_date,
                assigned_by,
                status
            )
            VALUES (
                :user_id,
                :role_id,
                CURRENT_TIMESTAMP,
                :assigned_by,
                'Active'
            )
        """, {
            "user_id": user_id,
            "role_id": role_id,
            "assigned_by": session["user_id"]
        })

        log_activity(
            "CREATE",
            "User",
            user_id,
            f"Created user account {user_id}"
        )

        flash("User added successfully.", "success")

    except Exception:
        app.logger.exception("Adding user failed")
        flash(
            "Could not add user. Check the ID, email, and database constraints.",
            "error"
        )

    return redirect(url_for("users"))


# --------------------------------------------------
# EDIT USER
# --------------------------------------------------

@app.route("/users/edit/<int:user_id>", methods=["POST"])
def edit_user(user_id):
    if not login_required():
        return redirect(url_for("login"))

    if not user_has_permission("MANAGE_USERS"):
        flash("You do not have permission to manage users.", "error")
        return redirect(url_for("dashboard"))

        # Keep your existing code here

    try:
        first_name = request.form.get("first_name", "").strip()
        middle_name = request.form.get("middle_name", "").strip() or None
        last_name = request.form.get("last_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone_no = request.form.get("phone_no", "").strip()
        status = request.form.get("status", "Active")

        if not first_name or not last_name or not email:
            flash(
                "First name, last name and email are required.",
                "error"
            )
            return redirect(url_for("users"))

        if status not in ("Active", "Inactive"):
            flash("Invalid user status.", "error")
            return redirect(url_for("users"))

        if user_id == session["user_id"] and status != "Active":
            flash("You cannot deactivate your own account.", "error")
            return redirect(url_for("users"))

        # Prevent another user from using the same email.
        duplicate_email = query_all("""
            SELECT user_id
            FROM app_user
            WHERE LOWER(email) = :email
              AND user_id <> :user_id
        """, {
            "email": email,
            "user_id": user_id
        })

        if duplicate_email:
            flash("That email is already in use.", "error")
            return redirect(url_for("users"))

        result = execute_sql("""
            UPDATE app_user
            SET first_name = :first_name,
                middle_name = :middle_name,
                last_name = :last_name,
                email = :email,
                phone_no = :phone_no,
                status = :status,
                updated_date = CURRENT_TIMESTAMP
            WHERE user_id = :user_id
              AND org_id = :org_id
        """, {
            "first_name": first_name,
            "middle_name": middle_name,
            "last_name": last_name,
            "email": email,
            "phone_no": phone_no or None,
            "status": status,
            "user_id": user_id,
            "org_id": session["org_id"]
        })

        if result.rowcount == 0:
            flash("User not found in your organization.", "error")
        else:
            log_activity(
                "UPDATE",
                "User",
                user_id,
                f"Updated user account {user_id}"
            )
            flash("User updated successfully.", "success")

    except Exception:
        app.logger.exception("Editing user failed")
        flash(
            "Could not update user. Check the email and entered values.",
            "error"
        )

    return redirect(url_for("users"))


# --------------------------------------------------
# ARCHIVE USER
# --------------------------------------------------

@app.route("/users/archive/<int:user_id>", methods=["POST"])
def archive_user(user_id):
    if not login_required():
        return redirect(url_for("login"))

    if not user_has_permission("MANAGE_USERS"):
        flash("You do not have permission to manage users.", "error")
        return redirect(url_for("dashboard"))


    if user_id == session.get("user_id"):
        flash("You cannot archive your own account.", "error")
        return redirect(url_for("users"))

    try:
        result = execute_sql("""
            UPDATE app_user
            SET status = 'Inactive',
                updated_date = CURRENT_TIMESTAMP
            WHERE user_id = :id
              AND org_id = :org_id
              AND status = 'Active'
        """, {
            "id": user_id,
            "org_id": session["org_id"]
        })

        if result.rowcount:
            log_activity(
                "ARCHIVE",
                "User",
                user_id,
                f"Archived user account {user_id}"
            )
            flash("User archived successfully.", "success")
        else:
            flash("User not found or already inactive.", "error")

    except Exception:
        app.logger.exception("Archiving user failed")
        flash("Could not archive user. Check the terminal.", "error")

    return redirect(url_for("users"))

# --------------------------------------------------
# PROJECT MANAGEMENT
# --------------------------------------------------

@app.route("/projects")
def projects():
    if not login_required():
        return redirect(url_for("login"))

    try:
        org_id = session["org_id"]

        
        
        project_rows = query_all("""
            SELECT
                p.project_id,
                p.project_name,
                p.project_type,
                p.start_date,
                p.end_date,
                p.status,
                o.organization_name,
                creator.first_name,
                creator.last_name,
                p.description,
                p.created_by,
                p.org_id
            FROM project p
            JOIN organization o
                ON o.organization_id = p.org_id
            LEFT JOIN app_user creator
                ON creator.user_id = p.created_by
            WHERE p.org_id = :org_id
            ORDER BY p.project_id DESC
        """, {"org_id": org_id})


        organizations = query_all("""
            SELECT organization_id, organization_name
            FROM organization
            WHERE organization_id = :org_id
              AND status = 'Active'
            ORDER BY organization_name
        """, {"org_id": org_id})

        users_list = query_all("""
            SELECT user_id, first_name, last_name
            FROM app_user
            WHERE org_id = :org_id
              AND status = 'Active'
            ORDER BY user_id
        """, {"org_id": org_id})

        return render_template(
            "projects.html",
            projects=project_rows,
            organizations=organizations,
            users=users_list
        )

    except Exception:
        app.logger.exception("Projects page failed")
        return "Unable to load projects. Check the terminal.", 500


# --------------------------------------------------
# ADD PROJECT
# --------------------------------------------------

@app.route("/projects/add", methods=["POST"])
def add_project():
    if not login_required():
        return redirect(url_for("login"))

    if not user_has_permission("CREATE_PROJECT"):
        flash("You do not have permission to create projects.", "error")
        return redirect(url_for("dashboard"))

    try:
        project_id = int(request.form["project_id"])
        org_id = int(request.form["org_id"])
        project_name = request.form["project_name"].strip()

        description = request.form.get("description", "").strip()
        project_type = request.form.get("project_type", "").strip()
        start_date = request.form.get("start_date") or None
        end_date = request.form.get("end_date") or None
        status = request.form.get("status", "Planning")

        if not project_name:
            flash("Project name is required.", "error")
            return redirect(url_for("projects"))

        if org_id != session["org_id"]:
            flash("Choose your own organization.", "error")
            return redirect(url_for("projects"))

        if status not in (
            "Planning", "Active", "Completed", "On Hold", "Cancelled"
        ):
            flash("Invalid project status.", "error")
            return redirect(url_for("projects"))

        execute_sql("""
            INSERT INTO project (
                project_id,
                org_id,
                project_name,
                description,
                project_type,
                start_date,
                end_date,
                status,
                created_by
            )
            VALUES (
                :id,
                :org,
                :name,
                :description,
                :type,
                :start_date,
                :end_date,
                :status,
                :created_by
            )
        """, {
            "id": project_id,
            "org": org_id,
            "name": project_name,
            "description": description or None,
            "type": project_type or None,
            "start_date": start_date,
            "end_date": end_date,
            "status": status,
            "created_by": session["user_id"]
        })

        log_activity(
            "CREATE",
            "Project",
            project_id,
            f"Created project {project_name}"
        )

        flash("Project added successfully.", "success")

    except Exception:
        app.logger.exception("Adding project failed")
        flash(
            "Could not add project. Check the project ID, organization, "
            "required fields and database constraints.",
            "error"
        )

    return redirect(url_for("projects"))


# --------------------------------------------------
# EDIT PROJECT
# --------------------------------------------------

@app.route("/projects/edit/<int:project_id>", methods=["POST"])
def edit_project(project_id):
    if not login_required():
        return redirect(url_for("login"))

    if not user_has_permission("UPDATE_PROJECT"):
        flash("You do not have permission to update projects.", "error")
        return redirect(url_for("dashboard"))

    try:
        project_name = request.form.get("project_name", "").strip()
        org_id = int(request.form["org_id"])

        if not project_name:
            flash("Project name is required.", "error")
            return redirect(url_for("projects"))

        if org_id != session["org_id"]:
            flash("Choose your own organization.", "error")
            return redirect(url_for("projects"))

        description = request.form.get("description", "").strip()
        project_type = request.form.get("project_type", "").strip()
        start_date = request.form.get("start_date") or None
        end_date = request.form.get("end_date") or None
        status = request.form.get("status", "Planning")

        if status not in (
            "Planning", "Active", "Completed", "On Hold", "Cancelled"
        ):
            flash("Invalid project status.", "error")
            return redirect(url_for("projects"))

        result = execute_sql("""
            UPDATE project
            SET project_name = :name,
                description = :description,
                project_type = :type,
                start_date = :start_date,
                end_date = :end_date,
                status = :status
            WHERE project_id = :id
              AND org_id = :session_org
        """, {
            "id": project_id,
            "name": project_name,
            "description": description or None,
            "type": project_type or None,
            "start_date": start_date,
            "end_date": end_date,
            "status": status,
            "session_org": session["org_id"]
        })

        if result.rowcount:
            log_activity(
                "UPDATE",
                "Project",
                project_id,
                f"Updated project {project_name}"
            )
            flash("Project updated successfully.", "success")
        else:
            flash("Project not found in your organization.", "error")

    except Exception:
        app.logger.exception("Editing project failed")
        flash(
            "Could not update project. Check the entered values "
            "and database constraints.",
            "error"
        )

    return redirect(url_for("projects"))

# ============================================================
# PART 5: PROJECT MEMBERS MANAGEMENT
# ============================================================

@app.route("/members")
def members():
    if not login_required():
        return redirect(url_for("login"))

      

    try:
        org_id = session["org_id"]

        members_data = query_all("""
            SELECT
                pm.member_id,
                pm.project_id,
                p.project_name,
                pm.user_id,
                u.first_name,
                u.last_name,
                pm.project_role,
                pm.joined_date,
                pm.status,
                pm.assigned_by,
                assigner.first_name AS assigner_first_name,
                assigner.last_name AS assigner_last_name
            FROM project_member pm
            JOIN project p
                ON p.project_id = pm.project_id
            JOIN app_user u
                ON u.user_id = pm.user_id
            LEFT JOIN app_user assigner
                ON assigner.user_id = pm.assigned_by
            WHERE p.org_id = :org_id
            ORDER BY pm.member_id DESC
        """, {"org_id": session["org_id"]})

        projects_data = query_all("""
            SELECT project_id, project_name
            FROM project
            WHERE org_id = :org_id
            ORDER BY project_name
        """, {"org_id": org_id})

        users_data = query_all("""
            SELECT user_id, first_name, last_name
            FROM app_user
            WHERE org_id = :org_id
              AND status = 'Active'
            ORDER BY first_name, last_name
        """, {"org_id": org_id})

        return render_template(
            "members.html",
            members=members_data,
            projects=projects_data,
            users=users_data
        )

    except Exception:
        app.logger.exception("Project Members page failed")
        return "Unable to load Project Members. Check the terminal.", 500


@app.route("/members/add", methods=["POST"])
def add_member():
    if not login_required():
        return redirect(url_for("login"))

    if not user_has_permission("ADD_PROJECT_MEMBER"):
        flash("You do not have permission to add or edit project members.", "error")
        return redirect(url_for("dashboard"))

    try:
        member_id = int(request.form["member_id"])
        project_id = int(request.form["project_id"])
        user_id = int(request.form["user_id"])
        project_role = request.form["project_role"].strip()
        status = request.form.get("status", "Active")

        if not project_role:
            flash("Project role is required.", "error")
            return redirect(url_for("members"))

        result = execute_sql("""
            INSERT INTO project_member (
                member_id,
                project_id,
                user_id,
                project_role,
                joined_date,
                assigned_by,
                status
            )
            SELECT
                :member_id,
                p.project_id,
                u.user_id,
                :project_role,
                CURRENT_TIMESTAMP,
                :assigned_by,
                :status
            FROM project p
            JOIN app_user u
                ON u.user_id = :user_id
            WHERE p.project_id = :project_id
              AND p.org_id = :org_id
              AND u.org_id = p.org_id
              AND u.status = 'Active'
        """, {
            "member_id": member_id,
            "project_id": project_id,
            "user_id": user_id,
            "project_role": project_role,
            "assigned_by": session["user_id"],
            "status": status,
            "org_id": session["org_id"]
        })

        if result.rowcount == 0:
            flash(
                "Could not add member. Check that the project and user "
                "belong to your organization and the user is active.",
                "error"
            )
        else:
            log_activity(
                "CREATE",
                "Project Member",
                member_id,
                f"Added user {user_id} to project {project_id}"
            )
            flash("Project member added successfully.", "success")

    except Exception:
        app.logger.exception("Adding project member failed")
        flash(
            "Could not add project member. Check the ID, selected project "
            "and user, and whether this member already exists.",
            "error"
        )

    return redirect(url_for("members"))


@app.route("/members/edit/<int:member_id>", methods=["POST"])
def edit_member(member_id):
    if not login_required():
        return redirect(url_for("login"))
    if not user_has_permission("ADD_PROJECT_MEMBER"):
        flash("You do not have permission to edit project members.", "error")
        return redirect(url_for("dashboard"))

    try:
        project_id = int(request.form["project_id"])
        user_id = int(request.form["user_id"])
        project_role = request.form["project_role"].strip()
        status = request.form.get("status", "Active")

        if not project_role:
            flash("Project role is required.", "error")
            return redirect(url_for("members"))

        result = execute_sql("""
            UPDATE project_member pm
            SET project_id = p.project_id,
                user_id = u.user_id,
                project_role = :project_role,
                status = :status
            FROM project p, app_user u
            WHERE pm.member_id = :member_id
              AND p.project_id = :project_id
              AND u.user_id = :user_id
              AND p.org_id = :org_id
              AND u.org_id = p.org_id
              AND u.status = 'Active'
              AND EXISTS (
                  SELECT 1
                  FROM project original_project
                  WHERE original_project.project_id = pm.project_id
                    AND original_project.org_id = :org_id
              )
        """, {
            "member_id": member_id,
            "project_id": project_id,
            "user_id": user_id,
            "project_role": project_role,
            "status": status,
            "org_id": session["org_id"]
        })

        if result.rowcount == 0:
            flash(
                "Could not update member. Check the selected project and "
                "user, and confirm the member belongs to your organization.",
                "error"
            )
        else:
            log_activity(
                "UPDATE",
                "Project Member",
                member_id,
                f"Updated membership for user {user_id} "
                f"in project {project_id}"
            )
            flash("Project member updated successfully.", "success")

    except Exception:
        app.logger.exception("Editing project member failed")
        flash(
            "Could not update project member. Check the selected values.",
            "error"
        )

    return redirect(url_for("members"))


# ============================================================
# PART 6: FOLDER MANAGEMENT
# ============================================================

@app.route("/folders")
def folders():
    if not login_required():
        return redirect(url_for("login"))

    try:
        org_id = session["org_id"]

        folders_data = query_all("""
            SELECT
                f.folder_id,
                f.folder_name,
                p.project_name,
                parent.folder_name AS parent_folder_name,
                f.description,
                creator.first_name AS creator_first_name,
                creator.last_name AS creator_last_name,
                f.created_date,
                f.status,
                f.project_id,
                f.parent_folder_id
            FROM folder f
            JOIN project p
                ON p.project_id = f.project_id
            LEFT JOIN folder parent
                ON parent.folder_id = f.parent_folder_id
            LEFT JOIN app_user creator
                ON creator.user_id = f.created_by
            WHERE p.org_id = :org_id
            ORDER BY f.folder_id DESC
        """, {"org_id": session["org_id"]})

        projects_data = query_all("""
            SELECT project_id, project_name
            FROM project
            WHERE org_id = :org_id
            ORDER BY project_name
        """, {"org_id": session["org_id"]})

        parent_folders = query_all("""
            SELECT f.folder_id, f.folder_name, f.project_id
            FROM folder f
            JOIN project p
                ON p.project_id = f.project_id
            WHERE p.org_id = :org_id
              AND f.status = 'Active'
            ORDER BY f.folder_name
        """, {"org_id": org_id})

        return render_template(
            "folders.html",
            folders=folders_data,
            projects=projects_data,
            parent_folders=parent_folders
        )

    except Exception:
        app.logger.exception("Folder Management page failed")
        return "Unable to load folders. Check the terminal.", 500


@app.route("/folders/add", methods=["POST"])
def add_folder():
    if not login_required():
        return redirect(url_for("login"))

    if not user_has_permission("CREATE_FOLDER"):
        flash("You do not have permission to modify folders.", "error")
        return redirect(url_for("dashboard"))

    try:
        folder_id = int(request.form["folder_id"])
        project_id = int(request.form["project_id"])
        parent_value = request.form.get("parent_folder_id", "").strip()
        parent_folder_id = int(parent_value) if parent_value else None
        folder_name = request.form["folder_name"].strip()
        description = request.form.get("description", "").strip()
        status = request.form.get("status", "Active")

        if not folder_name:
            flash("Folder name is required.", "error")
            return redirect(url_for("folders"))

        valid_project = query_all("""
            SELECT project_id
            FROM project
            WHERE project_id = :project_id
              AND org_id = :org_id
        """, {
            "project_id": project_id,
            "org_id": session["org_id"]
        })

        if not valid_project:
            flash("Choose a project from your organization.", "error")
            return redirect(url_for("folders"))

        if parent_folder_id is not None:
            valid_parent = query_all("""
                SELECT folder_id
                FROM folder
                WHERE folder_id = :parent_id
                  AND project_id = :project_id
                  AND status = 'Active'
            """, {
                "parent_id": parent_folder_id,
                "project_id": project_id
            })

            if not valid_parent:
                flash(
                    "Choose an active parent folder from the same project.",
                    "error"
                )
                return redirect(url_for("folders"))

        execute_sql("""
            INSERT INTO folder (
                folder_id,
                project_id,
                parent_folder_id,
                folder_name,
                description,
                created_by,
                created_date,
                updated_date,
                status
            )
            VALUES (
                :folder_id,
                :project_id,
                :parent_folder_id,
                :folder_name,
                :description,
                :created_by,
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP,
                :status
            )
        """, {
            "folder_id": folder_id,
            "project_id": project_id,
            "parent_folder_id": parent_folder_id,
            "folder_name": folder_name,
            "description": description or None,
            "created_by": session["user_id"],
            "status": status
        })

        log_activity(
            "CREATE",
            "Folder",
            folder_id,
            f"Created folder {folder_name}"
        )
        flash("Folder created successfully.", "success")

    except Exception:
        app.logger.exception("Creating folder failed")
        flash(
            "Could not create the folder. Check the folder ID, "
            "selected project, parent folder and entered values.",
            "error"
        )

    return redirect(url_for("folders"))


@app.route("/folders/edit/<int:folder_id>", methods=["POST"])
def edit_folder(folder_id):
    if not login_required():
        return redirect(url_for("login"))

    if not user_has_permission("CREATE_FOLDER"):
        flash("You do not have permission to modify folders.", "error")
        return redirect(url_for("dashboard"))

    try:
        project_id = int(request.form["project_id"])
        parent_value = request.form.get("parent_folder_id", "").strip()
        parent_folder_id = int(parent_value) if parent_value else None
        folder_name = request.form["folder_name"].strip()
        description = request.form.get("description", "").strip()
        status = request.form.get("status", "Active")
        org_id = session["org_id"]

        if not folder_name:
            flash("Folder name is required.", "error")
            return redirect(url_for("folders"))

        # Confirm the target project belongs to this organization.
        valid_project = query_all("""
            SELECT project_id
            FROM project
            WHERE project_id = :project_id
              AND org_id = :org_id
        """, {
            "project_id": project_id,
            "org_id": org_id
        })

        if not valid_project:
            flash("Choose a project from your organization.", "error")
            return redirect(url_for("folders"))

        # Confirm the folder being edited belongs to this organization.
        existing_folder = query_all("""
            SELECT f.folder_id
            FROM folder f
            JOIN project p ON p.project_id = f.project_id
            WHERE f.folder_id = :folder_id
              AND p.org_id = :org_id
        """, {
            "folder_id": folder_id,
            "org_id": org_id
        })

        if not existing_folder:
            flash("Folder not found in your organization.", "error")
            return redirect(url_for("folders"))

        if parent_folder_id is not None:
            if parent_folder_id == folder_id:
                flash("A folder cannot be its own parent.", "error")
                return redirect(url_for("folders"))

            valid_parent = query_all("""
                SELECT f.folder_id
                FROM folder f
                JOIN project p ON p.project_id = f.project_id
                WHERE f.folder_id = :parent_id
                  AND f.project_id = :project_id
                  AND p.org_id = :org_id
                  AND f.status = 'Active'
            """, {
                "parent_id": parent_folder_id,
                "project_id": project_id,
                "org_id": org_id
            })

            if not valid_parent:
                flash(
                    "Choose an active parent folder from the same project.",
                    "error"
                )
                return redirect(url_for("folders"))

            # Prevent placing a folder inside its own descendant.
            descendants = query_all("""
                WITH RECURSIVE folder_tree AS (
                    SELECT folder_id
                    FROM folder
                    WHERE parent_folder_id = :folder_id

                    UNION ALL

                    SELECT child.folder_id
                    FROM folder child
                    JOIN folder_tree tree
                      ON child.parent_folder_id = tree.folder_id
                )
                SELECT folder_id
                FROM folder_tree
                WHERE folder_id = :parent_id
            """, {
                "folder_id": folder_id,
                "parent_id": parent_folder_id
            })

            if descendants:
                flash(
                    "A folder cannot be moved inside one of its descendants.",
                    "error"
                )
                return redirect(url_for("folders"))

        result = execute_sql("""
            UPDATE folder
            SET project_id = :project_id,
                parent_folder_id = :parent_folder_id,
                folder_name = :folder_name,
                description = :description,
                status = :status,
                updated_date = CURRENT_TIMESTAMP
            WHERE folder_id = :folder_id
              AND EXISTS (
                  SELECT 1
                  FROM project
                  WHERE project.project_id = :project_id
                    AND project.org_id = :org_id
              )
              AND EXISTS (
                  SELECT 1
                  FROM project old_project
                  JOIN folder old_folder
                    ON old_folder.project_id = old_project.project_id
                  WHERE old_folder.folder_id = :folder_id
                    AND old_project.org_id = :org_id
              )
        """, {
            "folder_id": folder_id,
            "project_id": project_id,
            "parent_folder_id": parent_folder_id,
            "folder_name": folder_name,
            "description": description or None,
            "status": status,
            "org_id": org_id
        })

        if result.rowcount:
            log_activity(
                "UPDATE",
                "Folder",
                folder_id,
                f"Updated folder {folder_name}"
            )
            flash("Folder updated successfully.", "success")
        else:
            flash("Folder not found in your organization.", "error")

    except Exception:
        app.logger.exception("Updating folder failed")
        flash(
            "Could not update the folder. Check the entered values.",
            "error"
        )

    return redirect(url_for("folders"))


# ============================================================
# PART 7A: FILE MANAGEMENT
# ============================================================

@app.route("/files")
def files():
    if not login_required():
        return redirect(url_for("login"))

    try:
        org_id = session["org_id"]

        files_data = query_all("""
            SELECT
                f.file_id,
                f.file_name,
                f.file_type,
                f.file_size,
                f.current_version,
                fo.folder_name,
                p.project_name,
                u.first_name,
                u.last_name,
                f.upload_date,
                f.status,
                f.description,
                f.folder_id
            FROM file f
            JOIN folder fo ON fo.folder_id = f.folder_id
            JOIN project p ON p.project_id = fo.project_id
            JOIN app_user u ON u.user_id = f.uploaded_by
            WHERE p.org_id = :org_id
                AND p.org_id = :org_id
            ORDER BY f.file_id DESC
        """, {"org_id": session["org_id"]})

        folders_data = query_all("""
            SELECT
                f.folder_id,
                f.folder_name,
                f.project_id,
                p.project_name
            FROM folder f
            JOIN project p ON p.project_id = f.project_id
              AND f.status = 'Active'
            ORDER BY p.project_name, f.folder_name
        """)

        return render_template(
            "files.html",
            files=files_data,
            folders=folders_data
        )

    except Exception:
        app.logger.exception("File Management page failed")
        return "Unable to load files. Check the terminal.", 500


@app.route("/files/add", methods=["POST"])
def add_file():
    if not login_required():
        return redirect(url_for("login"))

    if not user_has_permission("UPLOAD_FILE"):
        flash("You do not have permission to upload files.", "error")
        return redirect(url_for("dashboard"))

    saved_path = None

    try:
        
        folder_id = int(request.form["folder_id"])
        description = request.form.get("description", "").strip()
        uploaded_file = request.files.get("uploaded_file")

        if not uploaded_file or not uploaded_file.filename:
            flash("Please select a file to upload.", "error")
            return redirect(url_for("files"))

        original_name = secure_filename(uploaded_file.filename)

        if not original_name:
            flash("The selected filename is invalid.", "error")
            return redirect(url_for("files"))

        valid_folder = query_all("""
            SELECT fo.folder_id
            FROM folder fo
            JOIN project p ON p.project_id = fo.project_id
            WHERE fo.folder_id = :folder_id
              AND p.org_id = :org_id
              AND fo.status = 'Active'
        """, {
            "folder_id": folder_id,
            "org_id": session["org_id"]
        })

        if not valid_folder:
            flash(
                "Choose an active folder from your organization.",
                "error"
            )
            return redirect(url_for("files"))

        upload_folder = os.path.join(app.root_path, "uploads")
        os.makedirs(upload_folder, exist_ok=True)

        stored_name = f"{uuid.uuid4().hex}_{original_name}"
        saved_path = os.path.join(upload_folder, stored_name)

        uploaded_file.save(saved_path)

        file_size = os.path.getsize(saved_path)
        file_type = os.path.splitext(original_name)[1].lower().lstrip(".")
        relative_path = os.path.join(
            "uploads", stored_name
        ).replace("\\", "/")

        result = execute_sql("""
            INSERT INTO file (
                folder_id,
                file_name,
                file_type,
                file_size,
                blob_path,
                uploaded_by,
                current_version,
                upload_date,
                updated_date,
                status,
                description
            )
            VALUES (
                :folder_id,
                :file_name,
                :file_type,
                :file_size,
                :blob_path,
                :uploaded_by,
                1,
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP,
                'Active',
                :description
            )
            RETURNING file_id
        """, {
            "folder_id": folder_id,
            "file_name": original_name,
            "file_type": file_type or None,
            "file_size": file_size,
            "blob_path": relative_path,
            "uploaded_by": session["user_id"],
            "description": description or None
        })
        file_id = result.scalar_one()

        log_activity(
            "CREATE",
            "File",
            file_id,
            f"Uploaded file {original_name}"
        )
        flash("File uploaded successfully.", "success")

    except Exception:
        if saved_path and os.path.exists(saved_path):
            try:
                os.remove(saved_path)
            except OSError:
                app.logger.exception("Could not remove failed upload")

        app.logger.exception("File upload failed")
        flash(
            "Upload failed. Check the file ID, folder, and database error.",
            "error"
        )

    return redirect(url_for("files"))


@app.route("/files/edit/<int:file_id>", methods=["POST"])
def edit_file(file_id):
    if not login_required():
        return redirect(url_for("login"))
    if not user_has_permission("UPDATE_FILE"):
        flash("You do not have permission to edit files.", "error")
        return redirect(url_for("dashboard"))

    try:
        folder_id = int(request.form["folder_id"])
        file_name = request.form["file_name"].strip()
        description = request.form.get("description", "").strip()
        status = request.form.get("status", "Active")
        org_id = session["org_id"]

        if not file_name:
            flash("File name is required.", "error")
            return redirect(url_for("files"))

        if status not in ("Active", "Archived", "Deleted"):
            flash("Invalid file status.", "error")
            return redirect(url_for("files"))

        valid_folder = query_all("""
            SELECT fo.folder_id
            FROM folder fo
            JOIN project p ON p.project_id = fo.project_id
            WHERE fo.folder_id = :folder_id
              AND p.org_id = :org_id
              AND fo.status = 'Active'
        """, {
            "folder_id": folder_id,
            "org_id": org_id
        })

        if not valid_folder:
            flash(
                "Choose an active folder from your organization.",
                "error"
            )
            return redirect(url_for("files"))

        result = execute_sql("""
            UPDATE file
            SET folder_id = :folder_id,
                file_name = :file_name,
                description = :description,
                status = :status,
                updated_date = CURRENT_TIMESTAMP
            WHERE file_id = :file_id
              AND EXISTS (
                  SELECT 1
                  FROM folder fo
                  JOIN project p ON p.project_id = fo.project_id
                  WHERE fo.folder_id = file.folder_id
                    AND p.org_id = :org_id
              )
        """, {
            "file_id": file_id,
            "folder_id": folder_id,
            "file_name": file_name,
            "description": description or None,
            "status": status,
            "org_id": org_id
        })

        if result.rowcount:
            log_activity(
                "UPDATE",
                "File",
                file_id,
                f"Updated file metadata for {file_name}"
            )
            flash("File details updated successfully.", "success")
        else:
            flash("File not found in your organization.", "error")

    except Exception:
        app.logger.exception("File metadata update failed")
        flash(
            "Could not update the file details. Check the terminal.",
            "error"
        )

    return redirect(url_for("files"))

@app.route("/files/download/<int:file_id>")
def download_file(file_id):
    if not login_required():
        return redirect(url_for("login"))

    if not user_has_permission("DOWNLOAD_FILE"):
        flash("You do not have permission to download files.", "error")
        return redirect(url_for("dashboard"))

    try:
        file_rows = query_all("""
            SELECT f.file_name, f.blob_path
            FROM file f
            JOIN folder fo ON fo.folder_id = f.folder_id
            JOIN project p ON p.project_id = fo.project_id
            WHERE f.file_id = :file_id
              AND p.org_id = :org_id
              AND f.status = 'Active'
        """, {
            "file_id": file_id,
            "org_id": session["org_id"]
        })

        if not file_rows:
            return "File not found or access denied.", 404

        file_name, blob_path = file_rows[0]

        if not blob_path:
            return "No stored file path is available.", 404

        # Serve only from the application's uploads directory.
        upload_folder = os.path.realpath(
            os.path.join(app.root_path, "uploads")
        )
        stored_path = os.path.realpath(
            os.path.join(app.root_path, blob_path)
        )

        if os.path.commonpath([upload_folder, stored_path]) != upload_folder:
            return "Invalid file path.", 400

        stored_name = os.path.basename(stored_path)

        return send_from_directory(
            upload_folder,
            stored_name,
            as_attachment=True,
            download_name=file_name
        )

    except Exception:
        app.logger.exception("File download failed")
        return "Unable to download file. Check the terminal.", 500


# ============================================================
# PART 7B: FILE VERSION HISTORY
# ============================================================

@app.route("/versions")
def versions():
    if not login_required():
        return redirect(url_for("login"))

    if not user_has_permission("VIEW_VERSION_HISTORY"):
        flash("You do not have permission to view version history.", "error")
        return redirect(url_for("dashboard"))

    try:
        org_id = session["org_id"]

        versions_data = query_all("""
            SELECT
                fv.version_id,
                f.file_name,
                fv.version_number,
                fv.file_size,
                u.first_name,
                u.last_name,
                fv.uploaded_date,
                fv.change_description,
                fv.is_current,
                fv.blob_path,
                fv.file_id
            FROM file_version fv
            JOIN file f ON f.file_id = fv.file_id
            JOIN app_user u ON u.user_id = fv.uploaded_by
            JOIN folder fo ON fo.folder_id = f.folder_id
            JOIN project p ON p.project_id = fo.project_id
            WHERE p.org_id = :org_id
            ORDER BY fv.file_id, fv.version_number
        """, {"org_id": session["org_id"]})

        files_data = query_all("""
            SELECT
                f.file_id,
                f.file_name,
                f.current_version
            FROM file f
            JOIN folder fo ON fo.folder_id = f.folder_id
            JOIN project p ON p.project_id = fo.project_id
            WHERE p.org_id = :org_id
              AND f.status = 'Active'
            ORDER BY f.file_name
        """, {"org_id": session["org_id"]})

        return render_template(
            "versions.html",
            versions=versions_data,
            files=files_data
        )

    except Exception:
        app.logger.exception("File Version Management page failed")
        return "Unable to load file versions. Check the terminal.", 500


@app.route("/versions/add", methods=["POST"])
def add_version():
    if not login_required():
        return redirect(url_for("login"))

    if not user_has_permission("UPLOAD_FILE"):
        flash("You do not have permission to upload file versions.", "error")
        return redirect(url_for("dashboard"))

    saved_path = None
    db_saved = False

    try:
        file_id = int(request.form["file_id"])
        change_description = request.form.get(
            "change_description", ""
        ).strip()
        org_id = session["org_id"]

        # Validate the uploaded file.
        uploaded_file = request.files.get("uploaded_file")

        if not uploaded_file or not uploaded_file.filename:
            flash("Please select a file to upload.", "error")
            return redirect(url_for("versions"))

        original_name = secure_filename(uploaded_file.filename)

        if not original_name:
            flash("The selected filename is invalid.", "error")
            return redirect(url_for("versions"))

        # Confirm that the selected file belongs to this organization.
        owned_file = query_all("""
            SELECT f.file_id
            FROM "file" f
            JOIN folder fo ON fo.folder_id = f.folder_id
            JOIN project p ON p.project_id = fo.project_id
            WHERE f.file_id = :file_id
              AND p.org_id = :org_id
              AND f.status = 'Active'
        """, {
            "file_id": file_id,
            "org_id": org_id
        })

        if not owned_file:
            flash(
                "Select an active file belonging to your organization.",
                "error"
            )
            return redirect(url_for("versions"))

        # Save the new version under a unique filename.
        upload_folder = os.path.join(app.root_path, "uploads")
        os.makedirs(upload_folder, exist_ok=True)

        stored_name = f"{uuid.uuid4().hex}_{original_name}"
        saved_path = os.path.join(upload_folder, stored_name)

        uploaded_file.save(saved_path)

        file_size = os.path.getsize(saved_path)
        blob_path = os.path.join(
            "uploads", stored_name
        ).replace("\\", "/")

        # Insert the new version and update the current version atomically.
        with db.engine.begin() as connection:
            connection.execute(text("""
                LOCK TABLE file_version IN SHARE ROW EXCLUSIVE MODE
            """))

            latest = connection.execute(text("""
                SELECT COALESCE(MAX(version_number), 0)
                FROM file_version
                WHERE file_id = :file_id
            """), {"file_id": file_id}).scalar_one()

            new_version = int(latest) + 1

            connection.execute(text("""
                UPDATE file_version
                SET is_current = FALSE
                WHERE file_id = :file_id
            """), {"file_id": file_id})

            result = connection.execute(text("""
                INSERT INTO file_version (
                    file_id,
                    version_number,
                    blob_path,
                    file_size,
                    uploaded_by,
                    uploaded_date,
                    change_description,
                    is_current
                )
                VALUES (
                    :file_id,
                    :version_number,
                    :blob_path,
                    :file_size,
                    :uploaded_by,
                    CURRENT_TIMESTAMP,
                    :change_description,
                    TRUE
                )
                RETURNING version_id
            """), {
                "file_id": file_id,
                "version_number": new_version,
                "blob_path": blob_path,
                "file_size": file_size,
                "uploaded_by": session["user_id"],
                "change_description": change_description or None
            })

            version_id = result.scalar_one()

            connection.execute(text("""
                UPDATE "file"
                SET current_version = :version_number,
                    blob_path = :blob_path,
                    file_size = :file_size,
                    updated_date = CURRENT_TIMESTAMP
                WHERE file_id = :file_id
            """), {
                "version_number": new_version,
                "blob_path": blob_path,
                "file_size": file_size,
                "file_id": file_id
            })

        db_saved = True

        # Log the activity after the database transaction succeeds.
        log_activity(
            "CREATE",
            "File Version",
            version_id,
            f"Created version {new_version} for file {file_id}"
        )

        flash(
            f"Version {new_version} added successfully.",
            "success"
        )

    except Exception:
        # Remove the physical file only if the database transaction failed.
        if (
            saved_path
            and os.path.exists(saved_path)
            and not db_saved
        ):
            try:
                os.remove(saved_path)
            except OSError:
                app.logger.exception(
                    "Could not remove failed version upload"
                )

        app.logger.exception("Adding file version failed")
        flash(
            "Could not add the version. Check the terminal for details.",
            "error"
        )

    return redirect(url_for("versions"))


# ============================================================
# PART 7C: ACTIVITY LOGS
# ============================================================

@app.route("/activity")
def activity():
    if not login_required():
        return redirect(url_for("login"))

    if not user_has_permission("VIEW_ACTIVITY_LOG"):
        flash("You do not have permission to view activity logs.", "error")
        return redirect(url_for("dashboard"))

    try:
        
        org_id = session["org_id"]

        logs = query_all("""
            SELECT
                al.log_id,
                u.first_name,
                u.last_name,
                al.action_type,
                al.entity_type,
                al.entity_id,
                al.description,
                al.log_time,
                al.ip_address
            FROM activity_log al
            JOIN app_user u
                ON u.user_id = al.user_id
            WHERE u.org_id = :org_id
            ORDER BY al.log_time DESC NULLS LAST, al.log_id DESC
        """, {"org_id": org_id})


        return render_template("activity.html", logs=logs)

    except Exception:
        app.logger.exception("Activity Logs page failed")
        return "Unable to load activity logs. Check the terminal.", 500

# ============================================================
# RUN APPLICATION
# ============================================================

if __name__ == "__main__":
    app.run(debug=True)
