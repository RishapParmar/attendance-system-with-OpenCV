import os
import cv2
import json
import csv
import time
import numpy as np
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
from datetime import datetime

# Define file paths and constants
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_DIR = os.path.join(BASE_DIR, "dataset")
TRAINER_DIR = os.path.join(BASE_DIR, "trainer")
TRAINER_FILE = os.path.join(TRAINER_DIR, "trainer.yml")
MAPPINGS_FILE = os.path.join(TRAINER_DIR, "students.json")
ATTENDANCE_FILE = os.path.join(BASE_DIR, "attendance.csv")

# Create folders if they do not exist
os.makedirs(DATASET_DIR, exist_ok=True)
os.makedirs(TRAINER_DIR, exist_ok=True)

# Load XML classifiers
FACE_CASCADE_PATH = os.path.join(BASE_DIR, "haarcascade_frontalface_default.xml")
if not os.path.exists(FACE_CASCADE_PATH):
    FACE_CASCADE_PATH = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
face_cascade = cv2.CascadeClassifier(FACE_CASCADE_PATH)

# Application States
STATE_OFF = "OFF"
STATE_IDLE = "IDLE"          # Camera on, drawing detection boxes
STATE_ENROLL = "ENROLL"      # Capturing student face samples
STATE_SCAN = "SCAN"          # Performing face recognition and marking attendance


def get_enroll_instruction(count):
    """Return visual pose instructions and UI colors based on sample count."""
    if count <= 6:
        return "Look Straight Ahead", "#38bdf8"
    elif count <= 12:
        return "Turn Head Slightly Left", "#c084fc"
    elif count <= 18:
        return "Turn Head Slightly Right", "#f472b6"
    elif count <= 24:
        return "Tilt Head Slightly Up", "#fb923c"
    else:
        return "Tilt Head Slightly Down", "#facc15"


def get_pose_bgr(count):
    """Return BGR colors for OpenCV drawing based on sample count."""
    if count <= 6:
        return (248, 189, 56)   # Sky Blue
    elif count <= 12:
        return (252, 132, 192)  # Purple
    elif count <= 18:
        return (182, 114, 244)  # Pink
    elif count <= 24:
        return (60, 146, 251)   # Orange
    else:
        return (21, 204, 250)   # Yellow


