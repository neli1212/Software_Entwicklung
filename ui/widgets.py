import cv2
import os
from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel, QHBoxLayout, QFileDialog, QSizePolicy, QPushButton
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

    def __init__(self, title="Drop Files", color="#3d94ff", multi=False):
        super().__init__()
        self.setAcceptDrops(True)
        self.setMinimumHeight(120)
        self.color, self.title, self.multi = color, title, multi
        self.all_paths = [] 
        self.is_dark = True
        
        self.layout = QVBoxLayout(self)
        self.label = QLabel(f"{self.title}\n(or click)")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet("border: none; background: transparent;")
        self.layout.addWidget(self.label)

        self.btn_x = QPushButton("✕", self)
        self.btn_x.setFixedSize(20, 20)
        self.btn_x.setStyleSheet("background: #d32f2f; color: white; border-radius: 10px; font-weight: bold; border: none;")
        self.btn_x.hide()
        self.btn_x.clicked.connect(self.clear)
        self.update_style()

    def update_theme(self, is_dark):
        self.is_dark = is_dark
        self.update_style()

    def update_style(self, highlight=False):
        if highlight:
            border_col = self.color
            bg_col = "#2a2a2a" if self.is_dark else "#e3f2fd"
        else:
            border_col = "#444" if self.is_dark else "#ccc"
            bg_col = "#1a1a1a" if self.is_dark else "#ffffff"
        
        text_col = "#888" if self.is_dark else "#555"
        
        self.setStyleSheet(f"QFrame {{ border: 2px dashed {border_col}; border-radius: 8px; background-color: {bg_col}; }}")
        self.label.setStyleSheet(f"color: {text_col}; font-size: 11px; border: none; background: transparent;")

    def resizeEvent(self, event):
        self.btn_x.move(self.width() - 25, 5)
        super().resizeEvent(event)

    def trigger_browse(self, is_folder=False):
        if is_folder:
            path = QFileDialog.getExistingDirectory(self, "Select Folder")
            files = [path] if path else []
        elif self.multi:
            files, _ = QFileDialog.getOpenFileNames(self, "Select Media", "", "Media (*.png *.jpg *.jpeg *.mp4 *.avi *.mov *.mkv)")
        else:
            file, _ = QFileDialog.getOpenFileName(self, "Select Image", "", "Images (*.png *.jpg *.jpeg)")
            files = [file] if file else []
        if files: self.add_paths(files)

    def add_paths(self, new_paths):
        if not self.multi:
            self.all_paths = [new_paths[0]]
            pixmap = QPixmap(new_paths[0])
            if not pixmap.isNull():
                self.label.setPixmap(pixmap.scaled(self.width()-20, self.height()-20, Qt.AspectRatioMode.KeepAspectRatio))
                self.label.setText("")
                self.btn_x.show()
        else:
            for p in new_paths:
                if p not in self.all_paths: self.all_paths.append(p)
            self.label.setText(f"{len(self.all_paths)} files queued")
            self.btn_x.show()
        self.filesDropped.emit(self.all_paths)

    def clear(self):
        self.all_paths = []
        self.label.setPixmap(QPixmap())
        self.label.setText(f"{self.title}\n(or click)")
        self.btn_x.hide()
        self.cleared.emit()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton: self.trigger_browse()
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls(): self.update_style(True); event.accept()
    def dragLeaveEvent(self, event): self.update_style(False)
    def dropEvent(self, event):
        self.update_style(False)
        urls = event.mimeData().urls()
        if urls: self.add_paths([u.toLocalFile() for u in urls])


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