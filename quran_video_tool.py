import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk
import cv2
import numpy as np
import os
import subprocess
import threading
import json
import re

# =========================
# إعدادات عامة
# =========================
TARGET_SIZE = (720, 1280)
video1_paths = []
video2_paths = []
preview1_img = None
preview2_img = None
save_folder = ""
spinner_running = False
spinner_canvas = None
spinner_angle = 0

used_quran_titles_path = "used_quran_titles.txt"
json_log_path = os.path.join(os.path.dirname(__file__), "quran_titles_log.json")

video_titles = [
    "عش راحة القرآن", "استمع بخشوع لهذه الآية", "الله يُحدثك الآن…", "كلام يهز القلب",
    "لحظة نور مع هذه التلاوة", "إذا ضاق صدرك… اسمع", "من رحمة الله بك", "آية واحدة… تشفيك",
    "القرآن دواء القلوب", "دع القرآن يلامس قلبك", "هذا الصوت خُشوع نقي", "اسمعها كأنها أول مرة",
    "كلام رب العالمين.. لا مثيل له"
]

# =========================
# توليد عنوان فريد
# =========================
def get_unique_quran_title(index):
    if not os.path.exists(used_quran_titles_path):
        open(used_quran_titles_path, "w", encoding="utf-8").close()

    with open(used_quran_titles_path, "r", encoding="utf-8") as f:
        used = [line.strip() for line in f if line.strip()]

    available_titles = [t for t in video_titles if t not in used]

    if not available_titles:
        with open(used_quran_titles_path, "w", encoding="utf-8") as f:
            f.write("")
        available_titles = video_titles.copy()

    title = available_titles[index % len(available_titles)]

    with open(used_quran_titles_path, "a", encoding="utf-8") as f:
        f.write(title + "\n")

    if os.path.exists(json_log_path):
        with open(json_log_path, "r", encoding="utf-8") as jf:
            data = json.load(jf)
    else:
        data = []

    data.append({"index": index, "title": title})

    with open(json_log_path, "w", encoding="utf-8") as jf:
        json.dump(data, jf, ensure_ascii=False, indent=2)

    return title

# =========================
# مؤثر التحميل (Spinner)
# =========================
def start_spinner():
    global spinner_angle
    def update():
        global spinner_angle
        if spinner_running:
            spinner_canvas.delete("all")
            spinner_canvas.create_oval(5, 5, 25, 25, outline="white", width=3)
            spinner_canvas.create_arc(5, 5, 25, 25, start=spinner_angle,
                                      extent=90, style="arc", outline="green", width=3)
            spinner_angle = (spinner_angle + 10) % 360
            spinner_canvas.after(50, update)
    update()

def stop_spinner():
    spinner_canvas.delete("all")

# =========================
# اختيار الفيديوهات
# =========================
def select_video1_list():
    global video1_paths, preview1_img
    video1_paths = filedialog.askopenfilenames(title="اختر فيديوهات المؤثر",
                                               filetypes=[("Video files", "*.mp4 *.avi *.mov")])
    label1.config(text=f"{len(video1_paths)} فيديو تم تحديده.")
    if video1_paths:
        preview1_img = generate_preview(video1_paths[0])
        if preview1_img:
            preview1_label.config(image=preview1_img)
            preview1_label.image = preview1_img

def select_video2_list():
    global video2_paths, preview2_img
    video2_paths = filedialog.askopenfilenames(title="اختر فيديوهات الخلفية",
                                               filetypes=[("Video files", "*.mp4 *.avi *.mov")])
    label2.config(text=f"{len(video2_paths)} فيديو خلفية.")
    if video2_paths:
        preview2_img = generate_preview(video2_paths[0])
        if preview2_img:
            preview2_label.config(image=preview2_img)
            preview2_label.image = preview2_img

def select_output_folder():
    global save_folder
    save_folder = filedialog.askdirectory(title="اختر مجلد الحفظ")
    if save_folder:
        folder_label.config(text=f"📁 {save_folder}")
    else:
        folder_label.config(text="لم يتم التحديد")

# =========================
# معاينة الفيديو
# =========================
def generate_preview(video_path):
    cap = cv2.VideoCapture(video_path)
    ret, frame = cap.read()
    cap.release()
    if ret:
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame = cv2.resize(frame, (160, 90))
        img = Image.fromarray(frame)
        return ImageTk.PhotoImage(img)
    return None

# =========================
# معالجة الفيديوهات
# =========================
def get_video_frames(path, target_frames):
    cap = cv2.VideoCapture(path)
    frames = []
    while len(frames) < target_frames:
        ret, frame = cap.read()
        if not ret:
            break
        frame = cv2.resize(frame, TARGET_SIZE)
        frames.append(frame)
    cap.release()
    return frames

def get_video_frames_repeat(paths, target_frames):
    frames = []
    for path in paths:
        if len(frames) >= target_frames:
            break
        frames.extend(get_video_frames(path, target_frames - len(frames)))
    return frames[:target_frames]