class PasswordDialog(tk.Toplevel):
    """A custom, dark-themed password authentication dialog."""
    def __init__(self, parent, callback):
        super().__init__(parent)
        self.callback = callback
        self.title("AURA — Authentication")
        self.geometry("325x190")
        self.configure(bg="#121214")
        self.resizable(False, False)
        
        self.transient(parent)
        self.grab_set()
        
        parent.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - 162
        y = parent.winfo_y() + (parent.winfo_height() // 2) - 95
        self.geometry(f"+{x}+{y}")
        
        title_lbl = tk.Label(self, text="Admin Authentication Required", font=("Helvetica", 11, "bold"), fg="#ffffff", bg="#121214")
        title_lbl.pack(pady=(20, 5))
        
        desc_lbl = tk.Label(self, text="Enter password to access Admin Center:", font=("Helvetica", 9), fg="#a1a1aa", bg="#121214")
        desc_lbl.pack(pady=(0, 15))
        
        self.entry_pwd = tk.Entry(self, bg="#1e1e24", fg="#ffffff", insertbackground="#ffffff", borderwidth=1, relief="solid", show="*", font=("Helvetica", 11), justify="center")
        self.entry_pwd.pack(fill="x", padx=40, pady=(0, 20))
        self.entry_pwd.focus_set()
        
        btn_frame = tk.Frame(self, bg="#121214")
        btn_frame.pack(fill="x", padx=40)
        
        btn_cancel = tk.Button(btn_frame, text="Cancel", font=("Helvetica", 9, "bold"), bg="#2d2d34", fg="#ffffff", activebackground="#3e3e4a", activeforeground="#ffffff", borderwidth=0, padx=12, pady=5, command=self.destroy)
        btn_cancel.pack(side="left")
        
        btn_verify = tk.Button(btn_frame, text="Unlock", font=("Helvetica", 9, "bold"), bg="#eab308", fg="#121214", activebackground="#ca8a04", activeforeground="#121214", borderwidth=0, padx=12, pady=5, command=self.verify)
        btn_verify.pack(side="right")
        
        self.bind("<Return>", lambda e: self.verify())

    def verify(self):
        password = self.entry_pwd.get()
        if password == "admin123":
            self.destroy()
            self.callback(True)
        else:
            messagebox.showerror("Access Denied", "Incorrect password. Please try again.", parent=self)
            self.entry_pwd.delete(0, tk.END)


class AdminCenter(tk.Toplevel):
    """A separate administrative dashboard window."""
    def __init__(self, parent, main_app):
        super().__init__(parent)
        self.parent = parent
        self.app = main_app
        self.title("AURA — Administrative Operations Center")
        self.geometry("850x550")
        self.configure(bg="#121214")
        self.minsize(800, 480)
        
        parent.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - 425
        y = parent.winfo_y() + (parent.winfo_height() // 2) - 275
        self.geometry(f"+{x}+{y}")
        
        self.transient(parent)
        self.grab_set()
        
        # Register pointer inside main app
        self.app.admin_center_win = self
        
        self.create_widgets()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def create_widgets(self):
        header = tk.Frame(self, bg="#18181b", height=55)
        header.pack(side="top", fill="x")
        header.pack_propagate(False)
        
        tk.Label(header, text="ADMINISTRATIVE PORTAL", font=("Helvetica", 12, "bold"), fg="#ffffff", bg="#18181b").pack(side="left", padx=20, pady=15)
        self.lbl_status = tk.Label(header, text="System Unlocked", font=("Helvetica", 9, "bold"), fg="#eab308", bg="#27272a", padx=10, pady=3)
        self.lbl_status.pack(side="right", padx=20, pady=15)
        
        style = ttk.Style()
        style.configure("TNotebook", background="#121214", borderwidth=0)
        style.configure("TNotebook.Tab", background="#1e1e24", foreground="#a1a1aa", font=("Helvetica", 9, "bold"), borderwidth=0, padding=[15, 6])
        style.map("TNotebook.Tab", background=[("selected", "#252530")], foreground=[("selected", "#ffffff")])
        
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=15, pady=15)
        
        # Tab 1: Enroll & Train
        tab_enroll = tk.Frame(notebook, bg="#1e1e24")
        notebook.add(tab_enroll, text="Enroll & Train")
        self.build_enroll_tab(tab_enroll)
        
        # Tab 2: Registered Students
        tab_students = tk.Frame(notebook, bg="#1e1e24")
        notebook.add(tab_students, text="Manage Students")
        self.build_students_tab(tab_students)
        
        # Tab 3: Attendance History Logs
        tab_history = tk.Frame(notebook, bg="#1e1e24")
        notebook.add(tab_history, text="Attendance Logs")
        self.build_history_tab(tab_history)

    # ────────────────────────────────────────────────────────
    # TAB 1: ENROLLMENT & MODEL TRAINING
    # ────────────────────────────────────────────────────────
    def build_enroll_tab(self, frame):
        form_frame = tk.Frame(frame, bg="#1e1e24")
        form_frame.pack(side="left", fill="both", expand=True, padx=30, pady=20)
        
        title = tk.Label(form_frame, text="Enroll New Student", font=("Helvetica", 12, "bold"), fg="#a855f7", bg="#1e1e24")
        title.pack(anchor="w", pady=(0, 5))
        
        desc = tk.Label(form_frame, text="Fill details, look at the webcam, and capture samples.\nYou will be prompted to adjust your face at 5 different angles.", font=("Helvetica", 9), fg="#a1a1aa", bg="#1e1e24", justify="left")
        desc.pack(anchor="w", pady=(0, 15))
        
        tk.Label(form_frame, text="Student ID / Roll No:", font=("Helvetica", 9, "bold"), fg="#ffffff", bg="#1e1e24").pack(anchor="w", pady=2)
        self.entry_id = tk.Entry(form_frame, bg="#121214", fg="#ffffff", insertbackground="#ffffff", borderwidth=1, relief="solid", font=("Helvetica", 10))
        self.entry_id.pack(fill="x", pady=(0, 10))
        
        tk.Label(form_frame, text="Full Name:", font=("Helvetica", 9, "bold"), fg="#ffffff", bg="#1e1e24").pack(anchor="w", pady=2)
        self.entry_name = tk.Entry(form_frame, bg="#121214", fg="#ffffff", insertbackground="#ffffff", borderwidth=1, relief="solid", font=("Helvetica", 10))
        self.entry_name.pack(fill="x", pady=(0, 15))
        
        # Horizontal Subframe for Capture Controls & Visual Face Preview
        horizontal_layout = tk.Frame(form_frame, bg="#1e1e24")
        horizontal_layout.pack(fill="both", expand=True, pady=(5, 0))
        
        controls_subframe = tk.Frame(horizontal_layout, bg="#1e1e24")
        controls_subframe.pack(side="left", fill="both", expand=True)
        
        # Capture button
        self.btn_capture = tk.Button(controls_subframe, text="Capture Face Samples", font=("Helvetica", 10, "bold"), bg="#a855f7", fg="#ffffff", activebackground="#9333ea", activeforeground="#ffffff", borderwidth=0, pady=8, command=self.start_enrollment)
        self.btn_capture.pack(fill="x", pady=(0, 10))
        
        # Progress visual indicator
        self.lbl_progress = tk.Label(controls_subframe, text="Awaiting enrollment initialization...", font=("Helvetica", 9, "italic"), fg="#a1a1aa", bg="#1e1e24", justify="left", wraplength=200)
        self.lbl_progress.pack(anchor="w", pady=2)
        
        self.progress_bar = ttk.Progressbar(controls_subframe, orient="horizontal", mode="determinate", maximum=30)
        self.progress_bar.pack(fill="x", pady=(0, 5))
        
        # Face preview panel
        preview_subframe = tk.LabelFrame(horizontal_layout, text=" Captured Face ", font=("Helvetica", 8, "bold"), fg="#a855f7", bg="#1e1e24", bd=1, relief="solid")
        preview_subframe.configure(padx=10, pady=10)
        preview_subframe.pack(side="right", padx=(25, 0), anchor="n")
        
        self.lbl_preview_pic = tk.Label(preview_subframe, bg="#121214", width=100, height=100)
        self.lbl_preview_pic.pack()
        self.show_preview_placeholder()
        
        # Right Control Panel inside enrollment tab
        train_frame = tk.Frame(frame, bg="#18181b", width=250)
        train_frame.pack(side="right", fill="y", padx=(10, 20), pady=20)
        train_frame.pack_propagate(False)
        
        tk.Label(train_frame, text="Training Engine", font=("Helvetica", 10, "bold"), fg="#eab308", bg="#18181b").pack(anchor="w", padx=15, pady=(15, 5))
        tk.Label(train_frame, text="Re-train the model after adding or deleting student records to apply changes.", font=("Helvetica", 8), fg="#a1a1aa", bg="#18181b", justify="left", wraplength=220).pack(anchor="w", padx=15, pady=(0, 20))
        
        self.btn_train = tk.Button(train_frame, text="Train Model Now", font=("Helvetica", 10, "bold"), bg="#eab308", fg="#121214", activebackground="#ca8a04", activeforeground="#121214", borderwidth=0, pady=8, command=self.train_model)
        self.btn_train.pack(fill="x", padx=15, side="bottom", pady=20)

    def show_preview_placeholder(self):
        # Displays "?" inside cropped preview box
        placeholder = np.zeros((100, 100, 3), dtype=np.uint8) + 20
        cv2.putText(placeholder, "No Face", (22, 53), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (80, 80, 80), 1, cv2.LINE_AA)
        
        rgb = cv2.cvtColor(placeholder, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(rgb)
        self.preview_photo = ImageTk.PhotoImage(image=pil_img)
        self.lbl_preview_pic.configure(image=self.preview_photo)

    def start_enrollment(self):
        if self.app.app_state == STATE_OFF:
            messagebox.showwarning("Webcam Offline", "Please start the video capture on the Home screen first.")
            return
            
        student_id = self.entry_id.get().strip()
        student_name = self.entry_name.get().strip()
        
        if not student_id or not student_name:
            messagebox.showwarning("Fields Required", "Please enter both Student ID and Full Name before capturing samples.")
            return
            
        label_int = None
        for key, val in self.app.students_map.items():
            if val["id"] == student_id:
                label_int = int(key)
                self.app.students_map[key]["name"] = student_name
                break
                
        if label_int is None:
            label_int = self.app.next_label_id
            self.app.students_map[str(label_int)] = {"id": student_id, "name": student_name}
            self.app.next_label_id += 1
            
        self.app.save_student_mappings()
        
        # Initialize capture properties
        self.progress_bar.configure(value=0)
        self.lbl_progress.configure(text="Initiating camera...", fg="#38bdf8")
        self.show_preview_placeholder()
        
        # Start capture loop in main app window
        self.app.enroll_id = student_id
        self.app.enroll_name = student_name
        self.app.enroll_label_int = label_int
        self.app.enroll_count = 0
        self.app.last_capture_time = 0.0  # Reset timer
        self.app.app_state = STATE_ENROLL
        
        # Lock controls
        self.btn_capture.configure(state="disabled")
        self.btn_train.configure(state="disabled")

    def update_enroll_progress(self, count, face_gray):
        # Update progress bar
        self.progress_bar.configure(value=count)
        
        # Get next pose description
        next_pose, color_hex = get_enroll_instruction(count + 1)
        self.lbl_progress.configure(text=f"Next Pose: {next_pose} ({count}/30)", fg=color_hex)
        
        # Generate and show thumbnail preview of cropped face
        try:
            face_resized = cv2.resize(face_gray, (100, 100))
            rgb = cv2.cvtColor(face_resized, cv2.COLOR_GRAY2RGB)
            pil_img = Image.fromarray(rgb)
            self.preview_photo = ImageTk.PhotoImage(image=pil_img)
            self.lbl_preview_pic.configure(image=self.preview_photo)
        except Exception as e:
            print(f"Failed to generate face preview: {e}")

    def on_enrollment_complete(self):
        # Restore controls
        self.btn_capture.configure(state="normal")
        self.btn_train.configure(state="normal")
        self.progress_bar.configure(value=30)
        self.lbl_progress.configure(text="Face enrollment complete! Re-train model.", fg="#10b981")
        
        self.entry_id.delete(0, tk.END)
        self.entry_name.delete(0, tk.END)
        
        # Refresh database list table
        self.refresh_students_table()
        
        messagebox.showinfo("Enrollment Completed", f"Successfully saved 30 face samples for '{self.app.enroll_name}'!\n\nClick the 'Train Model Now' button to finalize.")

    def train_model(self):
        path_list = [os.path.join(DATASET_DIR, f) for f in os.listdir(DATASET_DIR) if f.startswith("User.")]
        if not path_list:
            messagebox.showwarning("No Data", "No face samples found in 'dataset/'. Please enroll a student first.")
            return
            
        self.btn_train.configure(text="Training model...", bg="#854d0e", state="disabled")
        self.update()
        
        faces = []
        labels = []
        
        for image_path in path_list:
            try:
                pil_img = Image.open(image_path).convert('L')
                image_np = np.array(pil_img, 'uint8')
                
                filename = os.path.basename(image_path)
                parts = filename.split('.')
                if len(parts) >= 3:
                    label_int = int(parts[1])
                    faces.append(image_np)
                    labels.append(label_int)
            except Exception as e:
                print(f"Skipping training file {image_path}: {e}")
                
        if not faces:
            messagebox.showerror("Error", "Could not load any valid face data to train.")
            self.btn_train.configure(text="Train Model Now", bg="#eab308", state="normal")
            return
            
        try:
            self.app.recognizer.train(faces, np.array(labels))
            self.app.recognizer.write(TRAINER_FILE)
            self.app.is_trained = True
            
            messagebox.showinfo("Model Updated", f"Recognizer trained successfully on {len(faces)} face samples!")
        except Exception as e:
            messagebox.showerror("Training Failed", f"An error occurred during model training: {e}")
            
        self.btn_train.configure(text="Train Model Now", bg="#eab308", state="normal")

    # ────────────────────────────────────────────────────────
    # TAB 2: REGISTERED STUDENTS MANAGEMENT
    # ────────────────────────────────────────────────────────
    def build_students_tab(self, frame):
        title = tk.Label(frame, text="Registered Database", font=("Helvetica", 11, "bold"), fg="#ffffff", bg="#1e1e24")
        title.pack(anchor="w", padx=20, pady=(20, 5))
        
        subtitle = tk.Label(frame, text="List of currently enrolled students. Delete records to clear database.", font=("Helvetica", 8), fg="#a1a1aa", bg="#1e1e24")
        subtitle.pack(anchor="w", padx=20, pady=(0, 15))
        
        table_frame = tk.Frame(frame, bg="#1e1e24")
        table_frame.pack(fill="both", expand=True, padx=20, pady=(0, 10))
        
        columns = ("label", "id", "name", "samples")
        self.student_tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=10)
        self.student_tree.heading("label", text="System Index")
        self.student_tree.heading("id", text="Student ID")
        self.student_tree.heading("name", text="Full Name")
        self.student_tree.heading("samples", text="Captured Samples")
        
        self.student_tree.column("label", width=90, anchor="center")
        self.student_tree.column("id", width=120, anchor="center")
        self.student_tree.column("name", width=250, anchor="w")
        self.student_tree.column("samples", width=120, anchor="center")
        
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.student_tree.yview)
        self.student_tree.configure(yscrollcommand=scrollbar.set)
        
        self.student_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        control_bar = tk.Frame(frame, bg="#1e1e24")
        control_bar.pack(fill="x", padx=20, pady=(5, 20))
        
        self.btn_delete = tk.Button(control_bar, text="Delete Selected Record", font=("Helvetica", 9, "bold"), bg="#ef4444", fg="#ffffff", activebackground="#dc2626", activeforeground="#ffffff", borderwidth=0, padx=15, pady=8, command=self.delete_student_record)
        self.btn_delete.pack(side="right")
        
        self.refresh_students_table()

    def refresh_students_table(self):
        for item in self.student_tree.get_children():
            self.student_tree.delete(item)
            
        files = os.listdir(DATASET_DIR)
        counts = {}
        for f in files:
            if f.startswith("User."):
                parts = f.split('.')
                if len(parts) >= 2:
                    label = parts[1]
                    counts[label] = counts.get(label, 0) + 1
                    
        for label, val in self.app.students_map.items():
            sample_cnt = counts.get(str(label), 0)
            self.student_tree.insert("", "end", values=(label, val["id"], val["name"], sample_cnt))

    def delete_student_record(self):
        selected = self.student_tree.selection()
        if not selected:
            messagebox.showwarning("Select Record", "Please select a student record from the table to delete.")
            return
            
        item = self.student_tree.item(selected[0])
        label_int = str(item["values"][0])
        student_id = item["values"][1]
        student_name = item["values"][2]
        
        confirm = messagebox.askyesno("Confirm Deletion", f"Permanently remove student '{student_name}' (ID: {student_id})?\nThis deletes all their face samples from disk.")
        if not confirm:
            return
            
        if label_int in self.app.students_map:
            del self.app.students_map[label_int]
        self.app.save_student_mappings()
        
        deleted_count = 0
        try:
            for filename in os.listdir(DATASET_DIR):
                if filename.startswith(f"User.{label_int}."):
                    os.remove(os.path.join(DATASET_DIR, filename))
                    deleted_count += 1
        except Exception as e:
            print(f"Error deleting dataset files: {e}")
            
        self.refresh_students_table()
        messagebox.showinfo("Record Removed", f"Successfully deleted '{student_name}'. {deleted_count} sample files removed.\n\nPlease go to 'Enroll & Train' tab and run the model training to rebuild classifications.")

    # ────────────────────────────────────────────────────────
    # TAB 3: ATTENDANCE HISTORY LOGS
    # ────────────────────────────────────────────────────────
    def build_history_tab(self, frame):
        title = tk.Label(frame, text="Attendance Log History", font=("Helvetica", 11, "bold"), fg="#ffffff", bg="#1e1e24")
        title.pack(anchor="w", padx=20, pady=(20, 5))
        
        subtitle = tk.Label(frame, text="Complete log records stored in attendance.csv.", font=("Helvetica", 8), fg="#a1a1aa", bg="#1e1e24")
        subtitle.pack(anchor="w", padx=20, pady=(0, 15))
        
        table_frame = tk.Frame(frame, bg="#1e1e24")
        table_frame.pack(fill="both", expand=True, padx=20, pady=(0, 10))
        
        columns = ("date", "time", "id", "name", "status")
        self.history_tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=10)
        self.history_tree.heading("date", text="Date")
        self.history_tree.heading("time", text="Time Stamp")
        self.history_tree.heading("id", text="Student ID")
        self.history_tree.heading("name", text="Full Name")
        self.history_tree.heading("status", text="Status")
        
        self.history_tree.column("date", width=100, anchor="center")
        self.history_tree.column("time", width=100, anchor="center")
        self.history_tree.column("id", width=100, anchor="center")
        self.history_tree.column("name", width=220, anchor="w")
        self.history_tree.column("status", width=90, anchor="center")
        
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=scrollbar.set)
        
        self.history_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        control_bar = tk.Frame(frame, bg="#1e1e24")
        control_bar.pack(fill="x", padx=20, pady=(5, 20))
        
        btn_clear = tk.Button(control_bar, text="Clear Log File", font=("Helvetica", 9, "bold"), bg="#ef4444", fg="#ffffff", activebackground="#dc2626", activeforeground="#ffffff", borderwidth=0, padx=15, pady=8, command=self.clear_logs)
        btn_clear.pack(side="left")
        
        btn_refresh = tk.Button(control_bar, text="Refresh Logs List", font=("Helvetica", 9, "bold"), bg="#38bdf8", fg="#121214", activebackground="#0ea5e9", activeforeground="#121214", borderwidth=0, padx=15, pady=8, command=self.refresh_history_table)
        btn_refresh.pack(side="right")
        
        self.refresh_history_table()

    def refresh_history_table(self):
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
            
        if not os.path.exists(ATTENDANCE_FILE):
            return
            
        try:
            rows = []
            with open(ATTENDANCE_FILE, "r", newline='') as f:
                reader = csv.reader(f)
                next(reader, None)
                for row in reader:
                    if len(row) >= 5:
                        rows.append(row)
            rows.reverse()
            for r in rows:
                self.history_tree.insert("", "end", values=r)
        except Exception as e:
            print(f"Error loading attendance history: {e}")

    def clear_logs(self):
        if not os.path.exists(ATTENDANCE_FILE):
            return
            
        confirm = messagebox.askyesno("Confirm Clear Logs", "Are you sure you want to permanently delete all attendance logs?\nThis cannot be undone.")
        if not confirm:
            return
            
        try:
            os.remove(ATTENDANCE_FILE)
            self.app.today_marked_cache.clear()
            self.app.clear_welcome_card()
            
            self.refresh_history_table()
            messagebox.showinfo("Logs Cleared", "The attendance log file has been emptied.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete log file: {e}")

    def on_close(self):
        self.app.admin_center_win = None
        if self.app.app_state == STATE_ENROLL:
            self.app.stop_all_active_modes()
            self.app.app_state = STATE_IDLE
        self.destroy()


