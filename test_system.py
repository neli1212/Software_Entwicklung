# test_system.py

import os
import pytest
from unittest.mock import patch
from PySide6.QtCore import Qt
from ui.main_window import MainWindow

# ==========================================
# FIXTURES
# ==========================================

@pytest.fixture
def test_image_path():
    """Gibt den Pfad zu deinem Testbild zurück und prüft, ob es existiert."""
    test_image_path = os.path.abspath("./test/Katze1.jpeg")
    if not os.path.exists(test_image_path):
        pytest.fail(f"Testbild nicht gefunden unter: {test_image_path}")
    return test_image_path

# ==========================================
# SYSTEMTESTS 
# ==========================================
def test_e2e_application_starts(qtbot):
    """
    Benutzer kann die Anwendung öffnen.
    """
    window = MainWindow()
    qtbot.addWidget(window)

    assert window.isVisible() is False

    window.show()

    assert window.isVisible()
    assert window.scan_btn.isEnabled()
def test_e2e_add_file_to_queue(qtbot, test_image_path):
    """
    Benutzer fügt eine Datei hinzu.
    Die Datei erscheint in der Oberfläche.
    """
    window = MainWindow()
    qtbot.addWidget(window)

    window.add_files_to_view([test_image_path])

    assert len(window.file_map) == 1
    assert window.main_table.rowCount() == 1

def test_e2e_error_handling_no_input(qtbot, test_image_path):
    """
    Benutzer startet Suche ohne Query.
    Es erscheint eine Fehlermeldung.
    """
    window = MainWindow()
    qtbot.addWidget(window)

    window.add_files_to_view([test_image_path])
    window.models_loaded = True

    with patch("PySide6.QtWidgets.QMessageBox.warning") as mock_warning:
        qtbot.mouseClick(
            window.scan_btn,
            Qt.MouseButton.LeftButton
        )

        assert mock_warning.called

def test_e2e_user_can_change_model(qtbot):
    """
    Benutzer kann ein anderes Modell auswählen.
    """
    window = MainWindow()
    qtbot.addWidget(window)

    combo = window.combo_ai_model

    if combo.count() < 2:
        pytest.skip("Nur ein Modell vorhanden")

    first = combo.currentText()

    combo.setCurrentIndex(1)

    second = combo.currentText()

    assert first != second

def test_e2e_full_search_workflow(
    qtbot,
    test_image_path
):
    """
    Datei laden
    Query eingeben
    Suche starten
    Ergebnis erscheint
    """
    window = MainWindow()
    qtbot.addWidget(window)

    window.add_files_to_view([test_image_path])

    qtbot.keyClicks(
        window.query_text,
        "Eine Katze"
    )

    window.models_loaded = True

    with patch("ui.main_window.AIWorker") as MockWorker:
        worker = MockWorker.return_value

        qtbot.mouseClick(
            window.scan_btn,
            Qt.MouseButton.LeftButton
        )

        worker.start.assert_called_once()

        window.update_single_item(
            {
                "path": test_image_path,
                "score": 0.95,
                "caption": "Eine Katze sitzt im Garten",
            }
        )

    row = window.file_map[test_image_path]["row"]

    assert (
        window.main_table.item(row, 3).text()
        == "95.0%"
    )