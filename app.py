import os
import smtplib
import mysql.connector

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    send_from_directory
)

from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

from matching import calculate_match_score

app = Flask(__name__)

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "change-this-secret-key"
)

UPLOAD_FOLDER = os.path.join(app.root_path, "uploads")

ALLOWED_EXTENSIONS = {
    "png",
    "jpg",
    "jpeg",
    "webp"
}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# =========================================================
# MYSQL CONFIGURATION
# =========================================================

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "22042005",
    "database": "lost_found_db"
}


# =========================================================
# EMAIL NOTIFICATION CONFIGURATION
# =========================================================
#
# The application sends email notifications through SMTP.
#
# REQUIRED:
#   EMAIL_SENDER       = email address used to SEND emails
#   EMAIL_APP_PASSWORD = SMTP/App Password for that sender account
#
# For Gmail, EMAIL_APP_PASSWORD must be a Google-generated
# App Password. Do not use the normal Gmail password.
#
# PowerShell example:
#   $env:EMAIL_SENDER="your-sender@gmail.com"
#   $env:EMAIL_APP_PASSWORD="your-16-character-app-password"
#
# IMPORTANT:
# Set these variables in the SAME terminal before running:
#   python app.py
#
# The recipient is taken automatically from the user's
# registered email address.

EMAIL_SENDER = os.environ.get("EMAIL_SENDER", "").strip()
EMAIL_APP_PASSWORD = os.environ.get("EMAIL_APP_PASSWORD", "").strip()

SMTP_HOST = os.environ.get(
    "SMTP_HOST",
    "smtp.gmail.com"
).strip()

SMTP_PORT = int(
    os.environ.get(
        "SMTP_PORT",
        "587"
    )
)


def send_notification_email(
    receiver_email,
    subject,
    message
):
    """
    Send an email notification.

    Returns True when the SMTP server accepts the message.
    Returns False when configuration, network, or SMTP
    authentication fails.

    Email failure does not stop normal website
    registration or login.
    """

    receiver_email = (
        receiver_email or ""
    ).strip()

    if not receiver_email:
        print(
            "EMAIL NOT SENT: receiver email is empty."
        )
        return False

    if (
        not EMAIL_SENDER
        or not EMAIL_APP_PASSWORD
    ):
        print(
            "EMAIL NOT SENT: EMAIL_SENDER or "
            "EMAIL_APP_PASSWORD is not configured."
        )
        return False

    server = None

    try:

        msg = MIMEMultipart()

        msg["From"] = EMAIL_SENDER
        msg["To"] = receiver_email
        msg["Subject"] = subject

        msg.attach(
            MIMEText(
                message,
                "plain",
                "utf-8"
            )
        )

        print(
            f"EMAIL: Connecting to "
            f"{SMTP_HOST}:{SMTP_PORT}..."
        )

        server = smtplib.SMTP(
            SMTP_HOST,
            SMTP_PORT,
            timeout=20
        )

        server.ehlo()
        server.starttls()
        server.ehlo()

        print(
            "EMAIL: Authenticating sender:",
            EMAIL_SENDER
        )

        server.login(
            EMAIL_SENDER,
            EMAIL_APP_PASSWORD
        )

        server.sendmail(
            EMAIL_SENDER,
            [receiver_email],
            msg.as_string()
        )

        print(
            "EMAIL SENT SUCCESSFULLY TO:",
            receiver_email
        )

        return True

    except smtplib.SMTPAuthenticationError as e:

        print(
            "EMAIL SENDING FAILED: "
            "SMTP authentication failed."
        )

        print(
            "Use a valid provider-generated "
            "App Password."
        )

        print(
            "SMTP ERROR:",
            e
        )

        return False

    except smtplib.SMTPException as e:

        print(
            "EMAIL SENDING FAILED: "
            "SMTP error."
        )

        print(
            "SMTP ERROR:",
            e
        )

        return False

    except OSError as e:

        print(
            "EMAIL SENDING FAILED: "
            "network/connection error."
        )

        print(
            "ERROR:",
            e
        )

        return False

    except Exception as e:

        print(
            "EMAIL SENDING FAILED:",
            e
        )

        return False

    finally:

        if server is not None:

            try:
                server.quit()
            except Exception:
                pass



