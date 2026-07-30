from flask import Flask, render_template, request, redirect, Response, send_file, session, url_for
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors
import io
import joblib
import mysql.connector
from sklearn.metrics import mean_absolute_error, mean_squared_error,r2_score
app = Flask(__name__)
app.secret_key = "student_prediction_secret_key"
# Load ML Model
model = joblib.load("../model/student_performance_model.pkl")
# Connect MySQL Database
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="sabir1122",
    database="student_performance_db"
)
cursor = db.cursor()
@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        study_hours = float(request.form["study_hours"])
        attendance = float(request.form["attendance"])
        previous_marks = float(request.form["previous_marks"])
        assignments = float(request.form["assignments"])
        student_data = [[
            study_hours,
            attendance,
            previous_marks,
            assignments
        ]]
        prediction = model.predict(student_data)
        predicted_marks = float(prediction[0])
        # Performance Category
        if predicted_marks >= 90:
            performance = "Excellent 🌟"
        elif predicted_marks >= 75:
            performance = "Good 👍"
        elif predicted_marks >= 50:
            performance = "Average 🙂"
        else:
            performance = "Needs Improvement 📚"
        # Save to Database
        query = """
        INSERT INTO predictions
        (study_hours, attendance, previous_marks, assignments, predicted_marks)
        VALUES (%s, %s, %s, %s, %s)
        """
        values = (
            study_hours,
            attendance,
            previous_marks,
            assignments,
            predicted_marks
        )
        cursor.execute(query, values)
        db.commit()
        return render_template(
            "result.html",
            prediction=round(predicted_marks, 2),
            performance=performance
        )
    return render_template("index.html")
@app.route("/history")
def history():
    if "user" not in session:
        return redirect(url_for("login"))
    search = request.args.get("search", "")
    cursor = db.cursor()
    if search:
        cursor.execute("""
            SELECT * FROM predictions
            WHERE study_hours LIKE %s
               OR attendance LIKE %s
               OR previous_marks LIKE %s
               OR predicted_marks LIKE %s
        """, (
            "%" + search + "%",
            "%" + search + "%",
            "%" + search + "%",
            "%" + search + "%"
        ))
    else:
        cursor.execute("SELECT * FROM predictions")
    rows = cursor.fetchall()
    cursor.close()
    return render_template(
        "history.html",
        rows=rows,
        search=search
    )
import csv
from flask import Response
@app.route("/download_csv")
def download_csv():
    cursor = db.cursor()
    cursor.execute("SELECT * FROM predictions")
    data = cursor.fetchall()
    cursor.close()
    def generate():
        yield "ID,Study Hours,Attendance,Previous Marks,Assignments,Predicted Marks,Actual Marks\n"

        for row in data:
            yield f"{row[0]},{row[1]},{row[2]},{row[3]},{row[4]},{row[5]},{row[6]}\n"
    return Response(
        generate(),
        mimetype="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=prediction_history.csv"
        }
    )
@app.route("/download_pdf")
def download_pdf():
    cursor = db.cursor()
    cursor.execute("SELECT * FROM predictions")
    data = cursor.fetchall()
    cursor.close()
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer)
    elements = []
    table_data = [[
        "ID",
        "Study Hours",
        "Attendance",
        "Previous Marks",
        "Assignments",
        "Predicted Marks",
        "Actual Marks"
    ]]
    for row in data:
        table_data.append([
            row[0],
            row[1],
            row[2],
            row[3],
            row[4],
            row[5],
            row[6]
        ])
    table = Table(table_data)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("GRID", (0, 0), (-1, -1), 1, colors.black),
        ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 10),
    ]))
    elements.append(table)
    doc.build(elements)
    buffer.seek(0)
    return send_file(
        buffer,
        as_attachment=True,
        download_name="prediction_report.pdf",
        mimetype="application/pdf"
    )
