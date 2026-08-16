from flask import Flask, render_template, request, redirect, url_for, session
import mysql.connector
import qrcode
import os
import uuid


# ==========================================================
# PROJECT PATHS
# ==========================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# app.py:
# Digital_Product_Passport/Backend/Flask/app.py
PROJECT_DIR = os.path.abspath(
    os.path.join(BASE_DIR, "..", "..")
)

FRONTEND_DIR = os.path.join(
    PROJECT_DIR,
    "Frontend"
)

TEMPLATES_DIR = os.path.join(
    FRONTEND_DIR,
    "templates"
)

STATIC_DIR = os.path.join(
    FRONTEND_DIR,
    "static"
)


app = Flask(
    __name__,
    template_folder=TEMPLATES_DIR,
    static_folder=STATIC_DIR
)

app.secret_key = "digital_product_passport_secret_key"


QR_FOLDER = os.path.join(
    STATIC_DIR,
    "qr_codes"
)

os.makedirs(
    QR_FOLDER,
    exist_ok=True
)


# ==========================================================
# DATABASE
# ==========================================================

def get_database_connection():

    return mysql.connector.connect(

        host="localhost",

        user="root",

        password="Karthik@123",

        database="digital_product_passport"

    )


# ==========================================================
# HELPERS
# ==========================================================

ROLE_NAMES = [

    "Customer",

    "Manufacturer",

    "Supplier",

    "Service Center",

    "Recycler"

]


def render_login(
    error=None,
    selected_role="Customer",
    entered_username="",
    success=None
):

    return render_template(

        "login.html",

        error=error,

        selected_role=selected_role,

        entered_username=entered_username,

        success=success

    )


def register_user(role_name):

    username = request.form.get(
        "username",
        ""
    ).strip()

    email = request.form.get(
        "email",
        ""
    ).strip()

    password = request.form.get(
        "password",
        ""
    )

    confirm_password = request.form.get(
        "confirm_password",
        ""
    )


    if (
        not username
        or not email
        or not password
        or not confirm_password
    ):

        return render_template(

            f"{role_name.lower().replace(' ', '_')}_register.html",

            error="Please fill all required fields."

        )


    if password != confirm_password:

        return render_template(

            f"{role_name.lower().replace(' ', '_')}_register.html",

            error="Passwords do not match.",

            username=username,

            email=email

        )


    connection = None

    cursor = None


    try:

        connection = get_database_connection()

        cursor = connection.cursor(
            dictionary=True
        )


        # --------------------------------------------------
        # GET ROLE ID
        # --------------------------------------------------

        cursor.execute(

            """
            SELECT role_id
            FROM roles
            WHERE LOWER(role_name) = LOWER(%s)
            LIMIT 1
            """,

            (role_name,)

        )


        role = cursor.fetchone()


        if role is None:

            return render_template(

                f"{role_name.lower().replace(' ', '_')}_register.html",

                error=(
                    f"{role_name} role was not "
                    "found in the database."
                ),

                username=username,

                email=email

            )


        # --------------------------------------------------
        # CHECK EXISTING USER
        # --------------------------------------------------

        cursor.execute(

            """
            SELECT user_id
            FROM users
            WHERE username = %s
               OR email = %s
            LIMIT 1
            """,

            (
                username,
                email
            )

        )


        if cursor.fetchone():

            return render_template(

                f"{role_name.lower().replace(' ', '_')}_register.html",

                error=(
                    "Username or email already exists."
                ),

                username=username,

                email=email

            )


        # --------------------------------------------------
        # INSERT USER
        # --------------------------------------------------

        cursor.execute(

            """
            INSERT INTO users
            (
                username,
                password,
                email,
                role_id,
                status
            )
            VALUES
            (
                %s,
                %s,
                %s,
                %s,
                'Active'
            )
            """,

            (
                username,
                password,
                email,
                role["role_id"]
            )

        )


        connection.commit()


        return redirect(

            url_for(

                "login",

                registered="1",

                role=role_name

            )

        )


    except mysql.connector.Error as error:

        if connection:

            connection.rollback()


        return render_template(

            f"{role_name.lower().replace(' ', '_')}_register.html",

            error=f"Registration failed: {error}",

            username=username,

            email=email

        )


    finally:

        if cursor:

            cursor.close()


        if (
            connection
            and connection.is_connected()
        ):

            connection.close()


# ==========================================================
# WELCOME
# ==========================================================

@app.route("/")
def home():

    return render_template(
        "welcome.html"
    )


# ==========================================================
# LOGIN
# ==========================================================