def send_item_report_notification(
    item_type,
    reporter_name,
    reporter_email,
    item_name,
    category,
    brand,
    color,
    location,
    item_date,
    item_time,
    description
):
    """
    Send a new Lost/Found item alert to all registered users.

    All recipients are taken from the users table. Their
    addresses are sent using BCC so users cannot see the
    other recipients' email addresses.
    """

    if not EMAIL_SENDER or not EMAIL_APP_PASSWORD:
        print(
            "BROADCAST EMAIL NOT SENT: EMAIL_SENDER or "
            "EMAIL_APP_PASSWORD is not configured."
        )
        return False

    users = query(
        """
        SELECT email
        FROM users
        WHERE email IS NOT NULL
          AND TRIM(email) <> ''
        """,
        fetch=True
    )

    recipients = []
    seen = set()

    for user in users:
        user_email = (
            user.get("email") or ""
        ).strip()

        if not user_email:
            continue

        key = user_email.lower()

        if key not in seen:
            seen.add(key)
            recipients.append(user_email)

    if not recipients:
        print(
            "BROADCAST EMAIL NOT SENT: "
            "No registered user emails were found."
        )
        return False

    if item_type == "lost":
        report_label = "LOST ITEM"
        action_message = (
            "If you have found this item, please return it "
            "to the owner or contact the reporter using the "
            "email address above."
        )
    else:
        report_label = "FOUND ITEM"
        action_message = (
            "If this is your lost item, please contact the "
            "person who reported the found item using the "
            "email address above."
        )

    email_body = f"""Hello,

A new {report_label} has just been reported on the
Lost & Found Smart Matching System.

========================================
REPORTER DETAILS
========================================
Name: {reporter_name}
Email: {reporter_email}

========================================
ITEM DETAILS
========================================
Item Type: {item_type.title()}
Item Name: {item_name}
Category: {category or "Not provided"}
Brand: {brand or "Not provided"}
Color: {color or "Not provided"}
Location: {location or "Not provided"}
Date: {item_date or "Not provided"}
Time: {item_time or "Not provided"}

Description:
{description or "No description provided"}

========================================
MESSAGE
========================================
{action_message}

Please use the reporter's contact details above to help
return the item to its rightful owner.

Thank you,
Lost & Found Smart Matching System
"""

    subject = (
        f"New {item_type.title()} Item Alert - {item_name}"
    )

    server = None

    try:
        msg = MIMEMultipart()

        msg["From"] = EMAIL_SENDER
        msg["To"] = EMAIL_SENDER
        msg["Subject"] = subject

        # BCC prevents recipients from seeing all other
        # registered users' email addresses.
        msg["Bcc"] = ", ".join(recipients)

        msg.attach(
            MIMEText(
                email_body,
                "plain",
                "utf-8"
            )
        )

        print(
            "BROADCAST EMAIL: sending alert to",
            len(recipients),
            "registered user(s)..."
        )

        server = smtplib.SMTP(
            SMTP_HOST,
            SMTP_PORT,
            timeout=30
        )

        server.ehlo()
        server.starttls()
        server.ehlo()

        server.login(
            EMAIL_SENDER,
            EMAIL_APP_PASSWORD
        )

        server.sendmail(
            EMAIL_SENDER,
            recipients,
            msg.as_string()
        )

        print(
            "BROADCAST EMAIL SENT SUCCESSFULLY TO",
            len(recipients),
            "REGISTERED USER(S)."
        )

        return True

    except smtplib.SMTPAuthenticationError as e:
        print(
            "BROADCAST EMAIL FAILED: SMTP authentication failed."
        )
        print("SMTP ERROR:", e)
        return False

    except smtplib.SMTPException as e:
        print(
            "BROADCAST EMAIL FAILED: SMTP error."
        )
        print("SMTP ERROR:", e)
        return False

    except OSError as e:
        print(
            "BROADCAST EMAIL FAILED: network/connection error."
        )
        print("ERROR:", e)
        return False

    except Exception as e:
        print(
            "BROADCAST EMAIL FAILED:",
            e
        )
        return False

    finally:
        if server is not None:
            try:
                server.quit()
            except Exception:
                pass


def get_db():
    return mysql.connector.connect(**DB_CONFIG)


def query(sql, params=(), fetch=False, many=False):
    db = get_db()
    cursor = db.cursor(dictionary=True)

    try:
        if many:
            cursor.executemany(sql, params)
        else:
            cursor.execute(sql, params)

        if fetch:
            return cursor.fetchall()

        db.commit()
        return cursor.lastrowid

    finally:
        cursor.close()
        db.close()


# =========================================================
# USER FUNCTIONS
# =========================================================