@app.route("/delete/<int:id>")
def delete_prediction(id):
    cursor = db.cursor()
    cursor.execute("DELETE FROM predictions WHERE id=%s", (id,))
    db.commit()
    cursor.close()
    return redirect("/history")
@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit_prediction(id):
    cursor = db.cursor()
    if request.method == "POST":
        study_hours = float(request.form["study_hours"])
        attendance = float(request.form["attendance"])
        previous_marks = float(request.form["previous_marks"])
        assignments = float(request.form["assignments"])
        student_data = [[
            study_hours,
            attendance,
            previous_marks,
            assignments
        ]]
        prediction = model.predict(student_data)
        predicted_marks = float(prediction[0])
        query = """
        UPDATE predictions
        SET study_hours=%s,
            attendance=%s,
            previous_marks=%s,
            assignments=%s,
            predicted_marks=%s
        WHERE id=%s
        """
        values = (
            study_hours,
            attendance,
            previous_marks,
            assignments,
            predicted_marks,
            id
        )
        cursor.execute(query, values)
        db.commit()
        cursor.close()
        return redirect("/history")
    cursor.execute("SELECT * FROM predictions WHERE id=%s", (id,))
    data = cursor.fetchone()
    cursor.close()
    return render_template("edit.html", row=data)
@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect(url_for("login"))
    cursor = db.cursor()
    # Statistics
    cursor.execute("SELECT COUNT(*) FROM predictions")
    total = cursor.fetchone()[0]
    cursor.execute("SELECT AVG(predicted_marks) FROM predictions")
    average = cursor.fetchone()[0] or 0
    cursor.execute("SELECT MAX(predicted_marks) FROM predictions")
    highest = cursor.fetchone()[0] or 0
    cursor.execute("SELECT MIN(predicted_marks) FROM predictions")
    lowest = cursor.fetchone()[0] or 0
    # Prediction History Chart
    cursor.execute("SELECT id, predicted_marks FROM predictions")
    prediction_data = cursor.fetchall()
    labels = []
    marks = []
    for row in prediction_data:
        labels.append(str(row[0]))
        marks.append(row[1])
    # Actual vs Predicted Data
    cursor.execute("""
        SELECT id, actual_marks, predicted_marks
        FROM predictions
        WHERE actual_marks IS NOT NULL
    """)
    comparison_data = cursor.fetchall()
    comparison_labels = []
    actual_marks = []
    predicted_marks = []
    for row in comparison_data:
        comparison_labels.append(str(row[0]))
        actual_marks.append(row[1])
        predicted_marks.append(row[2])
    # Error Analysis
    error_values = []
    for actual, predicted in zip(actual_marks, predicted_marks):
        error_values.append(round(actual - predicted, 2))
    # Model Performance
    if len(actual_marks) > 0:
        mae = round(mean_absolute_error(actual_marks, predicted_marks), 2)
        mse = round(mean_squared_error(actual_marks, predicted_marks), 2)
        r2 = round(r2_score(actual_marks, predicted_marks), 2)
    else:
        mae = 0
        mse = 0
        r2 = 0
    cursor.close()
    return render_template(
        "dashboard.html",
        total=total,
        average=round(average, 2),
        highest=round(highest, 2),
        lowest=round(lowest, 2),
        labels=labels,
        marks=marks,
        comparison_labels=comparison_labels,
        actual_marks=actual_marks,
        predicted_marks=predicted_marks,
        error_values=error_values,
        mae=mae,
        mse=mse,
        r2=r2
    )
@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        cursor = db.cursor()

        cursor.execute(
            "SELECT * FROM users WHERE username=%s AND password=%s",
            (username, password)
        )

        user = cursor.fetchone()

        cursor.close()

        if user:
            session["user"] = username
            return redirect(url_for("dashboard"))
        else:
            return render_template(
                "login.html",
                error="Invalid Username or Password"
            )

    return render_template("login.html")
@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("login"))
if __name__ == "__main__":
    app.run(debug=True)
