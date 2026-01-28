import cv2
import os
from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel, QHBoxLayout
from PySide6.QtGui import QPixmap, QImage, QColor
from PySide6.QtCore import Qt

def get_thumbnail(path):
    pix = QPixmap()
    try:
        if path.lower().endswith(('.mp4', '.avi', '.mov', '.mkv')):
            cap = cv2.VideoCapture(path)
            ret, frame = cap.read()
            cap.release()
            if ret:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = frame.shape
                qimg = QImage(frame.data, w, h, ch * w, QImage.Format.Format_RGB888)
                pix = QPixmap.fromImage(qimg)
        else:
            pix = QPixmap(path)
    except: pass
    return pix

class UniversalCard(QFrame):
    def __init__(self, path):
        super().__init__()
        self.path = path
        self.setFixedWidth(240); self.setFixedHeight(320)
        
        # State tracking
        self.is_dark = True
        self.score = 0.0
        self.is_hit = False
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5,5,5,5)
        
        # Thumbnail
        self.thumb = QLabel()
        self.thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumb.setFixedSize(225, 150)
        self.thumb.setScaledContents(True)
        
        pix = get_thumbnail(path)
        if not pix.isNull():
            self.thumb.setPixmap(pix.scaled(225, 150, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        else:
            self.thumb.setText("NO PREVIEW")
            self.thumb.setStyleSheet("color: #555; font-weight: bold;")
        layout.addWidget(self.thumb)

        # Meta Data
        self.meta_layout = QVBoxLayout()
        self.name_lbl = QLabel(os.path.basename(path))
        self.name_lbl.setWordWrap(False)
        self.meta_layout.addWidget(self.name_lbl)
        
        self.status_lbl = QLabel("Waiting...")
        self.meta_layout.addWidget(self.status_lbl)
        
        self.caption_lbl = QLabel("")
        self.caption_lbl.setWordWrap(True)
        self.caption_lbl.hide()
        self.meta_layout.addWidget(self.caption_lbl)
        
        layout.addLayout(self.meta_layout)
        layout.addStretch()

        # Apply initial style
        self.apply_style()

    def set_processing(self):
        """Show yellow/blue border while scanning"""
        color = "#3d94ff" if self.is_dark else "#005fb8"
        bg = "#2a2a2a" if self.is_dark else "#e3f2fd"
        self.setStyleSheet(f"QFrame {{ background-color: {bg}; border: 2px solid {color}; border-radius: 8px; }}")
        self.status_lbl.setText("🤖 Scanning...")
        self.status_lbl.setStyleSheet(f"color: {color}; font-weight: bold; border: none;")

    def set_result(self, data):
        """Update data and decide if it's a HIT"""
        self.score = float(data['score'])
        
        # DEFINITION OF A HIT: > 60%
        self.is_hit = self.score > 0.60
        
        timestamp = data.get('timestamp', "")
        score_text = f"🎯 {self.score:.1%}"
        if timestamp: score_text += f" • 🕒 {timestamp}"
        
        self.status_lbl.setText(score_text)
        self.caption_lbl.setText(f"\"{data['caption']}\"")
        self.caption_lbl.show()
        
        self.apply_style()

    def update_theme(self, is_dark_mode):
        """Called by MainWindow when toggling theme"""
        self.is_dark = is_dark_mode
        self.apply_style()

    def apply_style(self):
        """
        Decides the Look based on:
        1. Theme (Dark/Light)
        2. Status (Hit/Miss/Idle)
        """
        # 1. Colors Setup
        if self.is_dark:
            bg_idle = "#222"
            bg_hit = "#1b3320" # Dark Greenish
            border_idle = "#333"
            border_hit = "#00c853"
            text_main = "white"
            text_sub = "#aaa"
            text_hit = "#00e676"
        else: # Light Mode
            bg_idle = "#ffffff"
            bg_hit = "#e8f5e9" # Light Greenish
            border_idle = "#cccccc"
            border_hit = "#2e7d32"
            text_main = "#000000"
            text_sub = "#555"
            text_hit = "#1b5e20"

        # 2. Logic
        if self.is_hit:
            style = f"QFrame {{ background-color: {bg_hit}; border: 3px solid {border_hit}; border-radius: 8px; }}"
            status_color = text_hit
        else:
            style = f"QFrame {{ background-color: {bg_idle}; border: 1px solid {border_idle}; border-radius: 8px; }}"
            status_color = text_sub

        self.setStyleSheet(style)
        self.name_lbl.setStyleSheet(f"border: none; color: {text_main}; font-weight: bold;")
        self.status_lbl.setStyleSheet(f"border: none; color: {status_color}; font-size: 11px;")
        self.caption_lbl.setStyleSheet(f"border: none; color: {text_sub}; font-style: italic; font-size: 11px;")