def current_user():
    user_id = session.get("user_id")

    if not user_id:
        return None

    rows = query(
        """
        SELECT id, name, email, role
        FROM users
        WHERE id=%s
        """,
        (user_id,),
        True
    )

    return rows[0] if rows else None


@app.context_processor
def inject_user():
    return {
        "current_user": current_user()
    }


def login_required():
    return session.get("user_id") is not None


def admin_required():
    return session.get("role") == "admin"


def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower()
        in ALLOWED_EXTENSIONS
    )


def ensure_item_time_column():
    """
    Makes sure the items table has the item_time column.
    This allows the updated Lost/Found form to work even when
    the existing database was created with the older schema.
    """
    db = get_db()
    cursor = db.cursor()
    try:
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA=%s
              AND TABLE_NAME='items'
              AND COLUMN_NAME='item_time'
            """,
            (DB_CONFIG["database"],)
        )

        exists = cursor.fetchone()[0]

        if not exists:
            cursor.execute(
                """
                ALTER TABLE items
                ADD COLUMN item_time TIME NULL AFTER item_date
                """
            )
            db.commit()

    finally:
        cursor.close()
        db.close()


# =========================================================
# HOME
# =========================================================

@app.route("/")
def index():
    return render_template("index.html")


# =========================================================
# LOGIN
# =========================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        rows = query(
            """
            SELECT *
            FROM users
            WHERE email=%s
            """,
            (email,),
            True
        )

        if rows:
            user = rows[0]

            password_ok = check_password_hash(
                user["password_hash"],
                password
            )

            if password_ok:

                session["user_id"] = user["id"]
                session["role"] = user["role"]

                # Website notification
                flash(
                    "Login completed successfully!",
                    "success"
                )

                # Email notification
                email_sent = send_notification_email(
                    user["email"],
                    "Login Successful - Lost & Found Smart Matching System",
                    f"""Hello {user["name"]},

You have successfully logged in to the Lost & Found Smart Matching System.

Your account is now active and you can use the Lost & Found services.

If you did not perform this login, please contact the system administrator.

Thank you,
Lost & Found Smart Matching System
"""
                )

                if email_sent:
                    print(
                        "LOGIN NOTIFICATION EMAIL: SENT"
                    )
                else:
                    print(
                        "LOGIN NOTIFICATION EMAIL: NOT SENT"
                    )

                return redirect(
                    url_for("dashboard")
                )

        flash(
            "Invalid email or password.",
            "danger"
        )

    return render_template("login.html")

# =========================================================
# REGISTER
# =========================================================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )

        if not name or not email or not password:

            flash(
                "All fields are required.",
                "danger"
            )

            return redirect(
                url_for("register")
            )

        try:

            password_hash = generate_password_hash(
                password
            )

            query(
                """
                INSERT INTO users
                (
                    name,
                    email,
                    password_hash
                )
                VALUES
                (%s,%s,%s)
                """,
                (
                    name,
                    email,
                    password_hash
                )
            )

            # Website notification
            flash(
                "Registration completed successfully! Please login to continue.",
                "success"
            )

            # Email notification
            email_sent = send_notification_email(
                email,
                "Registration Successful - Lost & Found Smart Matching System",
                f"""Hello {name},

You have successfully registered on the Lost & Found Smart Matching System.

Your account has been created successfully.

You can now login to the website and use the Lost & Found Smart Matching features.

Thank you for using our system.

