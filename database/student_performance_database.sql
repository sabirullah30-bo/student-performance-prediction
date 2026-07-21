create database student_performance_db;
use student_performance_db;
CREATE TABLE predictions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    study_hours FLOAT,
    attendance FLOAT,
    previous_marks FLOAT,
    assignments FLOAT,
    predicted_marks FLOAT);
show tables;