import sys, os
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLineEdit, QPushButton, QLabel, QScrollArea, 
                             QTableWidget, QTableWidgetItem, QHeaderView, QFrame, 
                             QFileDialog, QStatusBar, QGridLayout, QMessageBox, 
                             QStackedWidget, QSpinBox, QDoubleSpinBox, QComboBox, QProgressBar)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap, QColor

from engine.ai_worker import AIWorker, ModelLoader
from ui.widgets import UniversalCard
from engine.processor import collect_all_media

# --- STYLESHEETS ---
DARK_THEME = """
    QMainWindow, QWidget { background-color: #0f0f0f; color: #e0e0e0; font-family: 'Segoe UI'; }
    QLineEdit { background-color: #1a1a1a; border: 1px solid #333; padding: 10px; color: #3d94ff; font-weight: bold; }
    QPushButton { background-color: #252525; border: 1px solid #333; padding: 8px; color: white; border-radius: 4px; }
    QPushButton:hover { background-color: #333; }
    QTableWidget { background-color: #151515; border: 1px solid #333; color: #aaa; selection-background-color: #333; gridline-color: #222; }
    QHeaderView::section { background-color: #222; border: 1px solid #333; padding: 4px; color: #eee; }
    QSpinBox, QDoubleSpinBox, QComboBox { background-color: #1a1a1a; border: 1px solid #444; padding: 5px; color: white; }
    QComboBox::drop-down { border: none; }
    QLabel { color: #e0e0e0; }
    QProgressBar { border: 2px solid #333; border-radius: 5px; text-align: center; }
    QProgressBar::chunk { background-color: #3d94ff; width: 20px; }
"""