Regards,
Lost & Found Smart Matching System
"""
            )

            if email_sent:
                print(
                    "REGISTRATION NOTIFICATION EMAIL: SENT"
                )
            else:
                print(
                    "REGISTRATION NOTIFICATION EMAIL: NOT SENT"
                )

            return redirect(
                url_for("login")
            )

        except mysql.connector.Error:

            flash(
                "Email already exists or database error.",
                "danger"
            )

    return render_template("register.html")


# =========================================================
# COMPLAINT / REPORT CHOICE
# =========================================================

@app.route("/complaint")
def complaint():

    if not login_required():
        return redirect(url_for("login"))

    return render_template(
        "complaint.html"
    )


# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.clear()

    flash(
        "Logged out successfully.",
        "success"
    )

    return redirect(
        url_for("index")
    )


# =========================================================
# REPORT LOST / FOUND
# =========================================================

@app.route(
    "/report/<item_type>",
    methods=["GET", "POST"]
)
def report(item_type):

    if not login_required():
        return redirect(url_for("login"))

    if item_type not in (
        "lost",
        "found"
    ):
        return "Invalid item type", 400

    if request.method == "POST":

        image_name = None

        image = request.files.get("image")

        if (
            image
            and image.filename
            and allowed_file(image.filename)
        ):

            filename = secure_filename(
                image.filename
            )

            image_name = (
                f"{session['user_id']}_{filename}"
            )

            image.save(
                os.path.join(
                    app.config["UPLOAD_FOLDER"],
                    image_name
                )
            )

        item_name = request.form.get(
            "item_name",
            ""
        ).strip()

        category = request.form.get(
            "category",
            ""
        ).strip()

        brand = request.form.get(
            "brand",
            ""
        ).strip()

        color = request.form.get(
            "color",
            ""
        ).strip()

        location = request.form.get(
            "location",
            ""
        ).strip()

        item_date = request.form.get(
            "item_date"
        ) or None

        item_time = request.form.get(
            "item_time"
        ) or None

        description = request.form.get(
            "description",
            ""
        ).strip()

        if not item_name:
            flash(
                "Item name is required.",
                "danger"
            )

            return redirect(
                url_for(
                    "report",
                    item_type=item_type
                )
            )

        # Add the new time column automatically if the old database
        # schema does not have it yet.
        ensure_item_time_column()

        query(
            """
            INSERT INTO items
            (
                user_id,
                item_type,
                item_name,
                category,
                brand,
                color,
                location,
                item_date,
                item_time,
                description,
                image
            )
            VALUES
            (
                %s,%s,%s,%s,%s,%s,
                %s,%s,%s,%s,%s
            )
            """,
            (
                session["user_id"],
                item_type,
                item_name,
                category,
                brand,
                color,
                location,
                item_date,
                item_time,
                description,
                image_name
            )
        )

        # Fetch the reporter's name and email.
        reporter_rows = query(
            """
            SELECT name, email
            FROM users
            WHERE id=%s
            """,
            (session["user_id"],),
            True
        )

        reporter_name = (
            reporter_rows[0]["name"]
            if reporter_rows
            else "User"
        )

        reporter_email = (
            reporter_rows[0]["email"]
            if reporter_rows
            else ""
        )

        # Send the new Lost/Found alert immediately to all
        # registered users.
        broadcast_sent = send_item_report_notification(
            item_type=item_type,
            reporter_name=reporter_name,
            reporter_email=reporter_email,
            item_name=item_name,
            category=category,
            brand=brand,
            color=color,
            location=location,
            item_date=item_date,
            item_time=item_time,
            description=description
        )

        if broadcast_sent:
            flash(
                f"{item_type.title()} item reported successfully. "
                "Email notification sent to registered users.",
                "success"
            )
        else:
            flash(
                f"{item_type.title()} item reported successfully. "
                "Website notification shown, but email broadcast "
                "could not be sent. Check the VS Code terminal.",
                "warning"
            )

        return redirect(
            url_for("dashboard")
        )

    return render_template(
        "report.html",
        item_type=item_type
    )


# =========================================================
# UPLOADED IMAGES
# =========================================================

@app.route("/uploads/<path:filename>")
def uploaded_file(filename):

    return send_from_directory(
        app.config["UPLOAD_FOLDER"],
        filename
    )


# =========================================================
# DASHBOARD
# =========================================================

@app.route("/dashboard")
def dashboard():

    if not login_required():
        return redirect(url_for("login"))

    user_id = session["user_id"]

    items = query(
        """
        SELECT *
        FROM items
        WHERE user_id=%s
        ORDER BY created_at DESC
        """,
        (user_id,),
        True
    )

    matches = query(
        """
        SELECT
            m.*,

            l.item_name AS lost_name,
            l.location AS lost_location,

            f.item_name AS found_name,
            f.location AS found_location

        FROM matches m

        JOIN items l
        ON l.id=m.lost_item_id

        JOIN items f
        ON f.id=m.found_item_id

        WHERE
            l.user_id=%s
            OR
            f.user_id=%s

        ORDER BY m.score DESC
        """,
        (
            user_id,
            user_id
        ),
        True
    )

    return render_template(
        "dashboard.html",
        items=items,
        matches=matches
    )


# =========================================================
# SMART MATCHING
# =========================================================

@app.route("/find-matches/<int:item_id>")
def find_matches(item_id):

    if not login_required():
        return redirect(url_for("login"))

    rows = query(
        """
        SELECT *
        FROM items
        WHERE id=%s
        """,
        (item_id,),
        True
    )

    if not rows:
        return "Item not found", 404

    item = rows[0]

    if (
        item["user_id"] != session["user_id"]
        and not admin_required()
    ):
        return "Unauthorized", 403

    if item["item_type"] == "lost":
        opposite = "found"
    else:
        opposite = "lost"

    candidates = query(
        """
        SELECT *
        FROM items
        WHERE
            item_type=%s
            AND status='active'
            AND id<>%s
        """,
        (
            opposite,
            item_id
        ),
        True
    )

    results = []

    for candidate in candidates:

        score, details = calculate_match_score(
            item,
            candidate
        )

        results.append({
            "score": score,
            "item": candidate,
            "details": details
        })

    results.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    for result in results[:10]:

        candidate = result["item"]
        score = result["score"]

        if item["item_type"] == "lost":

            lost_id = item_id
            found_id = candidate["id"]

        else:

            lost_id = candidate["id"]
            found_id = item_id

        query(
            """
            INSERT INTO matches
            (
                lost_item_id,
                found_item_id,
                score
            )
            VALUES
            (%s,%s,%s)

            ON DUPLICATE KEY UPDATE
            score=%s
            """,
            (
                lost_id,
                found_id,
                score,
                score
            )
        )

    return render_template(
        "matches.html",
        item=item,
        results=results
    )


# =========================================================
# ADMIN
# =========================================================

@app.route("/admin")
def admin():

    if not admin_required():
        return "Admin access required", 403

    users = query(
        """
        SELECT
            id,
            name,
            email,
            role,
            created_at
        FROM users
        ORDER BY created_at DESC
        """,
        fetch=True
    )

    items = query(
        """
        SELECT
            i.*,
            u.name AS owner_name
        FROM items i
        JOIN users u
        ON u.id=i.user_id
        ORDER BY i.created_at DESC
        """,
        fetch=True
    )

    matches = query(
        """
        SELECT
            m.*,
            l.item_name AS lost_name,
            f.item_name AS found_name
        FROM matches m
        JOIN items l
        ON l.id=m.lost_item_id
        JOIN items f
        ON f.id=m.found_item_id
        ORDER BY m.score DESC
        """,
        fetch=True
    )

    return render_template(
        "admin.html",
        users=users,
        items=items,
        matches=matches
    )


# =========================================================
# ADMIN MATCH UPDATE
# =========================================================

@app.route(
    "/admin/match/<int:match_id>/<action>"
)
def update_match(match_id, action):

    if not admin_required():
        return "Admin access required", 403

    if action not in (
        "verified",
        "rejected"
    ):
        return "Invalid action", 400

    query(
        """
        UPDATE matches
        SET status=%s
        WHERE id=%s
        """,
        (
            action,
            match_id
        )
    )

    if action == "verified":

        rows = query(
            """
            SELECT
                lost_item_id,
                found_item_id
            FROM matches
            WHERE id=%s
            """,
            (match_id,),
            True
        )

        if rows:

            lost_id = rows[0]["lost_item_id"]
            found_id = rows[0]["found_item_id"]

            query(
                """
                UPDATE items
                SET status='matched'
                WHERE id=%s OR id=%s
                """,
                (
                    lost_id,
                    found_id
                )
            )

    flash(
        f"Match {action}.",
        "success"
    )

    return redirect(
        url_for("admin")
    )


# =========================================================
# CREATE ADMIN
# =========================================================

@app.route("/seed-admin")
def seed_admin():

    email = "nagapujitha.katla@aurora.edu.in"
    password = "pujitha@123"

    password_hash = generate_password_hash(password)

    existing = query(
        """
        SELECT id
        FROM users
        WHERE email=%s
        """,
        (email,),
        True
    )

    if existing:

        query(
            """
            UPDATE users
            SET
                name=%s,
                password_hash=%s,
                role='admin'
            WHERE email=%s
            """,
            (
                "Nagapujitha Katla",
                password_hash,
                email
            )
        )

        return (
            "Admin account updated successfully.<br>"
            "Email: nagapujitha.katla@aurora.edu.in<br>"
            "Password: pujitha@123"
        )

    query(
        """
        INSERT INTO users
        (
            name,
            email,
            password_hash,
            role
        )
        VALUES
        (%s,%s,%s,'admin')
        """,
        (
            "Nagapujitha Katla",
            email,
            password_hash
        )
    )

    return (
        "Admin created successfully.<br>"
        "Email: nagapujitha.katla@aurora.edu.in<br>"
        "Password: pujitha@123"
    )

if __name__ == "__main__":
    app.run(debug=True)