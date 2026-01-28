import sys, os, torch
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLineEdit, QPushButton, QLabel, QScrollArea, 
                             QTableWidget, QTableWidgetItem, QHeaderView, QFrame, 
                             QFileDialog, QStatusBar, QGridLayout)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap

from engine.ai_worker import AIWorker
from ui.widgets import ResultCard

class SmartDropZone(QFrame):
    filesDropped = Signal(list)
    cleared = Signal()

    def __init__(self, title="Drop Files", color="#3d94ff", multi=False):
        super().__init__()
        self.setAcceptDrops(True)
        self.setMinimumHeight(120)
        self.color, self.title, self.multi = color, title, multi
        self.all_paths = [] 
        
        self.layout = QVBoxLayout(self)
        self.label = QLabel(f"{self.title}\n(or click)")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setScaledContents(True)
        self.label.setStyleSheet("color: #888; font-size: 11px; border: none; background: transparent;")
        self.layout.addWidget(self.label)

        self.btn_x = QPushButton("✕", self)
        self.btn_x.setFixedSize(20, 20)
        self.btn_x.setStyleSheet("background: #550000; color: white; border-radius: 10px; font-weight: bold; border: none;")
        self.btn_x.hide()
        self.btn_x.clicked.connect(self.clear)

        self.update_style("#444")

    def resizeEvent(self, event):
        self.btn_x.move(self.width() - 25, 5)
        super().resizeEvent(event)

    def update_style(self, border_color):
        self.setStyleSheet(f"QFrame {{ border: 2px dashed {border_color}; border-radius: 8px; background-color: #1a1a1a; }}")

    def trigger_browse(self, is_folder=False):
        if is_folder:
            path = QFileDialog.getExistingDirectory(self, "Select Folder")
            files = [path] if path else []
        elif self.multi:
            files, _ = QFileDialog.getOpenFileNames(self, "Select Media", "", "Media (*.png *.jpg *.mp4 *.avi)")
        else:
            file, _ = QFileDialog.getOpenFileName(self, "Select Image", "", "Images (*.png *.jpg *.jpeg)")
            files = [file] if file else []
        if files: self.add_paths(files)

    def add_paths(self, new_paths):
        if not self.multi:
            self.all_paths = [new_paths[0]]
            pixmap = QPixmap(new_paths[0])
            if not pixmap.isNull():
                self.label.setPixmap(pixmap.scaled(280, 100, Qt.AspectRatioMode.KeepAspectRatio))
                self.label.setText("")
                self.btn_x.show()
        else:
            for p in new_paths:
                if p not in self.all_paths: self.all_paths.append(p)
        self.filesDropped.emit(self.all_paths)

    def clear(self):
        self.all_paths = []
        self.label.setPixmap(QPixmap())
        self.label.setText(f"{self.title}\n(or click)")
        self.btn_x.hide()
        self.cleared.emit()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and not self.all_paths: self.trigger_browse()
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls(): self.update_style(self.color); event.accept()
    def dragLeaveEvent(self, event): self.update_style("#444")
    def dropEvent(self, event):
        self.update_style("#444")
        urls = event.mimeData().urls()
        if urls: self.add_paths([u.toLocalFile() for u in urls])

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AI Search Engine (Full v1.0)")
        self.resize(1300, 900)
        self.setStatusBar(QStatusBar())
        self.setup_ui()
        self.setStyleSheet("""
            QMainWindow, QWidget { background-color: #0f0f0f; color: #e0e0e0; font-family: 'Segoe UI'; }
            QLineEdit { background-color: #1a1a1a; border: 1px solid #333; padding: 10px; color: #3d94ff; font-weight: bold; }
            QPushButton { background-color: #252525; border: 1px solid #333; padding: 8px; color: white; border-radius: 4px; }
            QTableWidget { background-color: #151515; border: 1px solid #333; color: #aaa; selection-background-color: #333; }
        """)

    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)

        # --- SIDEBAR ---
        sidebar = QFrame()
        sidebar.setFixedWidth(320)
        sidebar.setStyleSheet("background-color: #151515; border-right: 1px solid #222;")
        side_layout = QVBoxLayout(sidebar)

        side_layout.addWidget(QLabel("<b style='color:#3d94ff'>1. AI PROMPT & IMAGE</b>"))
        self.query_text = QLineEdit()
        self.query_text.setPlaceholderText("AI description appears here...")
        side_layout.addWidget(self.query_text)
        self.query_drop = SmartDropZone("Query Image", "#3d94ff", False)
        side_layout.addWidget(self.query_drop)
        
        side_layout.addSpacing(20)

        side_layout.addWidget(QLabel("<b style='color:#00c853'>2. TARGET DATA</b>"))
        self.target_drop = SmartDropZone("Target Media Queue", "#00c853", True)
        side_layout.addWidget(self.target_drop)
        
        t_btns = QHBoxLayout()
        self.btn_f = QPushButton("📄 + Files")
        self.btn_d = QPushButton("📁 + Folder")
        t_btns.addWidget(self.btn_f)
        t_btns.addWidget(self.btn_d)
        side_layout.addLayout(t_btns)
        
        self.btn_clear_all = QPushButton("🗑 Clear All Targets")
        side_layout.addWidget(self.btn_clear_all)

        side_layout.addStretch()

        self.scan_btn = QPushButton("🚀 RUN GLOBAL AI SEARCH")
        self.scan_btn.setStyleSheet("background-color: #005fb8; height: 50px; font-weight: bold;")
        side_layout.addWidget(self.scan_btn)

        # --- MAIN AREA ---
        content = QWidget()
        self.content_layout = QVBoxLayout(content)
        
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Filename", "Type", "Size"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.content_layout.addWidget(self.table)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.gallery_widget = QWidget()
        self.gallery_layout = QGridLayout(self.gallery_widget)
        self.scroll.setWidget(self.gallery_widget)
        self.scroll.hide()
        self.content_layout.addWidget(self.scroll)

        layout.addWidget(sidebar)
        layout.addWidget(content)

        # --- CONNECTIONS ---
        self.btn_f.clicked.connect(lambda: self.target_drop.trigger_browse(False))
        self.btn_d.clicked.connect(lambda: self.target_drop.trigger_browse(True))
        self.btn_clear_all.clicked.connect(self.clear_table)
        self.target_drop.filesDropped.connect(self.update_table)
        self.query_drop.filesDropped.connect(self.run_instant_caption)
        self.query_drop.cleared.connect(lambda: self.query_text.clear())
        self.scan_btn.clicked.connect(self.start_full_scan)

    def update_table(self, paths):
        self.table.setRowCount(0)
        self.table.show(); self.scroll.hide()
        files = self.flatten(paths)
        for p in files:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(os.path.basename(p)))
            self.table.setItem(row, 1, QTableWidgetItem(os.path.splitext(p)[1].upper()))
            self.table.setItem(row, 2, QTableWidgetItem(f"{os.path.getsize(p)/(1024*1024):.1f} MB"))

    def flatten(self, paths):
        out = []
        for p in paths:
            if os.path.isfile(p): out.append(p)
            elif os.path.isdir(p):
                for f in os.listdir(p):
                    if f.lower().endswith(('.png', '.jpg', '.jpeg', '.mp4', '.avi')):
                        out.append(os.path.join(p, f))
        return out

    def clear_table(self):
        self.target_drop.clear()
        self.table.setRowCount(0)

    def run_instant_caption(self, paths):
        if not paths: return
        self.statusBar().showMessage("AI interpreting query image...")
        self.worker = AIWorker("", paths[0], [])
        self.worker.progress_update.connect(lambda p, m: self.query_text.setText(m) if p == 100 else None)
        self.worker.start()

    def start_full_scan(self):
        prompt = self.query_text.text()
        targets = self.flatten(self.target_drop.all_paths)
        if not prompt or not targets:
            self.statusBar().showMessage("Error: No prompt or targets selected!")
            return
        
        # Clear old gallery results
        while self.gallery_layout.count():
            item = self.gallery_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
            
        self.scan_worker = AIWorker(prompt, None, targets)
        
        # FIX: Only hide the table when the FIRST result actually arrives
        def on_result(data):
            if not self.scroll.isVisible():
                self.table.hide()
                self.scroll.show()
            self.add_card(data)

        self.scan_worker.result_found.connect(on_result)
        self.scan_worker.progress_update.connect(lambda p, m: self.statusBar().showMessage(f"Scanning: {p}% - {m}"))
        self.scan_worker.finished.connect(lambda: self.statusBar().showMessage("Search Complete."))
        self.scan_worker.start()

    def add_card(self, data):
        # FIX: Pass raw data['score'] so ResultCard can format it itself
        card = ResultCard(data['path'], data['score'], data['caption'], data.get('timestamp'))
        cnt = self.gallery_layout.count()
        self.gallery_layout.addWidget(card, cnt // 4, cnt % 4)