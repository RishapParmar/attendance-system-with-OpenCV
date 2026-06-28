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
MAPPINGS_FILE = os.path.join(TRAINER_DIR, "students.json")
ATTENDANCE_FILE = os.path.join(BASE_DIR, "attendance.csv")

# Create folders if they do not exist
os.makedirs(DATASET_DIR, exist_ok=True)
os.makedirs(TRAINER_DIR, exist_ok=True)

# ────────────────────────────────────────────────────────
# Hexonn Labs Corporate Color Matrix & Styles (Default Theme Constants)
# ────────────────────────────────────────────────────────
COLOR_TECH_EMERALD = "#0A3C28"    # Main Identity, Corporate Weight, Headings
COLOR_CYBER_GREEN = "#10B981"     # Core IT, AI, Robotics, Active States
COLOR_MATTE_CHARCOAL = "#1A1F26"  # Premium Backgrounds, Typography
COLOR_TECH_PINK = "#E65F87"       # Counseling Services, Human Factors, CTAs
COLOR_DIGITAL_AMETHYST = "#7B2CBF" # Mentorship, Advanced Dev, Architecture
COLOR_PLATINUM_WHITE = "#F8FAFC"   # UI Background Canvas, Structural Separation

COLOR_BG_HEADER = COLOR_TECH_EMERALD      # Corporate weight Tech Emerald header
COLOR_TEXT_LIGHT = "#FFFFFF"              # White text for high-contrast elements

# Application States
STATE_OFF = "OFF"
STATE_IDLE = "IDLE"          # Camera on, drawing detection boxes
STATE_ENROLL = "ENROLL"      # Capturing student face samples
STATE_SCAN = "SCAN"          # Performing face recognition and marking attendance


def get_enroll_instruction(count):
    """Return visual pose instructions and UI colors based on sample count."""
    if count <= 20:
        return "Look Straight Ahead", COLOR_CYBER_GREEN
    elif count <= 40:
        return "Turn Head Slightly Left", COLOR_DIGITAL_AMETHYST
    elif count <= 60:
        return "Turn Head Slightly Right", COLOR_TECH_PINK
    elif count <= 80:
        return "Tilt Head Slightly Up", "#a855f7"
    else:
        return "Tilt Head Slightly Down", COLOR_TECH_EMERALD


def get_pose_bgr(count):
    """Return BGR colors for OpenCV drawing based on sample count."""
    if count <= 20:
        return (129, 185, 16)   # Cyber Green BGR
    elif count <= 40:
        return (191, 44, 123)   # Amethyst BGR
    elif count <= 60:
        return (135, 95, 230)   # Tech Pink BGR
    elif count <= 80:
        return (247, 85, 168)   # Amethyst shade BGR
    else:
        return (40, 60, 10)     # Tech Emerald BGR


