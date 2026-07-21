from flask import Flask, render_template, request
import joblib
import mysql.connector
app = Flask(__name__)
model = joblib.load("model/student_performance_model.pkl")
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
        return f"Predicted Final Marks: {predicted_marks:.2f}"
    return render_template("index.html")
@app.route("/history")
def history():
    cursor = db.cursor()
    cursor.execute("SELECT * FROM predictions")
    data = cursor.fetchall()
    cursor.close()
    return render_template("history.html", predictions=data)
if __name__ == "__main__":
    app.run(debug=True)