class AttendanceApp:
    def __init__(self, window):
        self.window = window
        self.window.title("AURA — Biometric Face Recognition Attendance System")
        self.window.geometry("1100x700")
        self.window.configure(bg="#121214")
        self.window.minsize(1000, 600)
        
        # Internal state variables
        self.app_state = STATE_OFF
        self.cap = None
        self.enroll_id = ""
        self.enroll_name = ""
        self.enroll_count = 0
        self.enroll_label_int = 0
        self.last_capture_time = 0.0  # Tracks timestamp of last sample write
        self.students_map = {}  # {str(label_int): {"id": student_id, "name": name}}
        self.next_label_id = 1
        
        # Admin Center Window Pointer
        self.admin_center_win = None
        
        # Load mappings and trained model
        self.load_student_mappings()
        self.recognizer = cv2.face.LBPHFaceRecognizer_create()
        self.is_trained = False
        self.load_trained_model()
        
        # Track marked attendance
        self.today_marked_cache = set()
        self.load_today_attendance_cache()
        
        # Build UI widgets
        self.setup_styles()
        self.create_widgets()
        
        self.window.protocol("WM_DELETE_WINDOW", self.on_close)

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')

    def load_student_mappings(self):
        if os.path.exists(MAPPINGS_FILE):
            try:
                with open(MAPPINGS_FILE, "r") as f:
                    data = json.load(f)
                    self.students_map = data.get("mappings", {})
                    self.next_label_id = data.get("next_label_id", 1)
            except Exception as e:
                print(f"Error loading mappings file: {e}")
                self.students_map = {}
                self.next_label_id = 1

    def save_student_mappings(self):
        try:
            with open(MAPPINGS_FILE, "w") as f:
                json.dump({
                    "mappings": self.students_map,
                    "next_label_id": self.next_label_id
                }, f, indent=4)
        except Exception as e:
            print(f"Error saving mappings file: {e}")

    def load_trained_model(self):
        if os.path.exists(TRAINER_FILE):
            try:
                self.recognizer.read(TRAINER_FILE)
                self.is_trained = True
            except Exception as e:
                print(f"Error loading model: {e}")
                self.is_trained = False
        else:
            self.is_trained = False

    def load_today_attendance_cache(self):
        today_str = datetime.now().strftime("%Y-%m-%d")
        if os.path.exists(ATTENDANCE_FILE):
            try:
                with open(ATTENDANCE_FILE, "r", newline='') as f:
                    reader = csv.reader(f)
                    next(reader, None)
                    for row in reader:
                        if len(row) >= 5 and row[0] == today_str:
                            self.today_marked_cache.add(row[2])
            except Exception as e:
                print(f"Error reading attendance cache: {e}")

    def create_widgets(self):
        # ────────────────────────────────────────────────────────
        # Top Header Bar
        # ────────────────────────────────────────────────────────
        header_frame = tk.Frame(self.window, bg="#18181b", height=60)
        header_frame.pack(side="top", fill="x")
        header_frame.pack_propagate(False)
        
        header_title = tk.Label(header_frame, text="AURA KIOSK", font=("Helvetica", 18, "bold"), fg="#38bdf8", bg="#18181b")
        header_title.pack(side="left", padx=20, pady=10)
        
        header_subtitle = tk.Label(header_frame, text="• Check-In Terminal", font=("Helvetica", 11), fg="#a1a1aa", bg="#18181b")
        header_subtitle.pack(side="left", pady=15)
        
        self.btn_admin_portal = tk.Button(header_frame, text="⚙️ Admin Portal", font=("Helvetica", 10, "bold"), bg="#27272a", fg="#ffffff", activebackground="#3f3f46", activeforeground="#ffffff", borderwidth=0, padx=12, pady=5, command=self.open_admin_auth)
        self.btn_admin_portal.pack(side="right", padx=20, pady=12)
        
        self.status_pill = tk.Label(header_frame, text="CAMERA OFFLINE", font=("Helvetica", 9, "bold"), fg="#a1a1aa", bg="#27272a", padx=10, pady=3)
        self.status_pill.pack(side="right", padx=5, pady=15)
        
        # Kiosk Layout Split
        main_container = tk.Frame(self.window, bg="#121214")
        main_container.pack(side="top", fill="both", expand=True, padx=15, pady=15)
        
        # ────────────────────────────────────────────────────────
        # Left Panel: Controls & Visual Welcome Check-in Card
        # ────────────────────────────────────────────────────────
        left_panel = tk.Frame(main_container, bg="#1e1e24", width=300)
        left_panel.pack(side="left", fill="y", padx=(0, 10))
        left_panel.pack_propagate(False)
        
        panel_title = tk.Label(left_panel, text="Terminal Control", font=("Helvetica", 12, "bold"), fg="#ffffff", bg="#1e1e24")
        panel_title.pack(anchor="w", padx=15, pady=(15, 10))
        
        sep = tk.Frame(left_panel, height=1, bg="#2d2d34")
        sep.pack(fill="x", padx=15, pady=(0, 15))
        
        self.btn_toggle_cam = tk.Button(left_panel, text="Start Video Capture", font=("Helvetica", 10, "bold"), bg="#38bdf8", fg="#121214", activebackground="#0ea5e9", activeforeground="#121214", borderwidth=0, pady=8, command=self.toggle_camera)
        self.btn_toggle_cam.pack(fill="x", padx=15, pady=5)
        
        self.btn_scan = tk.Button(left_panel, text="Start Scanner / Check-In", font=("Helvetica", 10, "bold"), bg="#10b981", fg="#ffffff", activebackground="#059669", activeforeground="#ffffff", borderwidth=0, state="disabled", pady=8, command=self.start_attendance_scanner)
        self.btn_scan.pack(fill="x", padx=15, pady=10)
        
        lbl_welcome_header = tk.Label(left_panel, text="Current Scan Status", font=("Helvetica", 9, "bold"), fg="#a1a1aa", bg="#1e1e24")
        lbl_welcome_header.pack(anchor="w", padx=15, pady=(20, 5))
        
        # Visual Check-in welcome card
        self.card_frame = tk.Frame(left_panel, bg="#18181b", highlightbackground="#2d2d34", highlightcolor="#2d2d34", highlightthickness=1)
        self.card_frame.pack(fill="both", expand=True, padx=15, pady=(0, 20))
        
        self.lbl_welcome_status = tk.Label(self.card_frame, text="AWAITING SCANS", font=("Helvetica", 9, "bold"), fg="#71717a", bg="#18181b")
        self.lbl_welcome_status.pack(pady=(20, 10))
        
        self.avatar_canvas = tk.Canvas(self.card_frame, width=80, height=80, bg="#18181b", highlightthickness=0)
        self.avatar_canvas.pack(pady=5)
        self.avatar_circle = self.avatar_canvas.create_oval(5, 5, 75, 75, fill="#27272a", outline="#3f3f46", width=2)
        self.avatar_text = self.avatar_canvas.create_text(40, 40, text="?", font=("Helvetica", 20, "bold"), fill="#a1a1aa")
        
        self.lbl_welcome_name = tk.Label(self.card_frame, text="No scan active", font=("Helvetica", 13, "bold"), fg="#71717a", bg="#18181b", wraplength=250)
        self.lbl_welcome_name.pack(pady=(10, 2))
        
        self.lbl_welcome_id = tk.Label(self.card_frame, text="ID: --", font=("Helvetica", 10), fg="#52525b", bg="#18181b")
        self.lbl_welcome_id.pack(pady=2)
        
        self.lbl_welcome_time = tk.Label(self.card_frame, text="Time: --:--:--", font=("Helvetica", 10, "bold"), fg="#52525b", bg="#18181b")
        self.lbl_welcome_time.pack(pady=(2, 20))
        
        # ────────────────────────────────────────────────────────
        # Center Panel: Active Camera Display Frame
        # ────────────────────────────────────────────────────────
        center_panel = tk.Frame(main_container, bg="#18181b")
        center_panel.pack(side="left", fill="both", expand=True)
        
        self.video_screen = tk.Label(center_panel, bg="#18181b")
        self.video_screen.pack(fill="both", expand=True)
        self.show_camera_offline_screen()
        
        self.info_label = tk.Label(left_panel, text="System Offline.\nClick 'Start Video Capture'.", font=("Helvetica", 8), fg="#a1a1aa", bg="#1e1e24", justify="left")
        self.info_label.pack(side="bottom", fill="x", padx=15, pady=10)

    def show_camera_offline_screen(self):
        width, height = 640, 480
        img = np.zeros((height, width, 3), dtype=np.uint8)
        
        cv2.putText(img, "CHECK-IN TERMINAL OFFLINE", (width // 2 - 190, height // 2 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (80, 80, 80), 2, cv2.LINE_AA)
        cv2.putText(img, "Please start the video stream from controls", (width // 2 - 180, height // 2 + 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (60, 60, 60), 1, cv2.LINE_AA)
        cv2.rectangle(img, (20, 20), (width - 20, height - 20), (35, 35, 35), 1)
        
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(rgb)
        self.photo = ImageTk.PhotoImage(image=pil_img)
        self.video_screen.configure(image=self.photo)

    def open_admin_auth(self):
        PasswordDialog(self.window, self.launch_admin_portal)

    def launch_admin_portal(self, authenticated):
        if authenticated:
            if self.admin_center_win is not None:
                self.admin_center_win.lift()
            else:
                AdminCenter(self.window, self)

    def update_welcome_card(self, student_id, name, time_str):
        self.lbl_welcome_status.configure(text="VERIFICATION SUCCESSFUL", fg="#10b981")
        self.lbl_welcome_name.configure(text=name, fg="#ffffff")
        self.lbl_welcome_id.configure(text=f"Student ID: {student_id}", fg="#a1a1aa")
        self.lbl_welcome_time.configure(text=f"Logged In At: {time_str}", fg="#38bdf8")
        
        initials = "".join([n[0].upper() for n in name.split() if n])[:2] if name else "?"
        self.avatar_canvas.itemconfig(self.avatar_circle, fill="#064e3b", outline="#10b981")
        self.avatar_canvas.itemconfig(self.avatar_text, text=initials, fill="#10b981")
        
        self.card_frame.configure(highlightbackground="#10b981", highlightcolor="#10b981", highlightthickness=2)

    def clear_welcome_card(self):
        self.lbl_welcome_status.configure(text="AWAITING SCANS", fg="#71717a")
        self.lbl_welcome_name.configure(text="No active scan", fg="#71717a")
        self.lbl_welcome_id.configure(text="ID: --", fg="#52525b")
        self.lbl_welcome_time.configure(text="Time: --:--:--", fg="#52525b")
        
        self.avatar_canvas.itemconfig(self.avatar_circle, fill="#27272a", outline="#3f3f46")
        self.avatar_canvas.itemconfig(self.avatar_text, text="?", fill="#a1a1aa")
        
        self.card_frame.configure(highlightbackground="#2d2d34", highlightcolor="#2d2d34", highlightthickness=1)

    def update_status_bar(self, text, fg, bg):
        self.status_pill.configure(text=text, fg=fg, bg=bg)

    def toggle_camera(self):
        if self.app_state == STATE_OFF:
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                messagebox.showerror("Webcam Error", "Could not access system camera.")
                return
            
            self.app_state = STATE_IDLE
            self.btn_toggle_cam.configure(text="Stop Video Capture", bg="#ef4444", fg="#ffffff", activebackground="#dc2626")
            self.btn_scan.configure(state="normal")
            
            self.update_status_bar("CAMERA IDLE", "#38bdf8", "#1e293b")
            self.info_label.configure(text="Webcam active.\nStart scanner mode to mark attendance.")
            self.process_camera_feed()
        else:
            self.stop_all_active_modes()
            self.app_state = STATE_OFF
            if self.cap:
                self.cap.release()
                self.cap = None
            
            self.btn_toggle_cam.configure(text="Start Video Capture", bg="#38bdf8", fg="#121214", activebackground="#0ea5e9")
            self.btn_scan.configure(text="Start Attendance Scanner", bg="#10b981", state="disabled")
            
            self.update_status_bar("CAMERA OFFLINE", "#a1a1aa", "#27272a")
            self.info_label.configure(text="System Offline.\nClick 'Start Video Capture'.")
            self.show_camera_offline_screen()
            self.clear_welcome_card()

    def stop_all_active_modes(self):
        if self.app_state == STATE_SCAN:
            self.btn_scan.configure(text="Start Attendance Scanner", bg="#10b981")
        elif self.app_state == STATE_ENROLL:
            self.enroll_count = 0
            if self.admin_center_win is not None:
                self.admin_center_win.btn_capture.configure(state="normal")
                self.admin_center_win.btn_train.configure(state="normal")
                self.admin_center_win.progress_bar.configure(value=0)
                self.admin_center_win.lbl_progress.configure(text="Capture aborted.", fg="#ef4444")
                self.admin_center_win.show_preview_placeholder()
            self.btn_toggle_cam.configure(state="normal")
            self.btn_scan.configure(state="normal")
            self.btn_admin_portal.configure(state="normal")

    def start_attendance_scanner(self):
        if not self.is_trained:
            messagebox.showwarning("Model Missing", "No trained model found.\nPlease register a student and train model from the Admin Portal.")
            return
            
        if self.app_state == STATE_SCAN:
            self.app_state = STATE_IDLE
            self.btn_scan.configure(text="Start Attendance Scanner", bg="#10b981")
            self.update_status_bar("CAMERA IDLE", "#38bdf8", "#1e293b")
            self.info_label.configure(text="Scanner stopped. Camera active.")
        else:
            self.stop_all_active_modes()
            self.app_state = STATE_SCAN
            self.btn_scan.configure(text="Stop Scanner Mode", bg="#f97316")
            self.update_status_bar("SCANNING BIOMETRICS", "#10b981", "#064e3b")
            self.info_label.configure(text="Kiosk Terminal Scanning.\nPlease face the webcam frame.")

    def log_attendance(self, student_id, student_name):
        if student_id in self.today_marked_cache:
            return False
            
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%I:%M:%S %p")
        
        file_exists = os.path.exists(ATTENDANCE_FILE)
        
        try:
            with open(ATTENDANCE_FILE, "a", newline='') as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow(["Date", "Time", "Student ID", "Name", "Status"])
                writer.writerow([date_str, time_str, student_id, student_name, "Present"])
                
            self.today_marked_cache.add(student_id)
            self.update_welcome_card(student_id, student_name, time_str)
            
            if self.admin_center_win is not None:
                self.admin_center_win.refresh_history_table()
                
            return True
        except Exception as e:
            print(f"Failed to log attendance to CSV: {e}")
            return False

    def process_camera_feed(self):
        if self.app_state == STATE_OFF or not self.cap:
            return
            
        ret, frame = self.cap.read()
        if not ret:
            self.window.after(10, self.process_camera_feed)
            return
            
        frame = cv2.flip(frame, 1)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)
        
        # Display instructions overlay on webcam when capturing dataset
        if self.app_state == STATE_ENROLL:
            instruction, _ = get_enroll_instruction(self.enroll_count + 1)
            cv2.putText(frame, f"POSE: {instruction}", (20, 35),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)
            cv2.putText(frame, f"Saving frame {self.enroll_count}/30", (20, 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1, cv2.LINE_AA)
        
        for (x, y, w, h) in faces:
            roi_gray = gray[y:y+h, x:x+w]
            
            if self.app_state == STATE_ENROLL:
                # Limit capture rate: 1 sample every 500ms (0.5s) to allow posing angles
                current_time = time.time()
                if current_time - self.last_capture_time >= 0.5:
                    self.enroll_count += 1
                    face_img_path = os.path.join(DATASET_DIR, f"User.{self.enroll_label_int}.{self.enroll_count}.jpg")
                    
                    face_resized = cv2.resize(roi_gray, (200, 200))
                    cv2.imwrite(face_img_path, face_resized)
                    self.last_capture_time = current_time
                    
                    # Update progress thumbnail preview in Admin Center
                    if self.admin_center_win is not None:
                        self.admin_center_win.update_enroll_progress(self.enroll_count, roi_gray)
                
                # Draw Pose specific framing color
                pose_bgr = get_pose_bgr(self.enroll_count + 1)
                cv2.rectangle(frame, (x, y), (x+w, y+h), pose_bgr, 2)
                cv2.putText(frame, f"Posing... ({self.enroll_count}/30)", (x, y-10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, pose_bgr, 2)
                
                if self.enroll_count >= 30:
                    self.app_state = STATE_IDLE
                    self.btn_toggle_cam.configure(state="normal")
                    self.btn_scan.configure(state="normal")
                    self.btn_admin_portal.configure(state="normal")
                    
                    if self.admin_center_win is not None:
                        self.admin_center_win.on_enrollment_complete()
                    
                    self.update_status_bar("CAMERA IDLE", "#38bdf8", "#1e293b")
                    self.info_label.configure(text="Face enrollment completed!\nPlease train the model.")
                
                # Break to process exactly one face frame per cycle
                break
                    
            elif self.app_state == STATE_SCAN and self.is_trained:
                try:
                    face_resized = cv2.resize(roi_gray, (200, 200))
                    label_int, confidence = self.recognizer.predict(face_resized)
                    
                    if confidence < 80:
                        student_info = self.students_map.get(str(label_int))
                        if student_info:
                            student_id = student_info["id"]
                            student_name = student_info["name"]
                            
                            self.log_attendance(student_id, student_name)
                            
                            cv2.rectangle(frame, (x, y), (x+w, y+h), (129, 185, 16), 2)
                            
                            conf_pct = max(0, min(100, int(100 - confidence)))
                            label_str = f"{student_name} ({conf_pct}%)"
                            cv2.putText(frame, label_str, (x, y-10),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (129, 185, 16), 2)
                            
                            if student_id in self.today_marked_cache:
                                cv2.putText(frame, "[LOGGED]", (x, y+h+20),
                                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (129, 185, 16), 1, cv2.LINE_AA)
                        else:
                            cv2.rectangle(frame, (x, y), (x+w, y+h), (50, 50, 240), 2)
                            cv2.putText(frame, "Unknown User", (x, y-10),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (50, 50, 240), 2)
                    else:
                        cv2.rectangle(frame, (x, y), (x+w, y+h), (50, 50, 240), 2)
                        cv2.putText(frame, "Unknown Face", (x, y-10),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (50, 50, 240), 2)
                except Exception as e:
                    print(f"Error predicting face: {e}")
                    
            else:
                cv2.rectangle(frame, (x, y), (x+w, y+h), (248, 189, 56), 2)
                cv2.putText(frame, "Face Detected", (x, y-10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (248, 189, 56), 1)
        
        rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(rgb_image)
        self.photo = ImageTk.PhotoImage(image=pil_image)
        self.video_screen.configure(image=self.photo)
        
        self.window.after(10, self.process_camera_feed)

    def on_close(self):
        self.stop_all_active_modes()
        self.app_state = STATE_OFF
        if self.cap:
            self.cap.release()
        self.window.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = AttendanceApp(root)
    root.mainloop()
