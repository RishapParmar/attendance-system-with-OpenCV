# AURA — Biometric Face Recognition Attendance System

AURA is a real-time, kiosk-style biometric student attendance system built using **OpenCV** and **Python (Tkinter)**. It utilizes the **LBPH (Local Binary Patterns Histograms) Face Recognizer** to locally register, train, and identify student faces in real-time.

The application is split into a public-facing **Check-In Kiosk** and a secure, password-protected **Administrative Portal** for enrollment, student database management, and logging.

---

## 🛠️ Installation & Setup

Follow these steps to set up a virtual environment, install the correct dependencies, and launch the application on Windows.

### Prerequisites
* **Python 3.10 to 3.12** installed on your system.

### Step 1: Create a Python Virtual Environment
Open your terminal (PowerShell or Command Prompt) in the project root directory and run:
```powershell
python -m venv venv
```

### Step 2: Activate the Virtual Environment
* **PowerShell**:
  ```powershell
  .\venv\Scripts\Activate.ps1
  ```
* **Command Prompt (CMD)**:
  ```cmd
  .\venv\Scripts\activate.bat
  ```

### Step 3: Install Dependencies
AURA requires the contributed module packages of OpenCV for the Face Recognition module (`cv2.face`). 

> [!WARNING]
> If you have the standard `opencv-python` package installed, it will conflict with `opencv-contrib-python` and hide the face recognition module. Please uninstall it first:
> ```powershell
> pip uninstall opencv-python opencv-contrib-python
> ```

Install the correct required dependencies:
```powershell
pip install -r requirements.txt
```

---

## 🚀 How to Run the App

With your virtual environment activated, run the application:
```powershell
python app.py
```

---

## 💡 How to Use AURA

### 1. Kiosk Attendance Check-In (Home Screen)
* Click **Start Video Capture** to initialize your webcam feed.
* Click **Start Scanner / Check-In** to launch scanning mode.
* When a registered face is detected:
  * A green box frames their face with their name and matching confidence score.
  * The prominent **Current Scan Status Card** lights up in green, displaying the student's name, ID, and exact check-in timestamp.
  * A check-in entry is appended to `attendance.csv` (duplicates for the day are automatically filtered).

### 2. Admin Operations Center
Click **⚙️ Admin Portal** in the top header and enter the default admin credentials:
* **Default Password**: `admin123`

This launches a separate dashboard with three tabs:
* **Enroll & Train**:
  * Input a Student ID and Full Name.
  * Click **Capture Face Samples**. Look at the camera and pose at different angles as instructed on-screen:
    1. *Look Straight Ahead* (Frames 1-6)
    2. *Turn Head Slightly Left* (Frames 7-12)
    3. *Turn Head Slightly Right* (Frames 13-18)
    4. *Tilt Head Slightly Up* (Frames 19-24)
    5. *Tilt Head Slightly Down* (Frames 25-30)
  * Click **Train Model Now** to build the database classification. (This is required before checking in new students).
* **Manage Students**:
  * View list of all registered students and their sample counts.
  * Select a student and click **Delete Selected Record** to remove them from `students.json` and wipe their face photographs from disk.
* **Attendance Logs**:
  * View the complete log history from `attendance.csv` in a scrollable list.
  * Select **Refresh Logs List** to view recent scans or **Clear Log File** to purge historical logs.

---

## 📁 Project Structure

```
trail_2/
├── dataset/                  # Stores raw grayscale face samples (.jpg)
├── trainer/
│   ├── trainer.yml           # Trained LBPH face classification model
│   └── students.json         # ID to Name metadata mappings file
├── app.py                    # Main Tkinter application code
├── requirements.txt          # Python packages dependency checklist
├── haarcascade_*.xml         # Pre-trained Haar Cascade XML classifiers
└── attendance.csv            # Excel/CSV database storing attendance check-ins
```
