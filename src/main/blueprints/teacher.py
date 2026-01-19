        if conn:
            conn.close()

@teacher_bp.route('/create_student', methods=['POST'])
def create_student():
    if "teacher_id" not in session:
        return redirect(url_for("teacher.teacher_login"))

    name = request.form.get("name")
    username = request.form.get("username")
    class_ = request.form.get("class")
    password = request.form.get("password")

    if not name or not username or not class_ or not password:
        flash("Missing required fields", "error")
        return redirect(url_for("teacher.teacher_dashboard"))

    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO Users (name, username, class, password_hash) VALUES (%s, %s, %s, %s)",
            (name, username, class_, password_hash)
        )
        conn.commit()
        flash(f"Student account created successfully! Username: {username}", "success")
        return redirect(url_for("teacher.teacher_dashboard"))
    except mysql.connector.Error as e:
        logger.exception("MySQL Error creating student: %s", e)
        flash(f"Database error: {e}", "error")
        return redirect(url_for("teacher.teacher_dashboard"))
    finally:
        if conn:
            conn.close()

@teacher_bp.route('/link_student_parent', methods=['POST'])