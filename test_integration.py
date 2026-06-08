import pytest
import os
from unittest.mock import patch
from ui.main_window import MainWindow

# ==========================================
# FIXTURES
# ==========================================

@pytest.fixture
def main_win(qtbot):
    """
    Erstellt eine Instanz des Hauptfensters für die Tests.
    'qtbot' verwaltet den Lebenszyklus des Widgets sicher.
    """
    window = MainWindow()
    qtbot.addWidget(window)
    return window

@pytest.fixture
def test_image_path():
    """Gibt den Pfad zu deinem Testbild zurück und prüft, ob es existiert."""
    path = os.path.abspath("./test/Katze1.jpeg")
    if not os.path.exists(path):
        pytest.fail(f"Testbild nicht gefunden unter: {path}")
    return path

# ==========================================
# INTEGRATIONSTESTS
# ==========================================

def test_add_media_integration(main_win, test_image_path):
    """Prüft, ob dein reales Testbild korrekt im UI geladen wird."""
    paths = [test_image_path]
    
    main_win.add_files_to_view(paths)
    
    assert main_win.main_table.rowCount() == 1
    assert len(main_win.file_map) == 1
    assert os.path.basename(test_image_path) in main_win.main_table.item(0, 0).text()
    assert main_win.gallery_layout.count() == 1




def test_wipe_data_integration(main_win, test_image_path):
    """Prüft die Bereinigung nach dem Hinzufügen des realen Bildes."""
    main_win.add_files_to_view([test_image_path])
    assert main_win.main_table.rowCount() == 1
    
    main_win.wipe_data()
    
    assert main_win.main_table.rowCount() == 0
    assert len(main_win.file_map) == 0

def test_ui_updates_on_ai_result(main_win, test_image_path):
    """Prüft die UI-Aktualisierung mit deinem realen Testbild."""
    main_win.add_files_to_view([test_image_path])
    
    mock_result = {
        'path': test_image_path,
        'score': 0.85,
        'caption': "Eine Katze"
    }
    
    main_win.update_single_item(mock_result)
    
    row = main_win.file_map[test_image_path]['row']
    assert main_win.main_table.item(row, 3).text() == "85.0%"
    assert main_win.main_table.item(row, 4).text() == "Eine Katze"
    
    card = main_win.file_map[test_image_path]['card']
    assert card.score == 0.85
    assert card.is_hit is True

@patch('ui.main_window.AIWorker')
def test_scan_start_creates_worker(mock_worker_class, main_win, test_image_path):
    """Prüft den Scan-Start mit deinem realen Testbild."""
    main_win.add_files_to_view([test_image_path])
    main_win.query_text.setText("Katze")
    main_win.models_loaded = True
    
    main_win.start_live_scan()
    
    mock_worker_class.assert_called_once()
    assert len(main_win._active_threads) == 1

@patch('ui.main_window.AIWorker')   
def test_keyword_mode_passed_to_worker(mock_worker_class, main_win, test_image_path):
    """Prüft ob der Keyword Modus an den AIWorker übergeben wird."""
    main_win.add_files_to_view([test_image_path])

    main_win.query_text.setText("Katze")
    main_win.models_loaded = True

    main_win.combo_mode.setCurrentIndex(0)

    main_win.start_live_scan()

    args = mock_worker_class.call_args[0]

    settings = args[3]

    assert settings["mode"] == "keyword"

@patch('ui.main_window.AIWorker')
def test_vector_mode_passed_to_worker(
    mock_worker_class,
    main_win,
    test_image_path
):
    main_win.add_files_to_view([test_image_path])

    main_win.query_text.setText("Katze")
    main_win.models_loaded = True

    main_win.combo_mode.setCurrentIndex(1)

    main_win.start_live_scan()

    args = mock_worker_class.call_args[0]

    settings = args[3]

    assert settings["mode"] == "vector"