def add_audio(source_path, target_path, output_path):
    command = [
        "ffmpeg", "-y", "-i", target_path, "-i", source_path,
        "-c:v", "copy", "-c:a", "aac", "-map", "0:v:0", "-map", "1:a:0", output_path
    ]
    subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def compress_video(input_path, output_path):
    command = [
        "ffmpeg", "-y", "-i", input_path,
        "-c:v", "libx265", "-crf", "23", "-preset", "fast",
        "-c:a", "aac", "-b:a", "128k", output_path
    ]
    subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def blend_single_video(video1_path, video2_paths, result_index, compress):
    global save_folder

    title = get_unique_quran_title(result_index)
    filename = re.sub(r"[؟،,:;!\"'<>\\/*|]", "", title).strip() + ".mp4"
    final_output = os.path.join(save_folder if save_folder else ".", filename)

    cap1 = cv2.VideoCapture(video1_path)
    fps = int(cap1.get(cv2.CAP_PROP_FPS)) or 25
    total_frames = int(cap1.get(cv2.CAP_PROP_FRAME_COUNT))
    background_frames = get_video_frames_repeat(video2_paths, total_frames)

    temp_output = f"temp_output_{result_index}.mp4"
    temp_with_audio = f"temp_with_audio_{result_index}.mp4"

    out = cv2.VideoWriter(temp_output, cv2.VideoWriter_fourcc(*'mp4v'), fps, TARGET_SIZE)

    for i in range(total_frames):
        ret1, frame1 = cap1.read()
        if not ret1:
            break
        h1, w1 = frame1.shape[:2]
        scale = min(TARGET_SIZE[0] / w1, TARGET_SIZE[1] / h1, 1.0)
        new_w, new_h = int(w1 * scale), int(h1 * scale)
        frame1_resized = cv2.resize(frame1, (new_w, new_h))
        x_offset = (TARGET_SIZE[0] - new_w) // 2
        y_offset = (TARGET_SIZE[1] - new_h) // 2
        background = background_frames[i].copy()
        roi = background[y_offset:y_offset+new_h, x_offset:x_offset+new_w]
        blended_roi = np.maximum(roi, frame1_resized)
        background[y_offset:y_offset+new_h, x_offset:x_offset+new_w] = blended_roi
        out.write(background)

    cap1.release()
    out.release()

    try:
        add_audio(video1_path, temp_output, temp_with_audio)
        if compress:
            compress_video(temp_with_audio, final_output)
            os.remove(temp_with_audio)
        else:
            os.rename(temp_with_audio, final_output)
    finally:
        if os.path.exists(temp_output):
            os.remove(temp_output)

# =========================
# تشغيل دفعة فيديوهات
# =========================
def start_batch_blend():
    global spinner_running
    if not video1_paths or not video2_paths:
        messagebox.showerror("خطأ", "يرجى تحديد كل من فيديوهات المقدمة والخلفيات.")
        return

    try:
        per_bg = int(bg_per_effect_entry.get())
    except:
        messagebox.showerror("خطأ", "يرجى إدخال رقم صحيح.")
        return

    spinner_running = True
    start_spinner()
    progress["maximum"] = len(video1_paths)

    bg_pointer = 0
    for idx, video1 in enumerate(video1_paths):
        if idx % per_bg == 0:
            bg_index = bg_pointer % len(video2_paths)
            main_bg = video2_paths[bg_index]
            bg_pointer += 1

        background_list = video2_paths[bg_index+1:] + video2_paths[:bg_index]
        selected_bgs = [main_bg] + list(background_list)

        status_label.config(text=f"📽️ معالجة الفيديو {idx+1}/{len(video1_paths)}...")
        root.update()
        blend_single_video(video1, selected_bgs, idx+1, compress_var.get())
        progress["value"] = idx + 1
        root.update()

    spinner_running = False
    stop_spinner()
    status_label.config(text="✅ تم الانتهاء من جميع الفيديوهات.")
    messagebox.showinfo("نجاح", "تم إنشاء الفيديوهات بنجاح.")

# =========================
# واجهة المستخدم
# =========================
root = tk.Tk()
root.title("🎥 Quran Video Blend Tool (H.265)")
root.geometry("600x740")
root.configure(bg="white")

compress_var = tk.BooleanVar(value=True)

tk.Label(root, text="🟦 فيديوهات المؤثر:", bg="white").pack(pady=5)
tk.Button(root, text="اختيار", command=select_video1_list, bg="#007ACC", fg="white").pack()
label1 = tk.Label(root, text="لم يتم التحديد", bg="white", fg="gray")
label1.pack()
preview1_label = tk.Label(root, bg="white")
preview1_label.pack(pady=5)

tk.Label(root, text="🟨 فيديوهات الخلفية:", bg="white").pack(pady=5)
tk.Button(root, text="اختيار", command=select_video2_list, bg="#007ACC", fg="white").pack()
label2 = tk.Label(root, text="لم يتم التحديد", bg="white", fg="gray")
label2.pack()
preview2_label = tk.Label(root, bg="white")
preview2_label.pack(pady=5)

tk.Label(root, text="🔁 عدد فيديوهات لكل خلفية:", bg="white").pack(pady=5)
bg_per_effect_entry = tk.Entry(root)
bg_per_effect_entry.insert(0, "3")
bg_per_effect_entry.pack()

tk.Label(root, text="📂 مجلد الحفظ:", bg="white").pack(pady=5)
tk.Button(root, text="تحديد", command=select_output_folder, bg="#444", fg="white").pack()
folder_label = tk.Label(root, text="لم يتم التحديد", bg="white", fg="gray")
folder_label.pack()

tk.Checkbutton(root, text="ضغط الفيديوهات (HEVC H.265)", variable=compress_var, bg="white").pack(pady=5)

tk.Button(root, text="🔄 ابدأ الدمج", command=lambda: threading.Thread(target=start_batch_blend).start(),
          bg="green", fg="white", font=("Arial", 14)).pack(pady=15)

progress = ttk.Progressbar(root, orient="horizontal", length=400, mode="determinate")
progress.pack(pady=10)

status_frame = tk.Frame(root, bg="white")
status_frame.pack()
status_label = tk.Label(status_frame, text="⚙️ في انتظار البدء...", fg="blue", bg="white")
status_label.pack(side="left", padx=5)
spinner_canvas = tk.Canvas(status_frame, width=30, height=30, bg="white", highlightthickness=0)
spinner_canvas.pack(side="left")

root.mainloop()