class PasswordDialog(tk.Toplevel):
    """A custom, password authentication dialog."""
    def __init__(self, parent, theme, callback):
        super().__init__(parent)
        self.callback = callback
        
        # Query theme colors
        if theme == "light":
            bg_dark = "#F8FAFC"
            bg_card = "#FFFFFF"
            text_primary = "#1A1F26"
            text_muted = "#4A5568"
        else:
            bg_dark = "#1A1F26"
            bg_card = "#242B35"
            text_primary = "#F8FAFC"
            text_muted = "#A3B8CC"
            
        self.title("CDAC — Authentication")
        self.geometry("325x190")
        self.configure(bg=bg_dark)
        self.resizable(False, False)
        
        self.transient(parent)
        self.grab_set()
        
        parent.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - 162
        y = parent.winfo_y() + (parent.winfo_height() // 2) - 95
        self.geometry(f"+{x}+{y}")
        
        title_lbl = tk.Label(self, text="CDAC SYSTEM AUTHENTICATION", font=("Helvetica", 10, "bold"), fg=COLOR_TECH_EMERALD if theme == "light" else COLOR_CYBER_GREEN, bg=bg_dark)
        title_lbl.pack(pady=(20, 5))
        
        desc_lbl = tk.Label(self, text="Enter password to access Admin Center:", font=("Helvetica", 9), fg=text_muted, bg=bg_dark)
        desc_lbl.pack(pady=(0, 15))
        
        self.entry_pwd = tk.Entry(self, bg=bg_card, fg=text_primary, insertbackground=text_primary, borderwidth=1, relief="solid", show="*", font=("Helvetica", 11), justify="center")
        self.entry_pwd.pack(fill="x", padx=40, pady=(0, 20))
        self.entry_pwd.focus_set()
        
        btn_frame = tk.Frame(self, bg=bg_dark)
        btn_frame.pack(fill="x", padx=40)
        
        btn_cancel = tk.Button(btn_frame, text="Cancel", font=("Helvetica", 9, "bold"), bg="#E2E8F0" if theme == "light" else "#2E3743", fg=text_primary, activebackground="#CBD5E1", activeforeground=text_primary, borderwidth=0, padx=12, pady=5, command=self.destroy)
        btn_cancel.pack(side="left")
        
        btn_verify = tk.Button(btn_frame, text="Unlock", font=("Helvetica", 9, "bold"), bg=COLOR_TECH_EMERALD, fg=COLOR_TEXT_LIGHT, activebackground="#052518", activeforeground=COLOR_TEXT_LIGHT, borderwidth=0, padx=12, pady=5, command=self.verify)
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


class EnrollmentGuideWindow(tk.Toplevel):
    """A pop-up window during enrollment that shows a large camera feed and graphical direction arrows."""
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.title("CDAC — Face Registration Guidance Center")
        self.geometry("900x560")
        
        theme = app.current_theme
        self.bg_color = "#F8FAFC" if theme == "light" else "#1A1F26"
        self.card_color = "#FFFFFF" if theme == "light" else "#242B35"
        self.text_color = "#1A1F26" if theme == "light" else "#F8FAFC"
        self.text_muted = "#4A5568" if theme == "light" else "#A3B8CC"
        
        self.configure(bg=self.bg_color)
        self.resizable(False, False)
        
        self.transient(parent)
        self.grab_set()
        
        # Center the window
        parent.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - 450
        y = parent.winfo_y() + (parent.winfo_height() // 2) - 280
        self.geometry(f"+{x}+{y}")
        
        self.create_widgets()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def create_widgets(self):
        # Camera screen (left)
        self.video_frame = tk.Frame(self, bg=self.card_color, bd=1, relief="solid")
        self.video_frame.pack(side="left", fill="both", expand=True, padx=20, pady=20)
        
        self.video_label = tk.Label(self.video_frame, bg=self.card_color)
        self.video_label.pack(fill="both", expand=True)
        
        # Sidebar layout (right)
        self.side_panel = tk.Frame(self, bg=self.card_color, width=220)
        self.side_panel.pack(side="right", fill="y", padx=(0, 20), pady=20)
        self.side_panel.pack_propagate(False)
        
        lbl_title = tk.Label(self.side_panel, text="GUIDED SCAN", font=("Helvetica", 11, "bold"), fg=COLOR_TECH_EMERALD if self.app.current_theme == "light" else COLOR_CYBER_GREEN, bg=self.card_color)
        lbl_title.pack(pady=(20, 10))
        
        # Arrow graphics canvas
        self.arrow_canvas = tk.Canvas(self.side_panel, width=120, height=120, bg=self.bg_color, highlightthickness=1, highlightbackground=COLOR_CYBER_GREEN)
        self.arrow_canvas.pack(pady=15)
        
        # Instruction text label (large)
        self.lbl_instruction = tk.Label(self.side_panel, text="Awaiting camera...", font=("Helvetica", 12, "bold"), fg=self.text_color, bg=self.card_color, justify="center", wraplength=200)
        self.lbl_instruction.pack(pady=10)
        
        self.lbl_count = tk.Label(self.side_panel, text="Samples Captured: 0 / 100", font=("Helvetica", 9), fg=self.text_muted, bg=self.card_color)
        self.lbl_count.pack(pady=5)
        
        # Progress bar
        self.progress_bar = ttk.Progressbar(self.side_panel, orient="horizontal", mode="determinate", maximum=100)
        self.progress_bar.pack(fill="x", padx=20, pady=10)
        
        # Cancel button
        self.btn_abort = tk.Button(self.side_panel, text="Abort Capture", font=("Helvetica", 9, "bold"), bg=COLOR_TECH_PINK, fg=COLOR_TEXT_LIGHT, activebackground="#d64e75", activeforeground=COLOR_TEXT_LIGHT, borderwidth=0, pady=8, command=self.on_close)
        self.btn_abort.pack(fill="x", padx=20, side="bottom", pady=20)
        
        # Draw initial straight arrow direction
        self.draw_guide_arrow(0)

    def draw_guide_arrow(self, count):
        self.arrow_canvas.delete("all")
        
        color_fill = COLOR_CYBER_GREEN
        
        if count <= 20: # Straight target alignment
            # Concentric rings target
            self.arrow_canvas.create_oval(20, 20, 100, 100, outline=color_fill, width=2)
            self.arrow_canvas.create_oval(40, 40, 80, 80, outline=color_fill, width=1.5)
            self.arrow_canvas.create_oval(55, 55, 65, 65, fill=COLOR_TECH_PINK, outline=color_fill)
            self.arrow_canvas.create_line(60, 10, 60, 110, fill=color_fill, width=1)
            self.arrow_canvas.create_line(10, 60, 110, 60, fill=color_fill, width=1)
        elif count <= 40: # Left
            # Thick arrow pointing left
            pts = [(100, 45), (45, 45), (45, 25), (15, 60), (45, 95), (45, 75), (100, 75)]
            self.arrow_canvas.create_polygon(pts, fill=COLOR_DIGITAL_AMETHYST, outline=COLOR_CYBER_GREEN, width=1.5)
        elif count <= 60: # Right
            # Thick arrow pointing right
            pts = [(20, 45), (75, 45), (75, 25), (105, 60), (75, 95), (75, 75), (20, 75)]
            self.arrow_canvas.create_polygon(pts, fill=COLOR_TECH_PINK, outline=COLOR_CYBER_GREEN, width=1.5)
        elif count <= 80: # Up
            # Thick arrow pointing up
            pts = [(45, 100), (45, 45), (25, 45), (60, 15), (95, 45), (75, 45), (75, 100)]
            self.arrow_canvas.create_polygon(pts, fill="#a855f7", outline=COLOR_CYBER_GREEN, width=1.5)
        else: # Down
            # Thick arrow pointing down
            pts = [(45, 20), (45, 75), (25, 75), (60, 105), (95, 75), (75, 75), (75, 20)]
            self.arrow_canvas.create_polygon(pts, fill=COLOR_TECH_EMERALD, outline=COLOR_CYBER_GREEN, width=1.5)

    def update_guide(self, count, aligned_face):
        self.progress_bar.configure(value=count)
        self.lbl_count.configure(text=f"Samples Captured: {count} / 100")
        
        next_pose, color_hex = get_enroll_instruction(count + 1)
        self.lbl_instruction.configure(text=next_pose, fg=color_hex)
        
        self.draw_guide_arrow(count)

    def update_video_feed(self, photo):
        self.video_label.configure(image=photo)
        self.video_photo = photo # Keep reference

    def on_close(self):
        self.app.stop_all_active_modes()
        self.app.app_state = STATE_IDLE
        self.app.enroll_guide_win = None
        self.destroy()


class AdminCenter(tk.Toplevel):
    """A separate administrative dashboard window."""
    def __init__(self, parent, main_app):
        super().__init__(parent)
        self.parent = parent
        self.app = main_app
        self.title("CDAC — Operations Center")
        self.geometry("850x550")
        self.configure(bg="#F8FAFC")
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
        self.apply_theme_colors(self.app.current_theme)
        
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def create_widgets(self):
        self.header = tk.Frame(self, bg=COLOR_BG_HEADER, height=55)
        self.header.pack(side="top", fill="x")
        self.header.pack_propagate(False)
        
        self.logo_text_frame = tk.Frame(self.header, bg=COLOR_BG_HEADER)
        self.logo_text_frame.pack(side="left", padx=20, pady=5)
        
        lbl_wordmark = tk.Label(self.logo_text_frame, text="C D A C", font=("Helvetica", 11, "bold"), fg=COLOR_TEXT_LIGHT, bg=COLOR_BG_HEADER)
        lbl_wordmark.pack(anchor="w")
        
        lbl_subtitle = tk.Label(self.logo_text_frame, text="OPERATIONS CENTER", font=("Helvetica", 6, "bold"), fg=COLOR_CYBER_GREEN, bg=COLOR_BG_HEADER)
        lbl_subtitle.pack(anchor="w", pady=(2, 0))
        
        self.lbl_status = tk.Label(self.header, text="System Unlocked", font=("Helvetica", 9, "bold"), fg="#1A1F26", bg="#F8FAFC", padx=10, pady=3)
        self.lbl_status.pack(side="right", padx=20, pady=15)
        
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=15, pady=(15, 0))
        self.notebook = notebook
        
        # Tab 1: Enroll & Train
        self.tab_enroll = tk.Frame(notebook, bg="#FFFFFF")
        notebook.add(self.tab_enroll, text="Enroll & Train")
        self.build_enroll_tab(self.tab_enroll)
        
        # Tab 2: Registered Students
        self.tab_students = tk.Frame(notebook, bg="#FFFFFF")
        notebook.add(self.tab_students, text="Manage Students")
        self.build_students_tab(self.tab_students)
        
        # Tab 3: Attendance History Logs
        self.tab_history = tk.Frame(notebook, bg="#FFFFFF")
        notebook.add(self.tab_history, text="Attendance Logs")
        self.build_history_tab(self.tab_history)
        
        # Bottom Footer Widget in Admin
        self.footer_frame = tk.Frame(self, bg="#F8FAFC")
        self.footer_frame.pack(side="bottom", fill="x", pady=(10, 10))
        
        self.powered_by_container = tk.Frame(self.footer_frame, bg="#F8FAFC")
        self.powered_by_container.pack(anchor="center")
        
        self.hexa_canvas = tk.Canvas(self.powered_by_container, width=25, height=25, bg="#F8FAFC", highlightthickness=0)
        self.hexa_canvas.pack(side="left", padx=5)
        
        self.lbl_powered = tk.Label(self.powered_by_container, text="Powered by Hexonn Labs", font=("Helvetica", 8, "bold"), fg="#4A5568", bg="#F8FAFC")
        self.lbl_powered.pack(side="left", padx=5)

    def apply_theme_colors(self, theme):
        if theme == "light":
            bg_dark = "#F8FAFC"
            bg_card = "#FFFFFF"
            text_primary = "#1A1F26"
            text_muted = "#4A5568"
        else:
            bg_dark = "#1A1F26"
            bg_card = "#242B35"
            text_primary = "#F8FAFC"
            text_muted = "#A3B8CC"
            
        self.configure(bg=bg_dark)
        self.lbl_status.configure(bg=bg_dark, fg=text_primary)
        
        # Recursive widget colors update
        def apply_colors(w):
            w_class = w.winfo_class()
            w_name = str(w).lower()
            parent_name = str(w.winfo_parent()).lower()
            
            if "header" in parent_name or "header" in w_name:
                return
                
            if w_class == "Label":
                if "train_frame" in parent_name:
                    w.configure(bg=bg_dark, fg=COLOR_TECH_EMERALD if theme == "light" else COLOR_CYBER_GREEN)
                elif "preview" in parent_name or "preview" in w_name:
                    w.configure(bg=bg_dark, fg=text_muted)
                else:
                    w.configure(bg=bg_card, fg=text_primary)
            elif w_class == "Frame":
                if "train_frame" in w_name:
                    w.configure(bg=bg_dark)
                elif "footer" in w_name or "footer" in parent_name:
                    w.configure(bg=bg_dark)
                else:
                    w.configure(bg=bg_card)
            elif w_class == "LabelFrame":
                w.configure(bg=bg_card, fg=COLOR_DIGITAL_AMETHYST)
            elif w_class == "Entry":
                w.configure(bg=bg_dark, fg=text_primary, insertbackground=text_primary)
            elif w_class == "Button":
                txt = w.cget("text")
                if txt not in ["Capture Face Samples", "Train Model Now", "Delete Selected Record", "Clear Log File", "Refresh Logs List"]:
                    w.configure(bg="#E2E8F0" if theme == "light" else "#2E3743", fg=text_primary)
                    
            for child in w.winfo_children():
                apply_colors(child)
                
        apply_colors(self.notebook)
        
        # Explicit tab container background updates
        self.tab_enroll.configure(bg=bg_card)
        self.tab_students.configure(bg=bg_card)
        self.tab_history.configure(bg=bg_card)
        
        # Footer
        self.footer_frame.configure(bg=bg_dark)
        self.powered_by_container.configure(bg=bg_dark)
        self.hexa_canvas.configure(bg=bg_dark)
        self.lbl_powered.configure(bg=bg_dark, fg=text_muted)
        
        # Redraw Hexonn Logo on Admin footer
        self.hexa_canvas.delete("all")
        nodes = [(12, 3), (21, 8), (21, 17), (12, 22), (3, 17), (3, 8)]
        for i in range(6):
            p1 = nodes[i]
            p2 = nodes[(i+1)%6]
            self.hexa_canvas.create_line(p1[0], p1[1], p2[0], p2[1], fill=COLOR_CYBER_GREEN, width=1.5)
        for x, y in nodes:
            self.hexa_canvas.create_oval(x-1.5, y-1.5, x+1.5, y+1.5, fill=COLOR_TECH_PINK, outline=COLOR_CYBER_GREEN, width=0.5)
        inner_nodes = [(12, 8), (16, 10), (16, 15), (12, 17), (8, 15), (8, 10)]
        self.hexa_canvas.create_polygon(inner_nodes, fill="", outline=COLOR_CYBER_GREEN, width=1)

    def build_enroll_tab(self, frame):
        form_frame = tk.Frame(frame, bg="#FFFFFF")
        form_frame.pack(side="left", fill="both", expand=True, padx=30, pady=20)
        
        title = tk.Label(form_frame, text="E N R O L L   N E W   S T U D E N T", font=("Helvetica", 11, "bold"), fg="#1A1F26", bg="#FFFFFF")
        title.pack(anchor="w", pady=(0, 5))
        
        desc = tk.Label(form_frame, text="Fill details, look at the webcam, and capture samples.\nYou will be prompted to adjust your face at 5 different angles.", font=("Helvetica", 9), fg="#4A5568", bg="#FFFFFF", justify="left")
        desc.pack(anchor="w", pady=(0, 15))
        
        tk.Label(form_frame, text="Student ID / Roll No:", font=("Helvetica", 9, "bold"), fg="#1A1F26", bg="#FFFFFF").pack(anchor="w", pady=2)
        self.entry_id = tk.Entry(form_frame, bg="#F8FAFC", fg="#1A1F26", insertbackground="#1A1F26", borderwidth=1, relief="solid", font=("Helvetica", 10))
        self.entry_id.pack(fill="x", pady=(0, 10))
        
        tk.Label(form_frame, text="Full Name:", font=("Helvetica", 9, "bold"), fg="#1A1F26", bg="#FFFFFF").pack(anchor="w", pady=2)
        self.entry_name = tk.Entry(form_frame, bg="#F8FAFC", fg="#1A1F26", insertbackground="#1A1F26", borderwidth=1, relief="solid", font=("Helvetica", 10))
        self.entry_name.pack(fill="x", pady=(0, 15))
        
        horizontal_layout = tk.Frame(form_frame, bg="#FFFFFF")
        horizontal_layout.pack(fill="both", expand=True, pady=(5, 0))
        
        controls_subframe = tk.Frame(horizontal_layout, bg="#FFFFFF")
        controls_subframe.pack(side="left", fill="both", expand=True)
        
        self.btn_capture = tk.Button(controls_subframe, text="Capture Face Samples", font=("Helvetica", 10, "bold"), bg=COLOR_DIGITAL_AMETHYST, fg=COLOR_TEXT_LIGHT, activebackground="#5E2299", activeforeground=COLOR_TEXT_LIGHT, borderwidth=0, pady=8, command=self.start_enrollment)
        self.btn_capture.pack(fill="x", pady=(0, 10))
        
        self.lbl_progress = tk.Label(controls_subframe, text="Awaiting enrollment initialization...", font=("Helvetica", 9, "italic"), fg="#4A5568", bg="#FFFFFF", justify="left", wraplength=200)
        self.lbl_progress.pack(anchor="w", pady=2)
        
        self.progress_bar = ttk.Progressbar(controls_subframe, orient="horizontal", mode="determinate", maximum=100)
        self.progress_bar.pack(fill="x", pady=(0, 5))
        
        preview_subframe = tk.LabelFrame(horizontal_layout, text=" Captured Face ", font=("Helvetica", 8, "bold"), fg=COLOR_DIGITAL_AMETHYST, bg="#FFFFFF", bd=1, relief="solid")
        preview_subframe.configure(padx=10, pady=10)
        preview_subframe.pack(side="right", padx=(25, 0), anchor="n")
        
        self.lbl_preview_pic = tk.Label(preview_subframe, bg="#F8FAFC", width=100, height=100)
        self.lbl_preview_pic.pack()
        self.show_preview_placeholder()
        
        train_frame = tk.Frame(frame, bg="#F8FAFC", width=250)
        train_frame.pack(side="right", fill="y", padx=(10, 20), pady=20)
        train_frame.pack_propagate(False)
        
        tk.Label(train_frame, text="TRAINING ENGINE", font=("Helvetica", 9, "bold"), fg=COLOR_TECH_EMERALD, bg="#F8FAFC").pack(anchor="w", padx=15, pady=(15, 5))
        tk.Label(train_frame, text="Re-train the model after adding or deleting student records to apply changes.", font=("Helvetica", 8), fg="#4A5568", bg="#F8FAFC", justify="left", wraplength=220).pack(anchor="w", padx=15, pady=(0, 20))
        
        self.btn_train = tk.Button(train_frame, text="Train Model Now", font=("Helvetica", 10, "bold"), bg=COLOR_TECH_EMERALD, fg=COLOR_TEXT_LIGHT, activebackground="#052518", activeforeground=COLOR_TEXT_LIGHT, borderwidth=0, pady=8, command=self.train_model)
        self.btn_train.pack(fill="x", padx=15, side="bottom", pady=20)

    def show_preview_placeholder(self):
        placeholder = np.zeros((100, 100, 3), dtype=np.uint8) + 220
        cv2.putText(placeholder, "No Face", (22, 53), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (120, 120, 120), 1, cv2.LINE_AA)
        
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
        
        self.progress_bar.configure(value=0)
        self.lbl_progress.configure(text="Initiating camera...", fg=COLOR_CYBER_GREEN)
        self.show_preview_placeholder()
        
        # Start capture state
        self.app.enroll_id = student_id
        self.app.enroll_name = student_name
        self.app.enroll_label_int = label_int
        self.app.enroll_count = 0
        self.app.last_capture_time = 0.0
        self.app.app_state = STATE_ENROLL
        
        self.btn_capture.configure(state="disabled")
        self.btn_train.configure(state="disabled")
        
        # Open the large Enrollment Guidance Center pop-up window
        self.app.enroll_guide_win = EnrollmentGuideWindow(self, self.app)

    def update_enroll_progress(self, count, aligned_face):
        self.progress_bar.configure(value=count)
        next_pose, color_hex = get_enroll_instruction(count + 1)
        self.lbl_progress.configure(text=f"Next Pose: {next_pose} ({count}/100)", fg=color_hex)
        
        try:
            face_resized = cv2.resize(aligned_face, (100, 100))
            rgb = cv2.cvtColor(face_resized, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(rgb)
            self.preview_photo = ImageTk.PhotoImage(image=pil_img)
            self.lbl_preview_pic.configure(image=self.preview_photo)
        except Exception as e:
            print(f"Failed to generate face preview: {e}")

    def on_enrollment_complete(self):
        self.btn_capture.configure(state="normal")
        self.btn_train.configure(state="normal")
        self.progress_bar.configure(value=100)
        self.lbl_progress.configure(text="Face enrollment complete! Re-train model.", fg=COLOR_CYBER_GREEN)
        
        self.entry_id.delete(0, tk.END)
        self.entry_name.delete(0, tk.END)
        
        self.refresh_students_table()
        messagebox.showinfo("Enrollment Completed", f"Successfully saved 100 face samples for '{self.app.enroll_name}'!\n\nClick the 'Train Model Now' button to finalize.")

    def train_model(self):
        path_list = [os.path.join(DATASET_DIR, f) for f in os.listdir(DATASET_DIR) if f.startswith("User.")]
        if not path_list:
            messagebox.showwarning("No Data", "No face samples found in 'dataset/'. Please enroll a student first.")
            return
            
        if self.app.recognizer is None:
            messagebox.showerror("Error", "Deep learning models are not loaded. Cannot extract embeddings.")
            return
            
        self.btn_train.configure(text="Extracting Embeddings...", bg=COLOR_TECH_EMERALD, fg=COLOR_TEXT_LIGHT, state="disabled")
        self.update()
        
        embeddings_db = {}
        processed_count = 0
        
        for image_path in path_list:
            try:
                img = cv2.imread(image_path)
                if img is None:
                    continue
                if img.shape[0] != 112 or img.shape[1] != 112:
                    img = cv2.resize(img, (112, 112))
                    
                filename = os.path.basename(image_path)
                parts = filename.split('.')
                if len(parts) >= 3:
                    label_str = parts[1]
                    
                    if label_str not in embeddings_db:
                        embeddings_db[label_str] = []
                        
                    feat = self.app.recognizer.feature(img)
                    embeddings_db[label_str].append(feat.flatten().tolist())
                    
                    flipped_img = cv2.flip(img, 1)
                    flipped_feat = self.app.recognizer.feature(flipped_img)
                    embeddings_db[label_str].append(flipped_feat.flatten().tolist())
                    
                    processed_count += 1
            except Exception as e:
                print(f"Skipping file {image_path}: {e}")
                
        if not embeddings_db:
            messagebox.showerror("Error", "Could not extract any valid face embeddings.")
            self.btn_train.configure(text="Train Model Now", bg=COLOR_TECH_EMERALD, fg=COLOR_TEXT_LIGHT, state="normal")
            return
            
        try:
            with open(self.app.embeddings_file, "w") as f:
                json.dump(embeddings_db, f)
            self.app.load_trained_model()
            messagebox.showinfo("Model Updated", f"Face embeddings extracted and saved successfully!\nProcessed {processed_count} images (total {processed_count * 2} reference vectors with mirroring).")
        except Exception as e:
            messagebox.showerror("Saving Failed", f"An error occurred saving embeddings: {e}")
            
        self.btn_train.configure(text="Train Model Now", bg=COLOR_TECH_EMERALD, fg=COLOR_TEXT_LIGHT, state="normal")

    def build_students_tab(self, frame):
        title = tk.Label(frame, text="R E G I S T E R E D   D A T A B A S E", font=("Helvetica", 10, "bold"), fg="#1A1F26", bg="#FFFFFF")
        title.pack(anchor="w", padx=20, pady=(20, 5))
        
        subtitle = tk.Label(frame, text="List of currently enrolled students. Delete records to clear database.", font=("Helvetica", 8), fg="#4A5568", bg="#FFFFFF")
        subtitle.pack(anchor="w", padx=20, pady=(0, 15))
        
        table_frame = tk.Frame(frame, bg="#FFFFFF")
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
        
        control_bar = tk.Frame(frame, bg="#FFFFFF")
        control_bar.pack(fill="x", padx=20, pady=(5, 20))
        
        self.btn_delete = tk.Button(control_bar, text="Delete Selected Record", font=("Helvetica", 9, "bold"), bg=COLOR_TECH_PINK, fg=COLOR_TEXT_LIGHT, activebackground="#d64e75", activeforeground=COLOR_TEXT_LIGHT, borderwidth=0, padx=15, pady=8, command=self.delete_student_record)
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

    def build_history_tab(self, frame):
        title = tk.Label(frame, text="A T T E N D A N C E   L O G   H I S T O R Y", font=("Helvetica", 10, "bold"), fg="#1A1F26", bg="#FFFFFF")
        title.pack(anchor="w", padx=20, pady=(20, 5))
        
        subtitle = tk.Label(frame, text="Complete log records stored in attendance.csv.", font=("Helvetica", 8), fg="#4A5568", bg="#FFFFFF")
        subtitle.pack(anchor="w", padx=20, pady=(0, 15))
        
        table_frame = tk.Frame(frame, bg="#FFFFFF")
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
        
        control_bar = tk.Frame(frame, bg="#FFFFFF")
        control_bar.pack(fill="x", padx=20, pady=(5, 20))
        
        btn_clear = tk.Button(control_bar, text="Clear Log File", font=("Helvetica", 9, "bold"), bg=COLOR_TECH_PINK, fg=COLOR_TEXT_LIGHT, activebackground="#d64e75", activeforeground=COLOR_TEXT_LIGHT, borderwidth=0, padx=15, pady=8, command=self.clear_logs)
        btn_clear.pack(side="left")
        
        btn_refresh = tk.Button(control_bar, text="Refresh Logs List", font=("Helvetica", 9, "bold"), bg=COLOR_TECH_EMERALD, fg=COLOR_TEXT_LIGHT, activebackground="#052518", activeforeground=COLOR_TEXT_LIGHT, borderwidth=0, padx=15, pady=8, command=self.refresh_history_table)
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
        self.window.title("CDAC — Biometric Face Recognition System")
        self.window.geometry("1100x700")
        self.window.configure(bg=COLOR_PLATINUM_WHITE)
        self.window.minsize(1000, 600)
        
        # Internal state variables
        self.app_state = STATE_OFF
        self.cap = None
        self.enroll_id = ""
        self.enroll_name = ""
        self.enroll_count = 0
        self.enroll_label_int = 0
        self.last_capture_time = 0.0
        self.students_map = {}
        self.next_label_id = 1
        
        # Theme config
        self.current_theme = "light"
        
        # Admin Center & Enrollment Guide Windows Pointers
        self.admin_center_win = None
        self.enroll_guide_win = None
        
        # Paths for ONNX models and embeddings
        self.yunet_path = os.path.join(TRAINER_DIR, "face_detection_yunet_2023mar.onnx")
        self.sface_path = os.path.join(TRAINER_DIR, "face_recognition_sface_2021dec.onnx")
        self.embeddings_file = os.path.join(TRAINER_DIR, "embeddings.json")
        
        self.detector = None
        self.recognizer = None
        self.is_trained = False
        
        self.load_student_mappings()
        self.load_trained_model()
        
        self.today_marked_cache = set()
        self.load_today_attendance_cache()
        
        self.setup_styles()
        self.create_widgets()
        
        # Check and download models in background if missing
        self.check_and_download_models()
        
        # Apply theme colors initial state
        self.apply_theme_colors()
        
        self.window.protocol("WM_DELETE_WINDOW", self.on_close)

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        
        style.configure("Treeview",
                        background="#FFFFFF",
                        foreground="#1A1F26",
                        fieldbackground="#FFFFFF",
                        rowheight=25,
                        font=("Helvetica", 9))
        style.configure("Treeview.Heading",
                        background="#F8FAFC",
                        foreground=COLOR_TECH_EMERALD,
                        font=("Helvetica", 9, "bold"),
                        borderwidth=1,
                        relief="flat")
        style.map("Treeview",
                  background=[("selected", COLOR_TECH_EMERALD)],
                  foreground=[("selected", COLOR_TEXT_LIGHT)])
                  
        style.configure("TScrollbar",
                        gripcount=0,
                        background="#F8FAFC",
                        troughcolor="#FFFFFF",
                        bordercolor="#F8FAFC",
                        arrowcolor=COLOR_TECH_EMERALD)

    def toggle_theme(self):
        if self.current_theme == "light":
            self.current_theme = "dark"
            self.btn_theme_toggle.configure(text="☀️ Light Mode")
        else:
            self.current_theme = "light"
            self.btn_theme_toggle.configure(text="🌙 Dark Mode")
        self.apply_theme_colors()

    def apply_theme_colors(self):
        if self.current_theme == "light":
            bg_dark = "#F8FAFC"
            bg_card = "#FFFFFF"
            text_primary = "#1A1F26"
            text_muted = "#4A5568"
            btn_header_bg = "#E2E8F0"
            btn_header_fg = "#1A1F26"
        else:
            bg_dark = "#1A1F26"
            bg_card = "#242B35"
            text_primary = "#F8FAFC"
            text_muted = "#A3B8CC"
            btn_header_bg = "#2E3743"
            btn_header_fg = "#F8FAFC"
            
        self.window.configure(bg=bg_dark)
        
        # Header button configurations
        self.btn_theme_toggle.configure(bg=btn_header_bg, fg=btn_header_fg, activebackground=btn_header_bg, activeforeground=btn_header_fg)
        self.btn_admin_portal.configure(bg=btn_header_bg, fg=btn_header_fg, activebackground=btn_header_bg, activeforeground=btn_header_fg)
        
        # Recursive widget updates from main_container
        def apply_colors(w):
            w_class = w.winfo_class()
            w_name = str(w).lower()
            
            if w_class == "Label":
                if "status_pill" in w_name:
                    pass
                elif "info_label" in w_name:
                    w.configure(bg=bg_card, fg=text_muted)
                elif "welcome" in w_name or "card" in w_name:
                    w.configure(bg=bg_dark, fg=text_primary if "name" in w_name or "id" in w_name or "time" in w_name else text_muted)
                else:
                    w.configure(bg=bg_card, fg=text_primary)
            elif w_class == "Frame":
                if "main_container" in w_name:
                    w.configure(bg=bg_dark)
                elif "card_frame" in w_name:
                    w.configure(bg=bg_dark)
                elif "left_panel" in w_name:
                    w.configure(bg=bg_card)
                elif "center_panel" in w_name:
                    w.configure(bg=bg_card)
                else:
                    w.configure(bg=bg_card)
            elif w_class == "Canvas":
                if "avatar_canvas" in w_name:
                    w.configure(bg=bg_dark)
            elif w_class == "Button":
                txt = w.cget("text")
                if "Start Video Capture" in txt or "Stop Video Capture" in txt:
                    pass
                elif "Start Attendance Scanner" in txt or "Stop Scanner Mode" in txt:
                    pass
                else:
                    w.configure(bg=btn_header_bg, fg=btn_header_fg)
                    
            for child in w.winfo_children():
                apply_colors(child)
                
        apply_colors(self.main_container)
        
        # Dynamic Card configuration
        border_col = "#E2E8F0" if self.current_theme == "light" else "#2E3743"
        if self.lbl_welcome_status.cget("text") == "VERIFICATION SUCCESSFUL":
            self.card_frame.configure(highlightbackground=COLOR_CYBER_GREEN, highlightcolor=COLOR_CYBER_GREEN, highlightthickness=2)
            self.lbl_welcome_name.configure(fg=COLOR_TECH_EMERALD if self.current_theme == "light" else COLOR_CYBER_GREEN)
            self.avatar_canvas.itemconfig(self.avatar_circle, fill=bg_dark, outline=COLOR_CYBER_GREEN)
            self.avatar_canvas.itemconfig(self.avatar_text, fill=COLOR_CYBER_GREEN)
        else:
            self.card_frame.configure(highlightbackground=border_col, highlightcolor=border_col, highlightthickness=1)
            self.avatar_canvas.itemconfig(self.avatar_circle, fill=bg_card, outline=border_col)
            self.avatar_canvas.itemconfig(self.avatar_text, fill=text_muted)
            
        if self.app_state == STATE_OFF:
            self.show_camera_offline_screen()
            
        if self.status_pill.cget("text") not in ["DOWNLOADING MODELS", "SCANNING BIOMETRICS", "DOWNLOAD ERROR"]:
            self.status_pill.configure(bg=bg_dark, fg=text_primary)
            
        # Footer update
        self.footer_frame.configure(bg=bg_dark)
        self.powered_by_container.configure(bg=bg_dark)
        self.hexa_canvas.configure(bg=bg_dark)
        self.lbl_powered.configure(bg=bg_dark, fg=text_muted)
        
        self.hexa_canvas.delete("all")
        nodes = [(12, 3), (21, 8), (21, 17), (12, 22), (3, 17), (3, 8)]
        for i in range(6):
            p1 = nodes[i]
            p2 = nodes[(i+1)%6]
            self.hexa_canvas.create_line(p1[0], p1[1], p2[0], p2[1], fill=COLOR_CYBER_GREEN, width=1.5)
        for x, y in nodes:
            self.hexa_canvas.create_oval(x-1.5, y-1.5, x+1.5, y+1.5, fill=COLOR_TECH_PINK, outline=COLOR_CYBER_GREEN, width=0.5)
        inner_nodes = [(12, 8), (16, 10), (16, 15), (12, 17), (8, 15), (8, 10)]
        self.hexa_canvas.create_polygon(inner_nodes, fill="", outline=COLOR_CYBER_GREEN, width=1)
        
        # Style variables configuration
        style = ttk.Style()
        style.configure("Treeview", background=bg_card, foreground=text_primary, fieldbackground=bg_card)
        style.configure("Treeview.Heading", background=bg_dark, foreground=COLOR_TECH_EMERALD if self.current_theme == "light" else COLOR_PLATINUM_WHITE)
        style.configure("TScrollbar", background=bg_dark, troughcolor=bg_card, bordercolor=bg_dark)
        style.configure("TNotebook", background=bg_dark)
        style.configure("TNotebook.Tab", background="#E2E8F0" if self.current_theme == "light" else "#242B35", foreground=text_muted)
        style.map("TNotebook.Tab", background=[("selected", bg_card)], foreground=[("selected", text_primary)])
        
        if self.admin_center_win is not None:
            self.admin_center_win.apply_theme_colors(self.current_theme)

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
        if os.path.exists(self.embeddings_file):
            try:
                with open(self.embeddings_file, "r") as f:
                    self.embeddings_map = json.load(f)
                self.embeddings_np = {}
                for label_str, emb_list in self.embeddings_map.items():
                    self.embeddings_np[label_str] = [np.array(emb, dtype=np.float32).reshape(1, -1) for emb in emb_list]
                self.is_trained = len(self.embeddings_np) > 0
            except Exception as e:
                print(f"Error loading embeddings: {e}")
                self.embeddings_np = {}
                self.is_trained = False
        else:
            self.embeddings_np = {}
            self.is_trained = False

    def check_and_download_models(self):
        if os.path.exists(self.yunet_path) and os.path.exists(self.sface_path):
            self.init_dl_models()
            return
            
        self.btn_toggle_cam.configure(state="disabled")
        self.btn_admin_portal.configure(state="disabled")
        self.update_status_bar("DOWNLOADING MODELS", COLOR_TEXT_LIGHT, COLOR_MATTE_CHARCOAL)
        
        def download_thread():
            import urllib.request
            import ssl
            
            ssl_context = ssl._create_unverified_context()
            
            urls = [
                ("YuNet Face Detector", "https://huggingface.co/opencv/face_detection_yunet/resolve/main/face_detection_yunet_2023mar.onnx", self.yunet_path),
                ("SFace Recognizer", "https://huggingface.co/opencv/face_recognition_sface/resolve/main/face_recognition_sface_2021dec.onnx", self.sface_path)
            ]
            
            for name, url, path in urls:
                if os.path.exists(path):
                    continue
                    
                self.window.after(0, lambda n=name: self.info_label.configure(text=f"Downloading {n}...\nThis may take a minute."))
                
                try:
                    os.makedirs(os.path.dirname(path), exist_ok=True)
                    
                    req = urllib.request.Request(
                        url, 
                        headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
                    )
                    
                    with urllib.request.urlopen(req, context=ssl_context) as response, open(path, 'wb') as out_file:
                        total_size = int(response.getheader('Content-Length', 0))
                        downloaded = 0
                        block_size = 8192
                        
                        while True:
                            buffer = response.read(block_size)
                            if not buffer:
                                break
                            downloaded += len(buffer)
                            out_file.write(buffer)
                            
                            if total_size > 0:
                                percent = min(100, int(downloaded * 100 / total_size))
                                self.window.after(0, lambda p=percent, n=name: self.update_status_bar(f"DL {n} {p}%", COLOR_TEXT_LIGHT, COLOR_MATTE_CHARCOAL))
                except Exception as e:
                    if os.path.exists(path):
                        try:
                            os.remove(path)
                        except Exception:
                            pass
                    self.window.after(0, lambda err=e: messagebox.showerror("Download Error", f"Failed to download deep learning models: {err}\n\nPlease check your internet connection and restart."))
                    self.window.after(0, self.on_download_failed)
                    return
            
            self.window.after(0, self.on_download_success)
            
        import threading
        threading.Thread(target=download_thread, daemon=True).start()

    def init_dl_models(self):
        try:
            self.detector = cv2.FaceDetectorYN.create(
                self.yunet_path, "", (320, 240), score_threshold=0.6, nms_threshold=0.3
            )
            self.recognizer = cv2.FaceRecognizerSF.create(self.sface_path, "")
            print("YuNet and SFace models initialized successfully.")
        except Exception as e:
            messagebox.showerror("Initialization Error", f"Failed to initialize deep learning models: {e}")

    def on_download_success(self):
        self.init_dl_models()
        self.btn_toggle_cam.configure(state="normal")
        self.btn_admin_portal.configure(state="normal")
        self.update_status_bar("CAMERA OFFLINE", COLOR_TEXT_LIGHT, COLOR_MATTE_CHARCOAL)
        self.info_label.configure(text="Deep learning models loaded.\nClick 'Start Video Capture'.")
        messagebox.showinfo("Success", "Deep learning models downloaded and loaded successfully!")

    def on_download_failed(self):
        self.update_status_bar("DOWNLOAD ERROR", COLOR_TEXT_LIGHT, COLOR_TECH_PINK)
        self.info_label.configure(text="Failed to download models.\nCheck network and restart.")

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
        header_frame = tk.Frame(self.window, bg=COLOR_BG_HEADER, height=60)
        header_frame.pack(side="top", fill="x")
        header_frame.pack_propagate(False)
        
        logo_text_frame = tk.Frame(header_frame, bg=COLOR_BG_HEADER)
        logo_text_frame.pack(side="left", padx=20, pady=8)
        
        lbl_wordmark = tk.Label(logo_text_frame, text="C D A C", font=("Helvetica", 14, "bold"), fg=COLOR_TEXT_LIGHT, bg=COLOR_BG_HEADER)
        lbl_wordmark.pack(anchor="w")
        
        lbl_slogan = tk.Label(logo_text_frame, text="BIOMETRIC ATTENDANCE SYSTEM", font=("Helvetica", 7, "bold"), fg=COLOR_CYBER_GREEN, bg=COLOR_BG_HEADER)
        lbl_slogan.pack(anchor="w", pady=(2, 0))
        
        header_subtitle = tk.Label(header_frame, text="• Check-In Terminal", font=("Helvetica", 11), fg=COLOR_PLATINUM_WHITE, bg=COLOR_BG_HEADER)
        header_subtitle.pack(side="left", pady=15)
        
        # 🌓 Toggle Theme Button
        self.btn_theme_toggle = tk.Button(header_frame, text="🌙 Dark Mode", font=("Helvetica", 10, "bold"), bg=COLOR_MATTE_CHARCOAL, fg=COLOR_PLATINUM_WHITE, activebackground="#2E3743", activeforeground=COLOR_PLATINUM_WHITE, borderwidth=0, padx=12, pady=5, command=self.toggle_theme)
        self.btn_theme_toggle.pack(side="right", padx=20, pady=12)
        
        # ⚙️ Admin Operations Button
        self.btn_admin_portal = tk.Button(header_frame, text="⚙️ Admin Operations", font=("Helvetica", 10, "bold"), bg=COLOR_MATTE_CHARCOAL, fg=COLOR_PLATINUM_WHITE, activebackground="#2E3743", activeforeground=COLOR_PLATINUM_WHITE, borderwidth=0, padx=12, pady=5, command=self.open_admin_auth)
        self.btn_admin_portal.pack(side="right", padx=(0, 5), pady=12)
        
        self.status_pill = tk.Label(header_frame, text="CAMERA OFFLINE", font=("Helvetica", 9, "bold"), fg="#1A1F26", bg="#F8FAFC", padx=10, pady=3)
        self.status_pill.pack(side="right", padx=5, pady=15)
        
        # Powered by Hexonn Labs Footer Widget at the bottom center
        self.footer_frame = tk.Frame(self.window, bg="#F8FAFC")
        self.footer_frame.pack(side="bottom", fill="x", pady=(0, 10))
        
        self.powered_by_container = tk.Frame(self.footer_frame, bg="#F8FAFC")
        self.powered_by_container.pack(anchor="center")
        
        self.hexa_canvas = tk.Canvas(self.powered_by_container, width=25, height=25, bg="#F8FAFC", highlightthickness=0)
        self.hexa_canvas.pack(side="left", padx=5)
        
        self.lbl_powered = tk.Label(self.powered_by_container, text="Powered by Hexonn Labs", font=("Helvetica", 8, "bold"), fg="#4A5568", bg="#F8FAFC")
        self.lbl_powered.pack(side="left", padx=5)
        
        # Kiosk Layout Split
        main_container = tk.Frame(self.window, bg="#F8FAFC")
        main_container.pack(side="top", fill="both", expand=True, padx=15, pady=(15, 0))
        self.main_container = main_container
        
        # ────────────────────────────────────────────────────────
        # Left Panel: Controls & Visual Welcome Check-in Card
        # ────────────────────────────────────────────────────────
        left_panel = tk.Frame(main_container, bg="#FFFFFF", width=300)
        left_panel.pack(side="left", fill="y", padx=(0, 10))
        left_panel.pack_propagate(False)
        self.left_panel = left_panel
        
        panel_title = tk.Label(left_panel, text="T E R M I N A L   C O N T R O L", font=("Helvetica", 10, "bold"), fg="#1A1F26", bg="#FFFFFF")
        panel_title.pack(anchor="w", padx=15, pady=(15, 10))
        self.panel_title = panel_title
        
        sep = tk.Frame(left_panel, height=1, bg="#F8FAFC")
        sep.pack(fill="x", padx=15, pady=(0, 15))
        self.sep = sep
        
        self.btn_toggle_cam = tk.Button(left_panel, text="Start Video Capture", font=("Helvetica", 10, "bold"), bg=COLOR_DIGITAL_AMETHYST, fg=COLOR_TEXT_LIGHT, activebackground="#5E2299", activeforeground=COLOR_TEXT_LIGHT, borderwidth=0, pady=8, command=self.toggle_camera)
        self.btn_toggle_cam.pack(fill="x", padx=15, pady=5)
        
        self.btn_scan = tk.Button(left_panel, text="Start Attendance Scanner", font=("Helvetica", 10, "bold"), bg=COLOR_TECH_EMERALD, fg=COLOR_TEXT_LIGHT, activebackground="#052518", activeforeground=COLOR_TEXT_LIGHT, borderwidth=0, state="disabled", pady=8, command=self.start_attendance_scanner)
        self.btn_scan.pack(fill="x", padx=15, pady=10)
        
        lbl_welcome_header = tk.Label(left_panel, text="Current Scan Status", font=("Helvetica", 9, "bold"), fg="#4A5568", bg="#FFFFFF")
        lbl_welcome_header.pack(anchor="w", padx=15, pady=(20, 5))
        self.lbl_welcome_header = lbl_welcome_header
        
        # Visual Check-in welcome card
        self.card_frame = tk.Frame(left_panel, bg="#F8FAFC", highlightbackground="#E2E8F0", highlightcolor="#E2E8F0", highlightthickness=1)
        self.card_frame.pack(fill="both", expand=True, padx=15, pady=(0, 20))
        
        self.lbl_welcome_status = tk.Label(self.card_frame, text="AWAITING SCANS", font=("Helvetica", 9, "bold"), fg="#4A5568", bg="#F8FAFC")
        self.lbl_welcome_status.pack(pady=(20, 10))
        
        self.avatar_canvas = tk.Canvas(self.card_frame, width=80, height=80, bg="#F8FAFC", highlightthickness=0)
        self.avatar_canvas.pack(pady=5)
        self.avatar_circle = self.avatar_canvas.create_oval(5, 5, 75, 75, fill="#FFFFFF", outline="#E2E8F0", width=2)
        self.avatar_text = self.avatar_canvas.create_text(40, 40, text="?", font=("Helvetica", 20, "bold"), fill="#4A5568")
        
        self.lbl_welcome_name = tk.Label(self.card_frame, text="No active scan", font=("Helvetica", 13, "bold"), fg="#4A5568", bg="#F8FAFC", wraplength=250)
        self.lbl_welcome_name.pack(pady=(10, 2))
        
        self.lbl_welcome_id = tk.Label(self.card_frame, text="ID: --", font=("Helvetica", 10), fg="#4A5568", bg="#F8FAFC")
        self.lbl_welcome_id.pack(pady=2)
        
        self.lbl_welcome_time = tk.Label(self.card_frame, text="Time: --:--:--", font=("Helvetica", 10, "bold"), fg="#4A5568", bg="#F8FAFC")
        self.lbl_welcome_time.pack(pady=(2, 20))
        
        # ────────────────────────────────────────────────────────
        # Center Panel: Active Camera Display Frame
        # ────────────────────────────────────────────────────────
        center_panel = tk.Frame(main_container, bg="#FFFFFF")
        center_panel.pack(side="left", fill="both", expand=True)
        self.center_panel = center_panel
        
        self.video_screen = tk.Label(center_panel, bg="#FFFFFF")
        self.video_screen.pack(fill="both", expand=True)
        self.show_camera_offline_screen()
        
        self.info_label = tk.Label(left_panel, text="System Offline.\nClick 'Start Video Capture'.", font=("Helvetica", 8), fg="#4A5568", bg="#FFFFFF", justify="left")
        self.info_label.pack(side="bottom", fill="x", padx=15, pady=10)

    def show_camera_offline_screen(self):
        width, height = 640, 480
        img = np.zeros((height, width, 3), dtype=np.uint8)
        
        if self.current_theme == "light":
            img[:] = (252, 250, 248) # Platinum White BGR
            text_color = (38, 31, 26) # Matte Charcoal BGR
        else:
            img[:] = (38, 31, 26) # Matte Charcoal BGR
            text_color = (252, 250, 248) # Platinum White BGR
            
        cv2.putText(img, "CDAC — TERMINAL OFFLINE", (width // 2 - 160, height // 2 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (40, 60, 10), 2, cv2.LINE_AA) # Tech Emerald BGR
        cv2.putText(img, "Please start the video stream from controls", (width // 2 - 180, height // 2 + 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, text_color, 1, cv2.LINE_AA)
        cv2.rectangle(img, (20, 20), (width - 20, height - 20), (129, 185, 16), 1) # Cyber Green BGR
        
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(rgb)
        self.photo = ImageTk.PhotoImage(image=pil_img)
        self.video_screen.configure(image=self.photo)

    def open_admin_auth(self):
        PasswordDialog(self.window, self.current_theme, self.launch_admin_portal)

    def launch_admin_portal(self, authenticated):
        if authenticated:
            if self.admin_center_win is not None:
                self.admin_center_win.deiconify()
                self.admin_center_win.lift()
            else:
                AdminCenter(self.window, self)

    def update_welcome_card(self, student_id, name, time_str):
        self.lbl_welcome_status.configure(text="VERIFICATION SUCCESSFUL", fg=COLOR_CYBER_GREEN)
        self.lbl_welcome_name.configure(text=name, fg=COLOR_TECH_EMERALD if self.current_theme == "light" else COLOR_PLATINUM_WHITE)
        self.lbl_welcome_id.configure(text=f"Student ID: {student_id}", fg=COLOR_MATTE_CHARCOAL if self.current_theme == "light" else COLOR_PLATINUM_WHITE)
        self.lbl_welcome_time.configure(text=f"Logged In At: {time_str}", fg=COLOR_TECH_PINK)
        
        initials = "".join([n[0].upper() for n in name.split() if n])[:2] if name else "?"
        self.avatar_canvas.itemconfig(self.avatar_circle, fill=COLOR_PLATINUM_WHITE if self.current_theme == "light" else "#242B35", outline=COLOR_CYBER_GREEN)
        self.avatar_canvas.itemconfig(self.avatar_text, text=initials, fill=COLOR_CYBER_GREEN)
        
        self.card_frame.configure(highlightbackground=COLOR_CYBER_GREEN, highlightcolor=COLOR_CYBER_GREEN, highlightthickness=2)

    def clear_welcome_card(self):
        self.lbl_welcome_status.configure(text="AWAITING SCANS", fg="#4A5568" if self.current_theme == "light" else "#A3B8CC")
        self.lbl_welcome_name.configure(text="No active scan", fg="#4A5568" if self.current_theme == "light" else "#A3B8CC")
        self.lbl_welcome_id.configure(text="ID: --", fg="#4A5568" if self.current_theme == "light" else "#A3B8CC")
        self.lbl_welcome_time.configure(text="Time: --:--:--", fg="#4A5568" if self.current_theme == "light" else "#A3B8CC")
        
        border_col = "#E2E8F0" if self.current_theme == "light" else "#2E3743"
        self.avatar_canvas.itemconfig(self.avatar_circle, fill="#FFFFFF" if self.current_theme == "light" else "#242B35", outline=border_col)
        self.avatar_canvas.itemconfig(self.avatar_text, text="?", fill="#4A5568" if self.current_theme == "light" else "#A3B8CC")
        
        self.card_frame.configure(highlightbackground=border_col, highlightcolor=border_col, highlightthickness=1)

    def update_status_bar(self, text, fg, bg):
        self.status_pill.configure(text=text, fg=fg, bg=bg)

    def toggle_camera(self):
        if self.app_state == STATE_OFF:
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                messagebox.showerror("Webcam Error", "Could not access system camera.")
                return
            
            self.app_state = STATE_IDLE
            self.btn_toggle_cam.configure(text="Stop Video Capture", bg=COLOR_TECH_PINK, fg=COLOR_TEXT_LIGHT, activebackground="#d64e75")
            self.btn_scan.configure(state="normal")
            
            self.update_status_bar("CAMERA IDLE", COLOR_TEXT_LIGHT, COLOR_MATTE_CHARCOAL)
            self.info_label.configure(text="Webcam active.\nStart scanner mode to mark attendance.")
            self.process_camera_feed()
        else:
            self.stop_all_active_modes()
            self.app_state = STATE_OFF
            if self.cap:
                self.cap.release()
                self.cap = None
            
            self.btn_toggle_cam.configure(text="Start Video Capture", bg=COLOR_DIGITAL_AMETHYST, fg=COLOR_TEXT_LIGHT, activebackground="#5E2299")
            self.btn_scan.configure(text="Start Attendance Scanner", bg=COLOR_TECH_EMERALD, fg=COLOR_TEXT_LIGHT, state="disabled")
            
            text_primary = "#1A1F26" if self.current_theme == "light" else "#F8FAFC"
            bg_dark = "#F8FAFC" if self.current_theme == "light" else "#1A1F26"
            self.update_status_bar("CAMERA OFFLINE", text_primary, bg_dark)
            self.info_label.configure(text="System Offline.\nClick 'Start Video Capture'.")
            self.show_camera_offline_screen()
            self.clear_welcome_card()

    def stop_all_active_modes(self):
        if self.app_state == STATE_SCAN:
            self.btn_scan.configure(text="Start Attendance Scanner", bg=COLOR_TECH_EMERALD, fg=COLOR_TEXT_LIGHT)
        elif self.app_state == STATE_ENROLL:
            self.enroll_count = 0
            if self.enroll_guide_win is not None:
                try:
                    self.enroll_guide_win.destroy()
                except Exception:
                    pass
                self.enroll_guide_win = None
            if self.admin_center_win is not None:
                self.admin_center_win.btn_capture.configure(state="normal")
                self.admin_center_win.btn_train.configure(state="normal")
                self.admin_center_win.progress_bar.configure(value=0)
                self.admin_center_win.lbl_progress.configure(text="Capture aborted.", fg=COLOR_TECH_PINK)
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
            self.btn_scan.configure(text="Start Attendance Scanner", bg=COLOR_TECH_EMERALD, fg=COLOR_TEXT_LIGHT)
            text_primary = "#1A1F26" if self.current_theme == "light" else "#F8FAFC"
            bg_dark = "#F8FAFC" if self.current_theme == "light" else "#1A1F26"
            self.update_status_bar("CAMERA IDLE", text_primary, bg_dark)
            self.info_label.configure(text="Scanner stopped. Camera active.")
        else:
            self.stop_all_active_modes()
            self.app_state = STATE_SCAN
            self.btn_scan.configure(text="Stop Scanner Mode", bg=COLOR_TECH_PINK, fg=COLOR_TEXT_LIGHT)
            self.update_status_bar("SCANNING BIOMETRICS", COLOR_TEXT_LIGHT, COLOR_TECH_EMERALD)
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
        h_frame, w_frame, _ = frame.shape
        
        faces = None
        if self.detector is not None:
            try:
                self.detector.setInputSize((w_frame, h_frame))
                _, faces = self.detector.detect(frame)
            except Exception as e:
                print(f"Error running detector: {e}")
                
        if faces is not None and len(faces) > 0:
            for face in faces:
                bbox = face[0:4].astype(np.int32)
                x, y, w, h = bbox[0], bbox[1], bbox[2], bbox[3]
                
                if self.app_state == STATE_ENROLL:
                    current_time = time.time()
                    if current_time - self.last_capture_time >= 0.20:
                        if self.recognizer is not None:
                            try:
                                aligned_face = self.recognizer.alignCrop(frame, face)
                                self.enroll_count += 1
                                face_img_path = os.path.join(DATASET_DIR, f"User.{self.enroll_label_int}.{self.enroll_count}.jpg")
                                cv2.imwrite(face_img_path, aligned_face)
                                self.last_capture_time = current_time
                                
                                # Update progress in enrollment guide pop-up window
                                if self.enroll_guide_win is not None:
                                    self.enroll_guide_win.update_guide(self.enroll_count, aligned_face)
                                
                                # Sync preview on admin center
                                if self.admin_center_win is not None:
                                    self.admin_center_win.update_enroll_progress(self.enroll_count, aligned_face)
                            except Exception as e:
                                print(f"Error aligning/saving face: {e}")
                                
                    pose_bgr = get_pose_bgr(self.enroll_count + 1)
                    cv2.rectangle(frame, (x, y), (x+w, y+h), pose_bgr, 2)
                    cv2.putText(frame, f"Posing... ({self.enroll_count}/100)", (x, y-10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, pose_bgr, 2)
                    
                    if self.enroll_count >= 100:
                        self.app_state = STATE_IDLE
                        self.btn_toggle_cam.configure(state="normal")
                        self.btn_scan.configure(state="normal")
                        self.btn_admin_portal.configure(state="normal")
                        
                        # Close the guidance center pop-up
                        if self.enroll_guide_win is not None:
                            try:
                                self.enroll_guide_win.destroy()
                            except Exception:
                                pass
                            self.enroll_guide_win = None
                            
                        if self.admin_center_win is not None:
                            self.admin_center_win.on_enrollment_complete()
                        
                        text_primary = "#1A1F26" if self.current_theme == "light" else "#F8FAFC"
                        bg_dark = "#F8FAFC" if self.current_theme == "light" else "#1A1F26"
                        self.update_status_bar("CAMERA IDLE", text_primary, bg_dark)
                        self.info_label.configure(text="Face enrollment completed!\nPlease train the model.")
                    
                    break
                    
                elif self.app_state == STATE_SCAN and self.is_trained:
                    if self.recognizer is not None:
                        try:
                            aligned_face = self.recognizer.alignCrop(frame, face)
                            query_feat = self.recognizer.feature(aligned_face)
                            
                            best_student_id = None
                            best_student_name = None
                            best_score = -1.0
                            
                            for label_str, ref_feats in self.embeddings_np.items():
                                for ref_feat in ref_feats:
                                    score = self.recognizer.match(query_feat, ref_feat, cv2.FaceRecognizerSF_FR_COSINE)
                                    if score > best_score:
                                        best_score = score
                                        student_info = self.students_map.get(label_str)
                                        if student_info:
                                            best_student_id = student_info["id"]
                                            best_student_name = student_info["name"]
                                            
                            if best_score >= 0.40:
                                self.log_attendance(best_student_id, best_student_name)
                                cv2.rectangle(frame, (x, y), (x+w, y+h), (129, 185, 16), 2)
                                
                                conf_pct = min(100, max(0, int(best_score * 100)))
                                label_str = f"{best_student_name} ({conf_pct}%)"
                                cv2.putText(frame, label_str, (x, y-10),
                                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (129, 185, 16), 2)
                                
                                if best_student_id in self.today_marked_cache:
                                    cv2.putText(frame, "[LOGGED]", (x, y+h+20),
                                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (129, 185, 16), 1, cv2.LINE_AA)
                            else:
                                cv2.rectangle(frame, (x, y), (x+w, y+h), (135, 95, 230), 2)
                                cv2.putText(frame, "Unknown Face", (x, y-10),
                                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (135, 95, 230), 2)
                        except Exception as e:
                            print(f"Error predicting face: {e}")
                            
                else:
                    cv2.rectangle(frame, (x, y), (x+w, y+h), (191, 44, 123), 2)
                    cv2.putText(frame, "Face Detected", (x, y-10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (191, 44, 123), 1)
        
        # Convert processed camera frames
        rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(rgb_image)
        self.photo = ImageTk.PhotoImage(image=pil_image)
        
        # Update the active display (either Guide pop-up window or main window)
        if self.app_state == STATE_ENROLL and self.enroll_guide_win is not None:
            self.enroll_guide_win.update_video_feed(self.photo)
            # Show active scanning indicator on main window
            placeholder = np.zeros((480, 640, 3), dtype=np.uint8)
            if self.current_theme == "light":
                placeholder[:] = (252, 250, 248)
                txt_color = (38, 31, 26)
            else:
                placeholder[:] = (38, 31, 26)
                txt_color = (252, 250, 248)
            cv2.putText(placeholder, "ENROLLMENT PROCESS RUNNING...", (130, 220),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (121, 44, 191), 2, cv2.LINE_AA) # Amethyst color BGR
            cv2.putText(placeholder, "Please look at the Enrollment Guide Window", (145, 255),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, txt_color, 1, cv2.LINE_AA)
            cv2.rectangle(placeholder, (20, 20), (620, 460), (121, 44, 191), 1)
            
            rgb_place = cv2.cvtColor(placeholder, cv2.COLOR_BGR2RGB)
            pil_place = Image.fromarray(rgb_place)
            self.photo_place = ImageTk.PhotoImage(image=pil_place)
            self.video_screen.configure(image=self.photo_place)
        else:
            self.video_screen.configure(image=self.photo)
            
        self.window.after(10, self.process_camera_feed)

    def on_close(self):
        self.stop_all_active_modes()
        self.app_state = STATE_OFF
        if self.cap:
            self.cap.release()
        self.window.destroy()


if __name__ == "__main__":
    # Enable high-DPI awareness on Windows to prevent blurry text
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            windll.user32.SetProcessDPIAware()
        except Exception:
            pass
            
    root = tk.Tk()
    app = AttendanceApp(root)
    root.mainloop()
