from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel, QHBoxLayout
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt

class ResultCard(QFrame):
    def __init__(self, image_path, score, caption, timestamp=None):
        super().__init__()
        self.setFixedWidth(260); self.setFixedHeight(340)
        self.setStyleSheet("QFrame { background-color: #1a1a1a; border: 1px solid #333; border-radius: 10px; } QFrame:hover { border-color: #3d94ff; }")
        layout = QVBoxLayout(self)
        self.thumbnail = QLabel(); self.thumbnail.setFixedSize(240, 180); self.thumbnail.setScaledContents(True)
        pix = QPixmap(image_path)
        if not pix.isNull(): self.thumbnail.setPixmap(pix.scaled(240, 180, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation))
        layout.addWidget(self.thumbnail, alignment=Qt.AlignmentFlag.AlignCenter)
        meta_layout = QHBoxLayout()
        # FIX: Convert score to float before formatting to fix the % crash
        try: s_val = float(score)
        except: s_val = 0.0
        score_label = QLabel(f"🎯 {s_val:.1%}")
        score_label.setStyleSheet("color: #00c853; font-weight: bold; border: none;")
        meta_layout.addWidget(score_label)
        if timestamp:
            time_label = QLabel(f"🕒 {timestamp}"); time_label.setStyleSheet("color: #aaa; border: none;"); meta_layout.addWidget(time_label)
        layout.addLayout(meta_layout)
        caption_label = QLabel(caption); caption_label.setWordWrap(True); caption_label.setStyleSheet("color: #eee; font-style: italic; border: none;"); layout.addWidget(caption_label)
        layout.addStretch()