@app.route("/login")
def login():

    return render_login(

        selected_role=request.args.get(
            "role",
            "Customer"
        ),

        success=(

            "Registration successful. Please login."

            if request.args.get(
                "registered"
            ) == "1"

            else None

        )

    )


@app.route(
    "/login",
    methods=["POST"]
)
def login_process():

    login_type = request.form.get(
        "login_type",
        "Customer"
    ).strip()


    username = request.form.get(
        "username",
        ""
    ).strip()


    password = request.form.get(
        "password",
        ""
    )


    if (
        not username
        or not password
    ):

        return render_login(

            "Please enter username and password.",

            login_type,

            username

        )


    connection = None

    cursor = None


    try:

        connection = get_database_connection()

        cursor = connection.cursor(
            dictionary=True
        )


        cursor.execute(

            """
            SELECT
                u.user_id,
                u.username,
                u.password,
                u.email,
                u.status,
                r.role_name
            FROM users u
            JOIN roles r
                ON u.role_id = r.role_id
            WHERE u.username = %s
            LIMIT 1
            """,

            (username,)

        )


        user = cursor.fetchone()


        if user is None:

            return render_login(

                "Invalid username or password.",

                login_type,

                username

            )


        if (
            str(user["status"]).lower()
            != "active"
        ):

            return render_login(

                "This account is inactive.",

                login_type,

                username

            )


        if password != user["password"]:

            return render_login(

                "Invalid username or password.",

                login_type,

                username

            )


        database_role = str(
            user["role_name"]
        ).strip()


        if (
            database_role.lower()
            != login_type.lower()
        ):

            return render_login(

                (
                    f"This account is not registered "
                    f"as {login_type}."
                ),

                login_type,

                username

            )


        session["user_id"] = user["user_id"]

        session["username"] = user["username"]

        session["email"] = user["email"]

        session["role"] = database_role


        return redirect(
            url_for("dashboard")
        )


    except mysql.connector.Error as error:

        return render_login(

            f"Database error: {error}",

            login_type,

            username

        )


    finally:

        if cursor:

            cursor.close()


        if (
            connection
            and connection.is_connected()
        ):

            connection.close()


# ==========================================================
# SEPARATE REGISTRATION PAGES
# ==========================================================

@app.route("/customer-register")
def customer_register():

    return render_template(
        "customer_register.html"
    )


@app.route(
    "/customer-register",
    methods=["POST"]
)
def customer_register_process():

    return register_user(
        "Customer"
    )


@app.route("/manufacturer-register")
def manufacturer_register():

    return render_template(
        "manufacturer_register.html"
    )


@app.route(
    "/manufacturer-register",
    methods=["POST"]
)
def manufacturer_register_process():

    return register_user(
        "Manufacturer"
    )


@app.route("/supplier-register")
def supplier_register():

    return render_template(
        "supplier_register.html"
    )


@app.route(
    "/supplier-register",
    methods=["POST"]
)
def supplier_register_process():

    return register_user(
        "Supplier"
    )


@app.route("/service-center-register")
def service_center_register():

    return render_template(
        "service_center_register.html"
    )


@app.route(
    "/service-center-register",
    methods=["POST"]
)
def service_center_register_process():

    return register_user(
        "Service Center"
    )


@app.route("/recycler-register")
def recycler_register():

    return render_template(
        "recycler_register.html"
    )


@app.route(
    "/recycler-register",
    methods=["POST"]
)
def recycler_register_process():

    return register_user(
        "Recycler"
    )


# ==========================================================
# DASHBOARD
# ==========================================================

@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )


    return render_template(

        "dashboard.html",

        username=session.get(
            "username"
        ),

        email=session.get(
            "email"
        ),

        role=session.get(
            "role"
        )

    )


# ==========================================================
# PRODUCT REGISTRATION
# ADMIN OR MANUFACTURER
# ==========================================================

@app.route("/register-product")
def register_product():

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )


    role = str(
        session.get(
            "role",
            ""
        )
    ).lower()


    if role not in [
        "admin",
        "manufacturer"
    ]:

        return redirect(
            url_for("dashboard")
        )


    connection = None

    cursor = None


    try:

        connection = get_database_connection()

        cursor = connection.cursor(
            dictionary=True
        )


        cursor.execute(

            """
            SELECT
                manufacturer_id,
                manufacturer_name
            FROM manufacturers
            ORDER BY manufacturer_name
            """

        )


        manufacturers = cursor.fetchall()


        cursor.execute(

            """
            SELECT
                supplier_id,
                supplier_name
            FROM suppliers
            ORDER BY supplier_name
            """

        )


        suppliers = cursor.fetchall()


        return render_template(

            "register_product.html",

            manufacturers=manufacturers,

            suppliers=suppliers

        )


    except mysql.connector.Error as error:

        return render_template(

            "register_product.html",

            manufacturers=[],

            suppliers=[],

            error=f"Database error: {error}"

        )


    finally:

        if cursor:

            cursor.close()


        if (
            connection
            and connection.is_connected()
        ):

            connection.close()


