from app.analysis import filler_analysis, pacing, pauses

def test_filler_detection():
    result = filler_analysis("Um, I basically built it, you know.", 30)
    assert result["total"] == 3

def test_pacing():
    assert pacing("word " * 150, 60)["wpm"] == 150

def test_pauses():
    assert "long_pause_count" in pauses("First, then, finally.", 60)
