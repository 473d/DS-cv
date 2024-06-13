import cv2
import mediapipe as mp
import tkinter as tk
from tkinter import ttk, colorchooser
from PIL import Image, ImageTk, ImageDraw
import numpy as np
import pyautogui
import pyaudio
import wave
import threading
import math

# لفتح كاميرا الويب وعرضها في نافذة صغيرة
class Webcam:
    def __init__(self, root, control_panel):
        self.root = root
        self.control_panel = control_panel
        self.video_frame = ttk.Label(root)
        self.video_frame.grid(row=0, column=0)
        self.cap = cv2.VideoCapture(0)
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands()
        self.drawing_utils = mp.solutions.drawing_utils
        self.allow_drawing = False
        self.canvas = None
        self.prev_x, self.prev_y = None, None
        self.update_frame()

    def update_frame(self):
        ret, frame = self.cap.read()
        if ret:
            frame = cv2.flip(frame, 1)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.hands.process(rgb_frame)
            if self.canvas is None:
                self.canvas = np.zeros_like(frame)

            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    self.drawing_utils.draw_landmarks(frame, hand_landmarks, self.mp_hands.HAND_CONNECTIONS)
                    thumb_tip = hand_landmarks.landmark[self.mp_hands.HandLandmark.THUMB_TIP]
                    index_tip = hand_landmarks.landmark[self.mp_hands.HandLandmark.INDEX_FINGER_TIP]
                    thumb_tip_coords = (int(thumb_tip.x * frame.shape[1]), int(thumb_tip.y * frame.shape[0]))
                    index_tip_coords = (int(index_tip.x * frame.shape[1]), int(index_tip.y * frame.shape[0]))
                    distance = math.hypot(index_tip_coords[0] - thumb_tip_coords[0], index_tip_coords[1] - thumb_tip_coords[1])

                    if  distance < 70:
                        place_to_write = self.control_panel.place_to_write.get()
                        if place_to_write == "الكاميرا":
                            if self.prev_x is not None and self.prev_y is not None:
                                cv2.line(self.canvas, (self.prev_x, self.prev_y), (index_tip_coords[0], index_tip_coords[1]), (255, 0, 0), 10)
                            self.prev_x, self.prev_y = index_tip_coords

                        elif place_to_write == "السبورة" and self.control_panel.whiteboard is not None:
                            self.control_panel.whiteboard.paint_with_coords(index_tip_coords[0], index_tip_coords[1])
                    else:
                        self.prev_x, self.prev_y = None, None

            combined = cv2.addWeighted(frame, 0.5, self.canvas, 0.5, 0)
            cv2image = cv2.cvtColor(combined, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(cv2image)
            imgtk = ImageTk.PhotoImage(image=img)
            self.video_frame.imgtk = imgtk
            self.video_frame.configure(image=imgtk)
        self.root.after(10, self.update_frame)

    def release(self):
        self.cap.release()



# تسجيل الشاشة
class ScreenRecorder:
    def __init__(self):
        self.is_recording = False
        self.frames = []
        self.screen_size = pyautogui.size()

    def record_screen(self):
        while self.is_recording:
            img = pyautogui.screenshot()
            frame = np.array(img)
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            self.frames.append(frame)

    def start_recording(self):
        self.is_recording = True
        self.recording_thread = threading.Thread(target=self.record_screen)
        self.recording_thread.start()

    def stop_recording(self, filename="recording.avi"):
        self.is_recording = False
        self.recording_thread.join()
        out = cv2.VideoWriter(filename, cv2.VideoWriter_fourcc(*'XVID'), 8, self.screen_size)
        for frame in self.frames:
            out.write(frame)
        out.release()

# تسجيل الصوت
class AudioRecorder:
    def __init__(self):
        self.is_recording = False
        self.frames = []
        self.sample_format = pyaudio.paInt16
        self.channels = 2
        self.fs = 44100
        self.chunk = 1024
        self.p = pyaudio.PyAudio()
        self.stream = None

    def start_recording(self):
        self.is_recording = True
        self.frames = []
        self.stream = self.p.open(format=self.sample_format,
                                  channels=self.channels,
                                  rate=self.fs,
                                  frames_per_buffer=self.chunk,
                                  input=True)
        self.recording_thread = threading.Thread(target=self.record_audio)
        self.recording_thread.start()

    def record_audio(self):
        while self.is_recording:
            data = self.stream.read(self.chunk)
            self.frames.append(data)

    def stop_recording(self, filename="recording.wav"):
        self.is_recording = False
        self.recording_thread.join()
        self.stream.stop_stream()
        self.stream.close()
        wf = wave.open(filename, 'wb')
        wf.setnchannels(self.channels)
        wf.setsampwidth(self.p.get_sample_size(self.sample_format))
        wf.setframerate(self.fs)
        wf.writeframes(b''.join(self.frames))
        wf.close()

# نافذة لتسجيل الجلسة
class SessionRecorder:
    def __init__(self, root):
        self.screen_recorder = ScreenRecorder()
        self.audio_recorder = AudioRecorder()
        self.session_window = tk.Toplevel(root)
        self.session_window.title("تسجيل الجلسة")
        self.start_button = tk.Button(self.session_window, text="بدء التسجيل", command=self.start_recording)
        self.start_button.pack()
        self.stop_button = tk.Button(self.session_window, text="انهاء التسجيل", command=self.stop_recording)
        self.stop_button.pack()

    def start_recording(self):
        self.screen_recorder.start_recording()
        self.audio_recorder.start_recording()

    def stop_recording(self):
        self.screen_recorder.stop_recording()
        self.audio_recorder.stop_recording()

# سبورة بيضاء للرسم
class Whiteboard:
    def __init__(self, root):
        self.whiteboard_window = tk.Toplevel(root)
        self.whiteboard_window.title("سبورة")
        self.canvas = tk.Canvas(self.whiteboard_window, bg='white', width=800, height=600)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.setup()
        self.canvas.bind("<B1-Motion>", self.paint)
        self.canvas.bind("<ButtonRelease-1>", self.reset)
        self.old_x, self.old_y = None, None
        self.color = 'black'
        self.line_width = 5
        self.actions = []  # قائمة لتخزين الإجراءات
        self.redo_stack = []  # قائمة لتخزين إجراءات الإعادة

    def setup(self):
        self.old_x = None
        self.old_y = None
        self.line_width = 5
        self.color = 'black'
        self.eraser_on = False

    def use_eraser(self):
        self.color = 'white'

    def choose_color(self):
        self.color = colorchooser.askcolor(color=self.color)[1]

    def change_line_width(self, event):
        self.line_width = int(event)

    def paint(self, event):
        if self.old_x and self.old_y:
            line = self.canvas.create_line(self.old_x, self.old_y, event.x, event.y,
                                    width=self.line_width, fill=self.color,
                                    capstyle=tk.ROUND, smooth=tk.TRUE, splinesteps=36)
            self.actions.append(line)  # تخزين الإجراء
            self.redo_stack = []  # مسح قائمة الإعادة عند الرسم الجديد
        self.old_x = event.x
        self.old_y = event.y

    def reset(self, event):
        self.old_x, self.old_y = None, None

    def paint_with_coords(self, x, y):
        if self.old_x and self.old_y:
            line = self.canvas.create_line(self.old_x, self.old_y, x, y,
                                    width=self.line_width, fill=self.color,
                                    capstyle=tk.ROUND, smooth=tk.TRUE, splinesteps=36)
            self.actions.append(line)  # تخزين الإجراء
            self.redo_stack = []  # مسح قائمة الإعادة عند الرسم الجديد
        self.old_x = x
        self.old_y = y

    def clear(self):
        self.canvas.delete("all")
        self.actions = []  # مسح جميع الإجراءات
        self.redo_stack = []  # مسح قائمة الإعادة

    def save(self):
        self.canvas.postscript(file="drawing.png", colormode='color')

    def undo(self):
        if self.actions:
            last_action = self.actions.pop()
            self.canvas.delete(last_action)
            self.redo_stack.append(last_action)  # تخزين الإجراء في قائمة الإعادة

    def redo(self):
        if self.redo_stack:
            last_action = self.redo_stack.pop()
            self.actions.append(last_action)
            # لاستعادة العنصر، يجب إعادة رسمه باستخدام البيانات المخزنة
            coords = self.canvas.coords(last_action)
            self.canvas.create_line(coords, width=self.line_width, fill=self.color, capstyle=tk.ROUND, smooth=tk.TRUE, splinesteps=36)

# نافذة لوحة التحكم
class ControlPanel:
    def __init__(self, root):
        self.control_window = tk.Toplevel(root)
        self.control_window.title("لوحة التحكم")

        self.whiteboard_button = tk.Button(self.control_window, text="سبورة", command=self.open_whiteboard)
        self.whiteboard_button.pack()

        self.save_button = tk.Button(self.control_window, text="حفظ", command=self.save_whiteboard)
        self.save_button.pack()

        self.color_button = tk.Button(self.control_window, text="اختر لون النص", command=self.choose_color)
        self.color_button.pack()

        self.erase_button = tk.Button(self.control_window, text="حذف", command=self.erase_text)
        self.erase_button.pack()

        self.clear_button = tk.Button(self.control_window, text="مسح السبورة", command=self.clear_whiteboard)
        self.clear_button.pack()

        self.undo_button = tk.Button(self.control_window, text="ارجاع للخلف", command=self.undo)
        self.undo_button.pack()

        self.redo_button = tk.Button(self.control_window, text="اعادة للامام", command=self.redo)
        self.redo_button.pack()



        self.line_width_scale = tk.Scale(self.control_window, from_=1, to=100, orient=tk.HORIZONTAL, label="سمك الخط", command=self.change_line_width)
        self.line_width_scale.pack()

        self.place_to_write = ttk.Combobox(self.control_window, values=["الكاميرا", "السبورة"])
        self.place_to_write.set("اختر مكان للكتابة")
        self.place_to_write.pack()

        self.whiteboard = None

    def open_whiteboard(self):
        self.whiteboard = Whiteboard(self.control_window)

    def save_whiteboard(self):
        if self.whiteboard:
            self.whiteboard.save()

    def choose_color(self):
        if self.whiteboard:
            self.whiteboard.choose_color()

    def erase_text(self):
        if self.whiteboard:
            self.whiteboard.use_eraser()

    def clear_whiteboard(self):
        if self.whiteboard:
            self.whiteboard.clear()

    def change_line_width(self, event):
        if self.whiteboard:
            self.whiteboard.change_line_width(int(event))

    def undo(self):
        if self.whiteboard:
            self.whiteboard.undo()

    def redo(self):
        if self.whiteboard:
            self.whiteboard.redo()



# إنشاء النافذة الرئيسية
root = tk.Tk()
root.title("Webcam Application")



# إنشاء لوحة التحكم
control_panel = ControlPanel(root)

# إنشاء كاميرا ويب
webcam = Webcam(root, control_panel)

# إنشاء نافذة تسجيل الجلسة
session_recorder = SessionRecorder(root)

root.mainloop()