@app.route(
    "/register-product",
    methods=["POST"]
)
def register_product_process():

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )


    role = str(
        session.get(
            "role",
            ""
        )
    ).lower()


    if role not in [
        "admin",
        "manufacturer"
    ]:

        return redirect(
            url_for("dashboard")
        )


    product_name = request.form.get(
        "product_name",
        ""
    ).strip()


    serial_number = request.form.get(
        "serial_number",
        ""
    ).strip()


    manufacture_date = request.form.get(
        "manufacture_date"
    ) or None


    purchase_date = request.form.get(
        "purchase_date"
    ) or None


    manufacturer_id = request.form.get(
        "manufacturer_id"
    )


    supplier_id = request.form.get(
        "supplier_id"
    ) or None


    status = request.form.get(
        "status",
        "Active"
    ).strip()


    if (
        not product_name
        or not serial_number
        or not manufacturer_id
    ):

        return render_template(

            "register_product.html",

            manufacturers=[],

            suppliers=[],

            error=(
                "Product name, serial number and "
                "manufacturer are required."
            )

        )


    connection = None

    cursor = None


    try:

        connection = get_database_connection()

        cursor = connection.cursor()


        # --------------------------------------------------
        # TEMPORARY CODE
        # --------------------------------------------------

        temporary_code = (
            "TEMP-"
            + uuid.uuid4().hex
        )


        cursor.execute(

            """
            INSERT INTO products
            (
                product_code,
                product_name,
                serial_number,
                manufacture_date,
                purchase_date,
                status,
                manufacturer_id,
                supplier_id
            )
            VALUES
            (
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s
            )
            """,

            (
                temporary_code,
                product_name,
                serial_number,
                manufacture_date,
                purchase_date,
                status,
                manufacturer_id,
                supplier_id
            )

        )


        product_id = cursor.lastrowid


        product_code = (
            f"P{int(product_id):06d}"
        )


        cursor.execute(

            """
            UPDATE products
            SET product_code = %s
            WHERE product_id = %s
            """,

            (
                product_code,
                product_id
            )

        )


        connection.commit()


        return redirect(

            url_for(

                "product_page",

                product_code=product_code

            )

        )


    except mysql.connector.Error as error:

        if connection:

            connection.rollback()


        return render_template(

            "register_product.html",

            manufacturers=[],

            suppliers=[],

            error=(
                f"Product registration failed: "
                f"{error}"
            )

        )


    finally:

        if cursor:

            cursor.close()


        if (
            connection
            and connection.is_connected()
        ):

            connection.close()


# ==========================================================
# SEARCH / PRODUCT PASSPORT
# ==========================================================

@app.route(
    "/search",
    methods=["GET", "POST"]
)
def search_product():

    # ------------------------------------------------------
    # GET
    # ------------------------------------------------------
    # When the user clicks "Search Product" from dashboard,
    # open index.html instead of the welcome page.
    # ------------------------------------------------------

    if request.method == "GET":

        return render_template(

            "index.html",

            searched_product_code=""

        )


    # ------------------------------------------------------
    # POST
    # ------------------------------------------------------
    # When the user submits the search form, find the
    # requested Product ID.
    # ------------------------------------------------------

    product_code = request.form.get(

        "product_code",

        ""

    ).strip().upper()


    if not product_code:

        return render_template(

            "index.html",

            error="Please enter a Product ID.",

            searched_product_code=""

        )


    return get_product_passport(
        product_code
    )


# ==========================================================
# PRODUCT PASSPORT URL
# ==========================================================

@app.route(
    "/product/<product_code>"
)
def product_page(product_code):

    return get_product_passport(

        product_code.strip().upper()

    )


# ==========================================================
# GET COMPLETE PRODUCT PASSPORT
# ==========================================================

