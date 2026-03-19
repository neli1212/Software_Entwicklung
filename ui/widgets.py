import cv2
import os
from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel, QHBoxLayout, QFileDialog, QSizePolicy
from PySide6.QtGui import QPixmap, QImage, QColor, QDragEnterEvent, QDropEvent
from PySide6.QtCore import Qt, Signal

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

class SmartDropZone(QFrame):
    filesDropped = Signal(list)
    cleared = Signal()

    def __init__(self, text, color, multi):
        super().__init__()
        self.setAcceptDrops(True)
        self.setMinimumHeight(120)
        self.multi = multi
        self.base_color = color
        self.is_dark = True
        self.all_paths = []

        layout = QVBoxLayout(self)
        self.lbl_text = QLabel(text)
        self.lbl_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_text)

        self.update_theme(self.is_dark)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.accept()
            self.setStyleSheet(f"QFrame {{ border: 2px dashed {self.base_color}; background-color: rgba(61, 148, 255, 0.2); border-radius: 10px; }}")
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self.update_theme(self.is_dark)

    def dropEvent(self, event: QDropEvent):
        paths = [url.toLocalFile() for url in event.mimeData().urls()]
        self.add_paths(paths)
        self.update_theme(self.is_dark)

    def trigger_browse(self, is_folder):
        if is_folder:
            folder = QFileDialog.getExistingDirectory(self, "Select Folder")
            if folder:
                paths = []
                for root, dirs, files in os.walk(folder):
                    for f in files:
                        paths.append(os.path.join(root, f))
                self.add_paths(paths)
        else:
            files, _ = QFileDialog.getOpenFileNames(self, "Select Files")
            if files:
                self.add_paths(files)

    def add_paths(self, new_paths):
        """Fügt neue Pfade hinzu und blockiert Duplikate strikt."""
        added_count = 0
        
        if not hasattr(self, 'all_paths'):
            self.all_paths = []

        for path in new_paths:
            norm_path = os.path.normpath(path)
            if norm_path not in self.all_paths:
                self.all_paths.append(norm_path)
                added_count += 1

        if self.all_paths:
            if self.multi:
                self.lbl_text.setText(f"{len(self.all_paths)} unique files loaded")
            else:
                self.lbl_text.setText(os.path.basename(self.all_paths[-1]))
        
        if added_count > 0:
            self.filesDropped.emit(self.all_paths)

    def clear(self):
        self.all_paths.clear()
        self.lbl_text.setText("Cleared")
        self.cleared.emit()

    def update_theme(self, is_dark):
        self.is_dark = is_dark
        bg = "#1e1e1e" if is_dark else "#f0f0f0"
        border = "#444" if is_dark else "#ccc"
        text_color = "white" if is_dark else "black"
        self.setStyleSheet(f"QFrame {{ border: 2px dashed {border}; background-color: {bg}; border-radius: 10px; }}")
        self.lbl_text.setStyleSheet(f"color: {text_color}; font-weight: bold;")


class UniversalCard(QFrame):
    def __init__(self, path):
        super().__init__()
        self.path = path
        
        # --- WINDOWS FIX: DYNAMISCHE MINDESTGRÖSSE ---
        self.setMinimumWidth(240)
        self.setMinimumHeight(320)
        self.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Fixed)
        
        self.is_dark = True
        self.score = 0.0
        self.is_hit = False
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5,5,5,5)
        
        self.thumb = QLabel()
        self.thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumb.setMinimumSize(225, 150)
        self.thumb.setScaledContents(True)
        
        pix = get_thumbnail(path)
        if not pix.isNull():
            self.thumb.setPixmap(pix.scaled(225, 150, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        else:
            self.thumb.setText("NO PREVIEW")
            self.thumb.setStyleSheet("color: #555; font-weight: bold;")
        layout.addWidget(self.thumb)

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

        self.apply_style()

    def set_processing(self):
        """Show yellow/blue border while scanning"""
        color = "#3d94ff" if self.is_dark else "#005fb8"
        bg = "#2a2a2a" if self.is_dark else "#e3f2fd"
        self.setStyleSheet(f"QFrame {{ background-color: {bg}; border: 2px solid {color}; border-radius: 8px; }}")
        self.status_lbl.setText("Scanning...")
        self.status_lbl.setStyleSheet(f"color: {color}; font-weight: bold; border: none;")

    def set_result(self, data):
        """Update data and decide if it's a HIT"""
        self.score = float(data['score'])
        
        self.is_hit = self.score > 0.60
        
        timestamp = data.get('timestamp', "")
        score_text = f"Score: {self.score:.1%}"
        if timestamp: score_text += f" • Time: {timestamp}"
        
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
        if self.is_dark:
            bg_idle = "#222"
            bg_hit = "#1b3320" 
            border_idle = "#333"
            border_hit = "#00c853"
            text_main = "white"
            text_sub = "#aaa"
            text_hit = "#00e676"
        else: 
            bg_idle = "#ffffff"
            bg_hit = "#e8f5e9" 
            border_idle = "#cccccc"
            border_hit = "#2e7d32"
            text_main = "#000000"
            text_sub = "#555"
            text_hit = "#1b5e20"

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