LIGHT_THEME = """
    QMainWindow, QWidget { background-color: #f5f5f5; color: #111111; font-family: 'Segoe UI'; }
    QLineEdit { background-color: #ffffff; border: 1px solid #cccccc; padding: 10px; color: #005fb8; font-weight: bold; }
    QPushButton { background-color: #ffffff; border: 1px solid #cccccc; padding: 8px; color: #333; border-radius: 4px; }
    QPushButton:hover { background-color: #e6e6e6; }
    QTableWidget { background-color: #ffffff; border: 1px solid #ddd; color: #333; selection-background-color: #d0e4f5; selection-color: #000; gridline-color: #eee; }
    QHeaderView::section { background-color: #e0e0e0; border: 1px solid #ccc; padding: 4px; color: #000; }
    QSpinBox, QDoubleSpinBox, QComboBox { background-color: #ffffff; border: 1px solid #ccc; padding: 5px; color: #000; }
    QComboBox::drop-down { border: none; }
    QLabel { color: #111111; }
    QProgressBar { border: 2px solid #ccc; border-radius: 5px; text-align: center; }
    QProgressBar::chunk { background-color: #005fb8; width: 20px; }
"""

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

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AI Search Engine (Final v2.1)")
        self.resize(1300, 950)
        self.setStatusBar(QStatusBar())
        self.view_mode = "LIST"
        self.file_map = {} 
        self.is_dark_mode = True 
        
        self._active_threads = []
        self.models_loaded = False
        
        self.setup_ui()
        self.setStyleSheet(DARK_THEME)

    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)

        # --- SIDEBAR ---
        self.sidebar = QFrame()
        self.sidebar.setFixedWidth(320)
        self.sidebar.setStyleSheet("background-color: #151515; border-right: 1px solid #222;")
        side_layout = QVBoxLayout(self.sidebar)

        # 1. Query
        side_layout.addWidget(QLabel("<b style='color:#3d94ff'>1. AI PROMPT & IMAGE</b>"))
        self.query_text = QLineEdit()
        self.query_text.setPlaceholderText("Describe object (e.g. 'Gray Cat')...")
        side_layout.addWidget(self.query_text)
        
        self.query_drop = SmartDropZone("Query Image", "#3d94ff", False)
        side_layout.addWidget(self.query_drop)

        q_btns = QHBoxLayout()
        self.btn_q_file = QPushButton("📄 + Image")
        self.btn_q_clear = QPushButton("🗑 Clear")
        q_btns.addWidget(self.btn_q_file); q_btns.addWidget(self.btn_q_clear)
        side_layout.addLayout(q_btns)
        
        side_layout.addSpacing(15)

        # 2. Target
        side_layout.addWidget(QLabel("<b style='color:#00c853'>2. TARGET DATA</b>"))
        self.target_drop = SmartDropZone("Target Media Queue", "#00c853", True)
        side_layout.addWidget(self.target_drop)
        
        t_btns = QHBoxLayout()
        self.btn_f = QPushButton("📄 + Files")
        self.btn_d = QPushButton("📁 + Folder")
        t_btns.addWidget(self.btn_f); t_btns.addWidget(self.btn_d)
        side_layout.addLayout(t_btns)
        
        self.btn_clear_all = QPushButton("🗑 Clear All Targets")
        side_layout.addWidget(self.btn_clear_all)

        side_layout.addSpacing(15)

        # 3. AI Settings
        side_layout.addWidget(QLabel("<b style='color:#ff9800'>3. AI SETTINGS</b>"))
        
        side_layout.addWidget(QLabel("Comparison Logic:"))
        self.combo_mode = QComboBox()
        self.combo_mode.addItems(["Keyword Match (Precise)", "Vector Space (Abstract)"])
        self.combo_mode.currentIndexChanged.connect(self.on_mode_changed)
        side_layout.addWidget(self.combo_mode)
        
        side_layout.addSpacing(5)

        # Spinners
        b_layout = QHBoxLayout(); b_layout.addWidget(QLabel("Beam Size (1-10):"))
        self.spin_beams = QSpinBox(); self.spin_beams.setRange(1, 10); self.spin_beams.setValue(5)
        b_layout.addWidget(self.spin_beams); side_layout.addLayout(b_layout)

        ml_layout = QHBoxLayout(); ml_layout.addWidget(QLabel("Min Len (5-100):"))
        self.spin_min_len = QSpinBox(); self.spin_min_len.setRange(5, 100); self.spin_min_len.setValue(20)
        ml_layout.addWidget(self.spin_min_len); side_layout.addLayout(ml_layout)

        lp_layout = QHBoxLayout(); lp_layout.addWidget(QLabel("Len Penalty (1-5):"))
        self.spin_len_pen = QDoubleSpinBox(); self.spin_len_pen.setRange(1.0, 5.0); self.spin_len_pen.setValue(3.0); self.spin_len_pen.setSingleStep(0.1)
        lp_layout.addWidget(self.spin_len_pen); side_layout.addLayout(lp_layout)

        rp_layout = QHBoxLayout(); rp_layout.addWidget(QLabel("No-Repeat (1-2):"))
        self.spin_rep_pen = QDoubleSpinBox(); self.spin_rep_pen.setRange(1.0, 2.0); self.spin_rep_pen.setValue(1.2); self.spin_rep_pen.setSingleStep(0.1)
        rp_layout.addWidget(self.spin_rep_pen); side_layout.addLayout(rp_layout)

        side_layout.addStretch()

        # --- MODEL LOADER PROGRESS BAR ---
        self.loading_label = QLabel("First Run: Downloading AI Models (~1GB)...")
        self.loading_label.setStyleSheet("color: #ff9800; font-weight: bold; font-size: 11px;")
        self.loading_label.hide()
        side_layout.addWidget(self.loading_label)

        self.progress_loading = QProgressBar()
        self.progress_loading.setRange(0, 0) 
        self.progress_loading.setTextVisible(False)
        self.progress_loading.hide()
        side_layout.addWidget(self.progress_loading)

        self.scan_btn = QPushButton("🚀 RUN GLOBAL AI SEARCH")
        self.scan_btn.setStyleSheet("background-color: #005fb8; height: 50px; font-weight: bold;")
        side_layout.addWidget(self.scan_btn)

        # --- MAIN DISPLAY ---
        content = QWidget()
        self.content_layout = QVBoxLayout(content)
        
        self.view_stack = QStackedWidget()
        self.main_table = QTableWidget(0, 5)
        self.main_table.setHorizontalHeaderLabels(["Filename", "Type", "Size", "Likelihood", "AI Prompt"])
        self.main_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.view_stack.addWidget(self.main_table)
        
        self.main_scroll = QScrollArea()
        self.main_scroll.setWidgetResizable(True)
        self.gallery_container = QWidget()
        self.gallery_layout = QGridLayout(self.gallery_container)
        self.main_scroll.setWidget(self.gallery_container)
        self.view_stack.addWidget(self.main_scroll)
        
        self.content_layout.addWidget(self.view_stack)

        # --- BOTTOM BAR ---
        bottom_bar = QHBoxLayout()
        self.lbl_status = QLabel("Ready.")
        bottom_bar.addWidget(self.lbl_status)
        bottom_bar.addStretch()
        
        self.btn_theme = QPushButton("🌗 Theme")
        self.btn_theme.setFixedWidth(100)
        self.btn_theme.clicked.connect(self.toggle_theme)
        bottom_bar.addWidget(self.btn_theme)

        self.btn_toggle_view = QPushButton("Switch View ☷/▦")
        self.btn_toggle_view.setFixedWidth(150)
        self.btn_toggle_view.clicked.connect(self.toggle_view)
        bottom_bar.addWidget(self.btn_toggle_view)
        
        self.content_layout.addLayout(bottom_bar)
        layout.addWidget(self.sidebar)
        layout.addWidget(content)

        # --- CONNECTIONS ---
        self.btn_q_file.clicked.connect(lambda: self.query_drop.trigger_browse(False))
        self.btn_q_clear.clicked.connect(self.query_drop.clear)
        self.query_drop.filesDropped.connect(self.run_instant_caption)
        self.query_drop.cleared.connect(lambda: self.query_text.clear())
        self.btn_f.clicked.connect(lambda: self.target_drop.trigger_browse(False))
        self.btn_d.clicked.connect(lambda: self.target_drop.trigger_browse(True))
        self.btn_clear_all.clicked.connect(self.target_drop.clear)
        self.target_drop.cleared.connect(self.wipe_data)
        self.target_drop.filesDropped.connect(self.add_files_to_view)
        self.scan_btn.clicked.connect(self.on_run_clicked)
        self.on_mode_changed()

    def on_run_clicked(self):
        if self.models_loaded:
            self.start_live_scan()
        else:
            self.scan_btn.setEnabled(False)
            self.scan_btn.setText("INITIALIZING AI...")
            self.loading_label.show()
            self.progress_loading.show()
            
            loader = ModelLoader()
            self._active_threads.append(loader) 
            loader.finished.connect(lambda: self.on_models_ready(loader))
            loader.start()

    def on_models_ready(self, loader):
        if loader in self._active_threads: self._active_threads.remove(loader)
        self.models_loaded = True
        self.loading_label.hide()
        self.progress_loading.hide()
        self.scan_btn.setEnabled(True)
        self.scan_btn.setText("🚀 RUN GLOBAL AI SEARCH")
        self.start_live_scan()

    def toggle_theme(self):
        self.is_dark_mode = not self.is_dark_mode
        if self.is_dark_mode:
            self.setStyleSheet(DARK_THEME)
            self.sidebar.setStyleSheet("background-color: #151515; border-right: 1px solid #222;")
            self.btn_toggle_view.setStyleSheet("background-color: #444; color: white; border: 1px solid #666;")
        else:
            self.setStyleSheet(LIGHT_THEME)
            self.sidebar.setStyleSheet("background-color: #f5f5f5; border-right: 1px solid #ccc;")
            self.btn_toggle_view.setStyleSheet("background-color: #ffffff; color: #333; border: 1px solid #ccc;")
        
        self.query_drop.update_theme(self.is_dark_mode)
        self.target_drop.update_theme(self.is_dark_mode)
        for widgets in self.file_map.values():
            widgets['card'].update_theme(self.is_dark_mode)

    def on_mode_changed(self):
        is_keyword_mode = (self.combo_mode.currentIndex() == 0)
        if is_keyword_mode:
            self.query_drop.setEnabled(False)
            self.query_drop.setToolTip("Image Input Disabled in Keyword Mode")
            self.query_drop.setStyleSheet("QFrame { border: 2px dashed #444; border-radius: 8px; background-color: #111; }")
            self.btn_q_file.setEnabled(False)
            self.query_text.setPlaceholderText("Enter precise keywords (e.g. 'Gray Cat')")
        else:
            self.query_drop.setEnabled(True)
            self.query_drop.setToolTip("")
            self.query_drop.update_theme(self.is_dark_mode)
            self.btn_q_file.setEnabled(True)
            self.query_text.setPlaceholderText("Describe vibe or use image...")

    def toggle_view(self):
        self.view_mode = "GALLERY" if self.view_mode == "LIST" else "LIST"
        if self.view_mode == "LIST": self.view_stack.setCurrentWidget(self.main_table)
        else: self.view_stack.setCurrentWidget(self.main_scroll)
        icon = "▦" if self.view_mode == "LIST" else "☷"
        self.btn_toggle_view.setText(f"Switch View {icon}")

    def wipe_data(self):
        self.main_table.setRowCount(0)
        while self.gallery_layout.count():
            item = self.gallery_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        self.file_map = {}

    def add_files_to_view(self, paths):
        files = collect_all_media(paths)
        new_files = [f for f in files if f not in self.file_map]
        self.target_drop.all_paths.extend(new_files)
        self.target_drop.label.setText(f"{len(self.target_drop.all_paths)} files queued")
        
        for p in new_files:
            row = self.main_table.rowCount()
            self.main_table.insertRow(row)
            self.main_table.setItem(row, 0, QTableWidgetItem(os.path.basename(p)))
            self.main_table.setItem(row, 1, QTableWidgetItem(os.path.splitext(p)[1].upper()))
            try: sz = f"{os.path.getsize(p)/(1024*1024):.1f} MB"
            except: sz = "0 MB"
            self.main_table.setItem(row, 2, QTableWidgetItem(sz))
            self.main_table.setItem(row, 3, QTableWidgetItem("-"))
            self.main_table.setItem(row, 4, QTableWidgetItem("-"))
            
            card = UniversalCard(p)
            card.update_theme(self.is_dark_mode)
            count = len(self.file_map)
            self.gallery_layout.addWidget(card, count // 4, count % 4)
            self.file_map[p] = {'row': row, 'card': card}

    def run_instant_caption(self, paths):
        if not paths: return
        self.statusBar().showMessage("AI interpreting query image...")
        settings = {'num_beams': 5, 'min_length': 20, 'length_penalty': 2.0, 'repetition_penalty': 1.2, 'mode': 'vector'}
        
        # FIX: Keep reference to the worker
        worker = AIWorker("", paths[0], [], settings)
        self._active_threads.append(worker)
        
        worker.progress_update.connect(lambda p, m: self.query_text.setText(m) if p == 100 else None)
        worker.finished.connect(lambda: self._active_threads.remove(worker) if worker in self._active_threads else None)
        worker.start()

    def start_live_scan(self):
        prompt = self.query_text.text()
        targets = [p for p in self.file_map.keys()]
        mode = "keyword" if self.combo_mode.currentIndex() == 0 else "vector"
        
        if mode == "keyword" and not prompt:
             QMessageBox.warning(self, "Error", "In Keyword Mode, you MUST enter text!")
             return
        if mode == "vector" and not prompt and not self.query_drop.all_paths:
             QMessageBox.warning(self, "Error", "Please enter a prompt or drop an image!")
             return
        if not targets:
             QMessageBox.warning(self, "Error", "No target files selected!")
             return
        
        for p, widgets in self.file_map.items():
            self.main_table.setItem(widgets['row'], 3, QTableWidgetItem("Waiting..."))
            self.main_table.setItem(widgets['row'], 4, QTableWidgetItem("-"))
            for c in range(5):
                self.main_table.item(widgets['row'], c).setBackground(QColor(0,0,0,0))

        settings = {
            'num_beams': self.spin_beams.value(),
            'min_length': self.spin_min_len.value(),
            'length_penalty': self.spin_len_pen.value(),
            'repetition_penalty': self.spin_rep_pen.value(),
            'mode': mode
        }

        scan_worker = AIWorker(prompt, self.query_drop.all_paths[0] if self.query_drop.all_paths else None, targets, settings)
        self._active_threads.append(scan_worker)
        
        scan_worker.result_found.connect(self.update_single_item)
        scan_worker.progress_update.connect(self.handle_progress)
        
        def on_complete():
            self.lbl_status.setText("Search Complete.")
            if scan_worker in self._active_threads: self._active_threads.remove(scan_worker)
            
        scan_worker.finished.connect(on_complete)
        scan_worker.start()

    def handle_progress(self, percent, message):
        self.lbl_status.setText(f"Scanning... {percent}% - {message}")
        for path, widgets in self.file_map.items():
            if os.path.basename(path) == message:
                widgets['card'].set_processing()
                color = QColor("#2a2a2a") if self.is_dark_mode else QColor("#e3f2fd")
                for c in range(5):
                    self.main_table.item(widgets['row'], c).setBackground(color)

    def update_single_item(self, data):
        path = data['path']
        if path in self.file_map:
            widgets = self.file_map[path]
            widgets['card'].set_result(data)
            
            score_val = f"{float(data['score']):.1%}"
            self.main_table.setItem(widgets['row'], 3, QTableWidgetItem(score_val))
            self.main_table.setItem(widgets['row'], 4, QTableWidgetItem(data['caption']))
            
            if float(data['score']) > 0.60:
                highlight_col = QColor("#1b3320") if self.is_dark_mode else QColor("#e8f5e9")
                text_col = QColor("#00e676") if self.is_dark_mode else QColor("#1b5e20")
                for c in range(5):
                    self.main_table.item(widgets['row'], c).setBackground(highlight_col)
                self.main_table.item(widgets['row'], 3).setForeground(text_col)
            else:
                for c in range(5):
                    self.main_table.item(widgets['row'], c).setBackground(QColor(0,0,0,0))
                default_text = QColor("#aaa") if self.is_dark_mode else QColor("#333")
                self.main_table.item(widgets['row'], 3).setForeground(default_text)