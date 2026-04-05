import sys, os

os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "0"
os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "0"

from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLineEdit, QPushButton, QLabel, QScrollArea, 
                             QTableWidget, QTableWidgetItem, QHeaderView, QFrame, 
                             QFileDialog, QStatusBar, QGridLayout, QMessageBox, 
                             QStackedWidget, QSpinBox, QDoubleSpinBox, QComboBox, QProgressBar)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap, QColor
from engine.ai_worker import AIWorker, ModelLoader, AVAILABLE_MODELS, check_model_downloaded, delete_local_model
from ui.widgets import UniversalCard, SmartDropZone
from engine.processor import collect_all_media
from PySide6.QtCore import QTimer

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

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AI Search Engine (Final)")
        self.resize(1300, 950)
        self.setStatusBar(QStatusBar())
        self.view_mode = "LIST"
        self.file_map = {} 
        self.is_dark_mode = True 
        
        self._active_threads = []
        self.models_loaded = False
        self.download_timer = QTimer(self)
        self.download_timer.timeout.connect(self.update_download_progress)
        
        self.setup_ui()
        self.refresh_model_ui() 
        self.setStyleSheet(DARK_THEME)

    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)

        self.sidebar_scroll = QScrollArea()
        self.sidebar_scroll.setMinimumWidth(300)
        self.sidebar_scroll.setMaximumWidth(420)
        self.sidebar_scroll.setWidgetResizable(True)
        self.sidebar_scroll.setStyleSheet("QScrollArea { border: none; border-right: 1px solid #222; background-color: #151515; }")
        
        self.sidebar = QWidget()
        self.sidebar.setStyleSheet("background-color: transparent;")
        side_layout = QVBoxLayout(self.sidebar)
        self.sidebar_scroll.setWidget(self.sidebar)

        # 1. Query
        side_layout.addWidget(QLabel("<b style='color:#3d94ff'>1. AI PROMPT & IMAGE</b>"))
        self.query_text = QLineEdit()
        self.query_text.setPlaceholderText("Describe object (e.g. 'Gray Cat')...")
        side_layout.addWidget(self.query_text)
        
        self.query_drop = SmartDropZone("Query Image", "#3d94ff", False)
        side_layout.addWidget(self.query_drop)

        q_btns = QHBoxLayout()
        self.btn_q_file = QPushButton("+ Image File")
        self.btn_q_clear = QPushButton("Clear Image")
        q_btns.addWidget(self.btn_q_file); q_btns.addWidget(self.btn_q_clear)
        side_layout.addLayout(q_btns)
        
        side_layout.addSpacing(15)

        # 2. Target
        side_layout.addWidget(QLabel("<b style='color:#00c853'>2. TARGET DATA</b>"))
        self.target_drop = SmartDropZone("Target Media Queue", "#00c853", True)
        side_layout.addWidget(self.target_drop)
        
        t_btns = QHBoxLayout()
        self.btn_f = QPushButton("+ Add Files")
        self.btn_d = QPushButton("+ Add Folder")
        t_btns.addWidget(self.btn_f); t_btns.addWidget(self.btn_d)
        side_layout.addLayout(t_btns)
        
        self.btn_clear_all = QPushButton("Clear All Targets")
        side_layout.addWidget(self.btn_clear_all)

        side_layout.addSpacing(15)

        # 3. AI Settings
        side_layout.addWidget(QLabel("<b style='color:#ff9800'>3. AI SETTINGS</b>"))
        
        side_layout.addWidget(QLabel("KI-Modell Version:"))
        self.combo_ai_model = QComboBox()
        self.combo_ai_model.currentIndexChanged.connect(self.on_model_selection_changed)
        side_layout.addWidget(self.combo_ai_model)
        
        self.btn_delete_model = QPushButton("Delete Selected Model")
        self.btn_delete_model.clicked.connect(self.delete_selected_model)
        side_layout.addWidget(self.btn_delete_model)
        side_layout.addSpacing(10)

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
        self.loading_label = QLabel("Ready to start.")
        self.loading_label.setStyleSheet("color: #ff9800; font-weight: bold; font-size: 11px;")
        self.loading_label.hide()
        side_layout.addWidget(self.loading_label)

        self.progress_loading = QProgressBar()
        self.progress_loading.setRange(0, 0) 
        self.progress_loading.setTextVisible(False)
        self.progress_loading.hide()
        side_layout.addWidget(self.progress_loading)

        self.scan_btn = QPushButton("RUN GLOBAL AI SEARCH")
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
        
        self.btn_theme = QPushButton("Toggle Theme")
        self.btn_theme.setFixedWidth(100)
        self.btn_theme.clicked.connect(self.toggle_theme)
        bottom_bar.addWidget(self.btn_theme)

        self.btn_toggle_view = QPushButton("Switch View (List/Grid)")
        self.btn_toggle_view.setFixedWidth(150)
        self.btn_toggle_view.clicked.connect(self.toggle_view)
        bottom_bar.addWidget(self.btn_toggle_view)
        
        self.content_layout.addLayout(bottom_bar)
        layout.addWidget(self.sidebar_scroll)
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

    def refresh_model_ui(self):
        current_index = self.combo_ai_model.currentIndex()
        self.combo_ai_model.blockSignals(True)
        self.combo_ai_model.clear()
        
        for key in AVAILABLE_MODELS.keys():
            is_downloaded = check_model_downloaded(key)
            display_text = f"{key} (Ready)" if is_downloaded else f"{key} (Needs Download)"
            self.combo_ai_model.addItem(display_text, userData=key)
            
        if 0 <= current_index < self.combo_ai_model.count():
            self.combo_ai_model.setCurrentIndex(current_index)
            
        self.combo_ai_model.blockSignals(False)
        self.on_model_selection_changed()

    def on_model_selection_changed(self):
        selected_key = self.combo_ai_model.currentData()
        self.models_loaded = False 
        self.scan_btn.setText("RUN GLOBAL AI SEARCH")
        
        if check_model_downloaded(selected_key):
            self.btn_delete_model.setEnabled(True)
            self.btn_delete_model.setStyleSheet("background-color: #d32f2f; color: white;")
        else:
            self.btn_delete_model.setEnabled(False)
            self.btn_delete_model.setStyleSheet("background-color: #444; color: #888;")

    def delete_selected_model(self):
        selected_key = self.combo_ai_model.currentData()
        reply = QMessageBox.question(self, 'Delete Model', 
                                     f'Are you sure you want to delete the files for "{selected_key}"?',
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
                                     QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            if delete_local_model(selected_key):
                QMessageBox.information(self, "Success", "Model deleted successfully.")
                self.models_loaded = False
            else:
                QMessageBox.warning(self, "Error", "Error deleting model. It might be in use.")
            self.refresh_model_ui()

    def get_dir_size(self, path):
        total_size = 0
        if os.path.exists(path):
            for dirpath, _, filenames in os.walk(path):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    if not os.path.islink(fp):
                        try:
                            total_size += os.path.getsize(fp)
                        except:
                            pass
        return total_size

    def update_download_progress(self):
        selected_key = self.combo_ai_model.currentData()
        if not selected_key:
            return
        folder_name = AVAILABLE_MODELS[selected_key]["folder"]
        path = os.path.join(os.getcwd(), "ai_models", folder_name)
        
        size_bytes = self.get_dir_size(path)
        size_mb = size_bytes / (1024 * 1024)
        self.loading_label.setText(f"Downloading Model")

    def on_run_clicked(self):
        selected_model_key = self.combo_ai_model.currentData()
        if self.models_loaded:
            self.start_live_scan()
        else:
            self.scan_btn.setEnabled(False)
            self.scan_btn.setText("INITIALIZING AI...")
            self.loading_label.setText("Starting Download...")
            self.loading_label.show()
            self.progress_loading.show()
            
            self.download_timer.start(500)
            
            loader = ModelLoader(selected_model_key)
            self._active_threads.append(loader) 
            loader.finished.connect(lambda: self.on_models_ready(loader))
            loader.start()

    def on_models_ready(self, loader):
        if loader in self._active_threads: self._active_threads.remove(loader)
        self.models_loaded = True
        self.download_timer.stop()
        self.loading_label.hide()
        self.progress_loading.hide()
        self.scan_btn.setEnabled(True)
        self.scan_btn.setText("RUN GLOBAL AI SEARCH")
        self.refresh_model_ui() 
        self.start_live_scan()

    def toggle_theme(self):
        self.is_dark_mode = not self.is_dark_mode
        if self.is_dark_mode:
            self.setStyleSheet(DARK_THEME)
            self.sidebar_scroll.setStyleSheet("QScrollArea { border: none; border-right: 1px solid #222; background-color: #151515; }")
            self.btn_toggle_view.setStyleSheet("background-color: #444; color: white; border: 1px solid #666;")
        else:
            self.setStyleSheet(LIGHT_THEME)
            self.sidebar_scroll.setStyleSheet("QScrollArea { border: none; border-right: 1px solid #ccc; background-color: #f5f5f5; }")
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
        self.btn_toggle_view.setText("Switch View")

    def wipe_data(self):
        self.main_table.setRowCount(0)
        while self.gallery_layout.count():
            item = self.gallery_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        self.file_map = {}

    def add_files_to_view(self, paths):
        files = collect_all_media(paths)
        new_files = [f for f in files if f not in self.file_map]
        
        self.target_drop.label.setText(f"{len(self.file_map) + len(new_files)} files queued")
        
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
            card.show()
            
        self.gallery_container.adjustSize()
        self.main_scroll.widget().updateGeometry()

    def run_instant_caption(self, paths):
        if not paths: return
        self.statusBar().showMessage("AI interpreting query image...")
        
        selected_model_key = self.combo_ai_model.currentData()
        
        settings = {'num_beams': 5, 'min_length': 20, 'length_penalty': 2.0, 'repetition_penalty': 1.2, 'mode': 'vector', 'model_key': selected_model_key}
        
        worker = AIWorker("", paths[0], [], settings)
        self._active_threads.append(worker)
        
        worker.progress_update.connect(lambda p, m: self.query_text.setText(m) if p == 100 else None)
        worker.finished.connect(lambda: self._active_threads.remove(worker) if worker in self._active_threads else None)
        worker.start()

    def start_live_scan(self):
        prompt = self.query_text.text()
        targets = [p for p in self.file_map.keys()]
        mode = "keyword" if self.combo_mode.currentIndex() == 0 else "vector"
        
        selected_model_key = self.combo_ai_model.currentData()
        
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
            'mode': mode,
            'model_key': selected_model_key
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