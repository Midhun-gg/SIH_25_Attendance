🎯 Face Recognition Attendance System (FastAPI)

A lightweight attendance management system built with FastAPI + SQLite + face_recognition.
It uses facial recognition to mark student attendance automatically from uploaded classroom photos.

🚀 Features

Add classes and manage sections.

Add students with a photo → generates & stores a face embedding.

Upload a class photo → detects multiple faces and marks matching students as present.

View, edit, and delete attendance records.

Lightweight: uses face_recognition (dlib-based), no heavy deep learning models.

REST API ready for mobile/Flutter frontend integration.

🛠️ Tech Stack

Backend: FastAPI

Database: SQLite

Face Recognition: face_recognition
(built on dlib)

Image Processing: Pillow (PIL), OpenCV, NumPy

📦 Installation

Clone this repo:

git clone https://github.com/yourusername/attendance-system.git
cd attendance-system

Create a virtual environment & activate:

python -m venv venv
source venv/bin/activate # Linux/Mac
venv\Scripts\activate # Windows

Install dependencies:

pip install fastapi uvicorn face_recognition pillow opencv-python numpy

⚠️ Note: face_recognition requires dlib. On Windows, install via:

pip install cmake
pip install dlib

Run the FastAPI server:

uvicorn main:app --reload

Open in browser:

http://127.0.0.1:8000/docs

(Swagger UI for testing API endpoints)

📌 API Endpoints
Class Management

POST /add_class → Add a new class (number & section).

GET /list_classes → List all classes.

POST /delete_class → Delete a class.

Student Management

POST /add_student → Add a student (PEN, name, class_id, photo).

GET /list_students?class_id=1 → List all students in a class.

POST /delete_student → Delete a student.

Attendance Management

POST /upload_attendance → Upload classroom photo → mark attendance.

POST /edit_attendance → Manually edit attendance.

GET /view_attendance?class_id=1&date=2025-09-16 → View attendance (by date/class).

⚠️ Notes & Limitations

Currently stores only 1 embedding per student. For better accuracy, extend DB to allow multiple embeddings.

Default recognition tolerance = 0.5. Recommended: 0.6 for classroom scenarios.

Ensure good lighting & front-facing photos for best results.

Database: attendance.db is auto-created in project root.

📷 Example Workflow

Add a class → 10-A.

Register students by uploading their face photos.

Upload classroom photo (group pic) → System detects faces & marks attendance.

View attendance via API or integrate with your frontend.

👨‍💻 Author

Built by Midhun (BTech @ VIT-AP)