def get_product_passport(
    product_code
):

    connection = None

    cursor = None


    try:

        connection = get_database_connection()

        cursor = connection.cursor(
            dictionary=True
        )


        # --------------------------------------------------
        # PRODUCT INFORMATION
        # --------------------------------------------------

        cursor.execute(

            """
            SELECT
                p.product_id,
                p.product_code,
                p.product_name,
                p.serial_number,
                p.manufacture_date,
                p.purchase_date,
                p.status,
                m.manufacturer_name,
                s.supplier_name
            FROM products p
            JOIN manufacturers m
                ON p.manufacturer_id =
                   m.manufacturer_id
            LEFT JOIN suppliers s
                ON p.supplier_id =
                   s.supplier_id
            WHERE p.product_code = %s
            """,

            (product_code,)

        )


        product = cursor.fetchone()


        if not product:

            return render_template(

                "index.html",

                error="Product not found.",

                searched_product_code=product_code

            )


        product_id = product[
            "product_id"
        ]


        # --------------------------------------------------
        # COMPONENTS
        # --------------------------------------------------

        cursor.execute(

            """
            SELECT
                c.component_name,
                c.component_serial_no,
                c.manufacturer,
                c.description,
                pc.quantity,
                pc.installation_date,
                pc.status
            FROM product_components pc
            JOIN components c
                ON pc.component_id =
                   c.component_id
            WHERE pc.product_id = %s
            """,

            (product_id,)

        )


        components = cursor.fetchall()


        # --------------------------------------------------
        # WARRANTY
        # --------------------------------------------------

        cursor.execute(

            """
            SELECT
                warranty_type,
                warranty_start,
                warranty_end,
                terms,
                status
            FROM warranty
            WHERE product_id = %s
            ORDER BY warranty_start DESC
            """,

            (product_id,)

        )


        warranty = cursor.fetchall()


        # --------------------------------------------------
        # SERVICE HISTORY
        # --------------------------------------------------

        cursor.execute(

            """
            SELECT
                sc.center_name,
                sh.service_date,
                sh.problem_description,
                sh.service_type,
                sh.parts_replaced,
                sh.service_cost,
                sh.service_status,
                sh.remarks
            FROM service_history sh
            JOIN service_centers sc
                ON sh.service_center_id =
                   sc.service_center_id
            WHERE sh.product_id = %s
            ORDER BY sh.service_date DESC
            """,

            (product_id,)

        )


        service_history = cursor.fetchall()


        # --------------------------------------------------
        # OWNERSHIP HISTORY
        # --------------------------------------------------

        cursor.execute(

            """
            SELECT
                c.customer_name,
                c.phone,
                c.email,
                oh.ownership_start,
                oh.ownership_end,
                oh.transfer_date,
                oh.transfer_reason
            FROM ownership_history oh
            JOIN customers c
                ON oh.customer_id =
                   c.customer_id
            WHERE oh.product_id = %s
            ORDER BY oh.ownership_start
            """,

            (product_id,)

        )


        ownership_history = cursor.fetchall()


        # --------------------------------------------------
        # RECYCLING
        # --------------------------------------------------

        cursor.execute(

            """
            SELECT
                recycling_date,
                recycler_name,
                recycling_reason,
                recovered_material,
                status,
                remarks
            FROM recycling
            WHERE product_id = %s
            ORDER BY recycling_date DESC
            """,

            (product_id,)

        )


        recycling = cursor.fetchall()


    except mysql.connector.Error as error:

        return render_template(

            "index.html",

            error=f"Database error: {error}",

            searched_product_code=product_code

        )


    finally:

        if cursor:

            cursor.close()


        if (
            connection
            and connection.is_connected()
        ):

            connection.close()


    # ======================================================
    # QR CODE
    # ======================================================

    qr_filename = (
        product_code
        + ".png"
    )


    qr_path = os.path.join(

        QR_FOLDER,

        qr_filename

    )


    qr_url = url_for(

        "product_page",

        product_code=product_code,

        _external=True

    )


    if not os.path.exists(
        qr_path
    ):

        qr = qrcode.QRCode(

            version=1,

            box_size=10,

            border=4

        )


        qr.add_data(
            qr_url
        )


        qr.make(
            fit=True
        )


        qr_image = qr.make_image(

            fill_color="black",

            back_color="white"

        )


        qr_image.save(
            qr_path
        )


    qr_image_url = url_for(

        "static",

        filename=(
            "qr_codes/"
            + qr_filename
        )

    )


    # ======================================================
    # DISPLAY PRODUCT PASSPORT
    # ======================================================

    return render_template(

        "index.html",

        product=product,

        components=components,

        warranty=warranty,

        service_history=service_history,

        ownership_history=ownership_history,

        recycling=recycling,

        qr_image_url=qr_image_url,

        searched_product_code=product_code

    )


# ==========================================================
# LOGOUT
# ==========================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(
        url_for("login")
    )


# ==========================================================
# RUN
# ==========================================================

if __name__ == "__main__":

    app.run(
        debug=True
    )