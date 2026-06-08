import os
import pytest
from unittest.mock import patch, mock_open
from engine.processor import collect_all_media
from engine.ai_worker import AIWorker, get_model_path, check_model_downloaded
from main import check_permissions

# ==========================================
# TESTS FÜR: processor.py
# ==========================================

def test_collect_all_media_valid_files(tmp_path):
    """Testet, ob gültige Bild- und Videodateien korrekt erkannt werden."""
    img = tmp_path / "test.jpg"
    img.write_text("dummy")
    vid = tmp_path / "test.mp4"
    vid.write_text("dummy")
    
    paths = [str(img), str(vid)]
    result = collect_all_media(paths)
    
    assert len(result) == 2
    assert str(img) in result
    assert str(vid) in result

def test_collect_all_media_invalid_files(tmp_path):
    """Testet, ob ungültige Dateiformate ignoriert werden."""
    txt = tmp_path / "document.txt"
    txt.write_text("dummy")
    pdf = tmp_path / "tabelle.pdf"
    pdf.write_text("dummy")
    
    paths = [str(txt), str(pdf)]
    result = collect_all_media(paths)
    
    assert len(result) == 0

def test_collect_all_media_directory(tmp_path):
    """Testet, ob Verzeichnisse korrekt rekursiv durchsucht werden."""
    sub_dir = tmp_path / "media"
    sub_dir.mkdir()
    
    img1 = sub_dir / "pic1.png"
    img1.write_text("dummy")
    
    img2 = tmp_path / "pic2.jpeg"
    img2.write_text("dummy")
    
    txt = sub_dir / "ignore.txt"
    txt.write_text("dummy")
    
    result = collect_all_media([str(tmp_path)])
    
    assert len(result) == 2
    assert str(img1) in result
    assert str(img2) in result

def test_collect_all_media_deduplication(tmp_path):
    """Testet, ob Duplikate gefiltert werden, wenn eine Datei mehrfach übergeben wird."""
    img = tmp_path / "test.jpg"
    img.write_text("dummy")
    
    paths = [str(img), str(img), str(tmp_path)] 
    result = collect_all_media(paths)
    
    assert len(result) == 1

def test_collect_all_media_empty_input():
    """Testet das Verhalten bei einer leeren Eingabeliste."""
    result = collect_all_media([])
    assert result == []

# ==========================================
# TESTS FÜR: ai_worker.py
# ==========================================

@pytest.fixture
def worker(qapp):
    """Fixture, die einen AIWorker bereitstellt."""
    return AIWorker(query_text="dummy", query_img_path=None, target_paths=[])

def test_get_clean_words_basic(worker):
    """Testet die Standard-Wortextraktion."""
    result = worker.get_clean_words("Hello World")
    assert result == ["hello", "world"]

def test_get_clean_words_stopwords(worker):
    """Testet, ob englische Stoppwörter entfernt werden."""
    result = worker.get_clean_words("The quick brown fox is in the box")
    assert result == ["quick", "brown", "fox", "box"]

def test_get_clean_words_punctuation(worker):
    """Testet, ob Satzzeichen sauber entfernt werden."""
    result = worker.get_clean_words("Cat, dog! Mouse?")
    assert result == ["cat", "dog", "mouse"]

def test_get_clean_words_numbers(worker):
    """Testet, ob Zahlen als gültige Wörter behandelt werden."""
    result = worker.get_clean_words("I have 2 cats")
    assert result == ["i", "have", "2", "cats"]

def test_strict_keyword_score_perfect_match(worker):
    """Testet das Scoring bei einem perfekten Keyword-Treffer."""
    worker.query_words = ["gray", "cat"]
    score = worker.calculate_strict_keyword_score("A gray cat is sitting", visual_score=0.0)
    assert score == 1.0

def test_strict_keyword_score_partial_match(worker):
    """Testet das Scoring bei einem teilweisen Treffer (über 50%)."""
    worker.query_words = ["gray", "cat", "sleeping"]
    score = worker.calculate_strict_keyword_score("A gray cat is awake", visual_score=0.0)
    assert round(score, 2) == 0.60

def test_strict_keyword_score_no_match(worker):
    """Testet das Scoring, wenn kein relevantes Wort gefunden wird."""
    worker.query_words = ["dog"]
    score = worker.calculate_strict_keyword_score("A gray cat", visual_score=0.5)
    assert score == 0.0

def test_strict_keyword_score_empty_query(worker):
    """Testet den Fallback auf den Visual Score, wenn keine Suchbegriffe vorliegen."""
    worker.query_words = []
    score = worker.calculate_strict_keyword_score("A gray cat", visual_score=0.8)
    assert score == 0.8



@patch('engine.ai_worker.os.path.exists')
@patch('engine.ai_worker.os.listdir')
def test_check_model_downloaded_true(mock_listdir, mock_exists):
    """Simuliert einen erfolgreichen Modell-Check."""
    mock_exists.return_value = True
    mock_listdir.return_value = ["config.json", "pytorch_model.bin"]
    assert check_model_downloaded("Base ") is True

@patch('engine.ai_worker.os.path.exists')
@patch('engine.ai_worker.os.listdir')
def test_check_model_downloaded_false_empty(mock_listdir, mock_exists):
    """Simuliert den Fall, dass der Modellordner existiert, aber leer ist."""
    mock_exists.return_value = True
    mock_listdir.return_value = []
    assert check_model_downloaded("Base ") is False

# ==========================================
# TESTS FÜR: main.py
# ==========================================

@patch('main.os.remove')
@patch('builtins.open', new_callable=mock_open)
@patch('main.os.makedirs')
def test_check_permissions_success(mock_makedirs, mock_file, mock_remove):
    """Testet, ob die Rechteprüfung erfolgreich ist, wenn Schreibzugriff besteht."""
    assert check_permissions() is True
    mock_makedirs.assert_called_once()
    mock_file.assert_called_once()
    mock_remove.assert_called_once()

@patch('main.os.makedirs', side_effect=PermissionError("Access Denied"))
def test_check_permissions_failure(mock_makedirs):
    """Testet, ob die Funktion korrekt 'False' zurückgibt, wenn keine Schreibrechte bestehen."""
    assert check_permissions() is False