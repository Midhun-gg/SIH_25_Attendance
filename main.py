from fastapi import FastAPI, UploadFile, File, Form
import sqlite3, io, cv2, numpy as np, shutil, os
from pathlib import Path
from PIL import Image
import face_recognition
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or specify ["http://localhost:port"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- DATABASE ----------------
conn = sqlite3.connect("attendance.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""CREATE TABLE IF NOT EXISTS classes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    class_number INTEGER,
                    section TEXT)""")

cursor.execute("""CREATE TABLE IF NOT EXISTS students (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    class_id INTEGER,
                    pen TEXT UNIQUE,
                    name TEXT,
                    embedding BLOB,
                    photo_path TEXT,
                    FOREIGN KEY(class_id) REFERENCES classes(id) ON DELETE CASCADE)""")

cursor.execute("""CREATE TABLE IF NOT EXISTS attendance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    class_id INTEGER,
                    student_pen TEXT,
                    date TEXT,
                    present INTEGER,
                    FOREIGN KEY(class_id) REFERENCES classes(id) ON DELETE CASCADE)""")
conn.commit()

# ---------------- FACE UTILS ----------------
def get_embedding(img_array: np.ndarray):
    """Return embedding (128-d vector) for first detected face"""
    encodings = face_recognition.face_encodings(img_array)
    if encodings:
        return encodings[0].astype(np.float32)
    return None

def detect_faces(img_array: np.ndarray):
    """Return list of face crops"""
    face_locations = face_recognition.face_locations(img_array)
    faces = []
    for top, right, bottom, left in face_locations:
        face = img_array[top:bottom, left:right]
        faces.append(face)
    return faces

# ---------------- API ENDPOINTS ----------------
@app.post("/add_class")
def add_class(class_number: int = Form(...), section: str = Form(...)):
    cursor.execute("INSERT INTO classes (class_number, section) VALUES (?, ?)", (class_number, section))
    conn.commit()
    return {"message": f"Class {class_number}-{section} added successfully"}

@app.get("/list_classes")
def list_classes():
    cursor.execute("SELECT * FROM classes")
    rows = cursor.fetchall()
    return {"classes": [{"id": r[0], "class_number": r[1], "section": r[2]} for r in rows]}

@app.post("/delete_class")
def delete_class(class_number: int = Form(...), section: str = Form(...)):
    cursor.execute("DELETE FROM classes WHERE class_number=? AND section=?", (class_number, section))
    conn.commit()
    return {"message": f"Class {class_number}-{section} deleted successfully"}

# ✅ UPDATED ADD STUDENT ENDPOINT (with photo saving)
@app.post("/add_student")
async def add_student(class_id: int = Form(...), pen: str = Form(...), name: str = Form(...), file: UploadFile = File(...)):
    img = Image.open(io.BytesIO(await file.read())).convert("RGB")
    img_array = np.array(img)

    emb = get_embedding(img_array)
    if emb is None:
        return {"error": "No face detected"}

    # Ensure uploads folder exists
    UPLOAD_DIR = Path("uploads/students")
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    # Save uploaded photo
    file_ext = Path(file.filename).suffix
    file_name = f"{pen}{file_ext}"
    save_path = UPLOAD_DIR / file_name
    img.save(save_path)

    try:
        cursor.execute(
            "INSERT INTO students (class_id, pen, name, embedding, photo_path) VALUES (?, ?, ?, ?, ?)",
            (class_id, pen, name, emb.tobytes(), str(save_path))
        )
        conn.commit()
    except sqlite3.IntegrityError:
        return {"error": f"Student with PEN {pen} already exists"}

    return {"message": f"Student {name} added to class {class_id}", "photo": str(save_path)}

@app.post("/upload_attendance")
async def upload_attendance(class_id: int = Form(...), date: str = Form(...), file: UploadFile = File(...)):
    img = Image.open(io.BytesIO(await file.read())).convert("RGB")
    img_array = np.array(img)

    face_locations = face_recognition.face_locations(img_array)
    face_encodings = face_recognition.face_encodings(img_array, face_locations)

    if not face_encodings:
        return {"error": "No faces detected"}

    cursor.execute("SELECT pen, embedding FROM students WHERE class_id=?", (class_id,))
    rows = cursor.fetchall()

    known_encodings = [np.frombuffer(r[1], dtype=np.float32) for r in rows]
    known_pens = [r[0] for r in rows]

    present_students = []

    for encoding in face_encodings:
        matches = face_recognition.compare_faces(known_encodings, encoding, tolerance=0.5)  # adjustable
        face_distances = face_recognition.face_distance(known_encodings, encoding)

        if True in matches:
            best_match_index = np.argmin(face_distances)
            pen = known_pens[best_match_index]
            if pen not in present_students:
                present_students.append(pen)
                cursor.execute("INSERT INTO attendance (class_id, student_pen, date, present) VALUES (?, ?, ?, 1)",
                               (class_id, pen, date))

    conn.commit()
    return {"present_pens": present_students}

@app.get("/list_students")
def list_students(class_id: int):
    cursor.execute("SELECT pen, name, photo_path FROM students WHERE class_id=?", (class_id,))
    rows = cursor.fetchall()
    return {"students": [{"pen": r[0], "name": r[1], "photo": r[2]} for r in rows]}

@app.post("/delete_student")
def delete_student(pen: str = Form(...)):
    cursor.execute("DELETE FROM students WHERE pen=?", (pen,))
    conn.commit()
    return {"message": f"Student {pen} deleted successfully"}

@app.post("/edit_attendance")
def edit_attendance(class_id: int = Form(...), pen: str = Form(...), date: str = Form(...), present: int = Form(...)):
    cursor.execute("UPDATE attendance SET present=? WHERE class_id=? AND student_pen=? AND date=?",
                   (present, class_id, pen, date))
    conn.commit()
    return {"message": f"Attendance updated for {pen} on {date}"}

@app.get("/view_attendance")
def view_attendance(class_id: int, date: str = None):
    if date:
        cursor.execute("SELECT student_pen, date, present FROM attendance WHERE class_id=? AND date=?", (class_id, date))
    else:
        cursor.execute("SELECT student_pen, date, present FROM attendance WHERE class_id=?", (class_id,))
    rows = cursor.fetchall()

    records = []
    for pen, att_date, present in rows:
        cursor.execute("SELECT name FROM students WHERE pen=?", (pen,))
        student = cursor.fetchone()
        name = student[0] if student else "Unknown"
        records.append({
            "pen": pen,
            "name": name,
            "date": att_date,
            "present": bool(present)
        })
    return {"attendance_records": records}
