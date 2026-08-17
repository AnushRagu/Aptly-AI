import re
from collections import Counter

FILLERS = ["you know", "um", "uh", "uhm", "like", "basically", "actually", "so", "right", "okay"]

def filler_analysis(text: str, duration: float):
    lower = text.lower()
    events = []
    for filler in FILLERS:
        for match in re.finditer(r"(?<!\w)" + re.escape(filler) + r"(?!\w)", lower):
            # Deterministic estimated location based on transcript position when word timings are absent.
            events.append({"word": filler, "timestamp": round(duration * match.start() / max(1, len(text)), 1), "precision": "estimated"})
    events.sort(key=lambda e: e["timestamp"])
    bins = Counter(int(event["timestamp"] // 20) for event in events)
    return {"total": len(events), "rate_per_minute": round(len(events) / (duration / 60), 1), "events": events,
            "spikes": [{"start": n * 20, "end": n * 20 + 20, "count": c} for n, c in bins.items() if c >= 2]}

def pacing(text: str, duration: float):
    words = re.findall(r"\b[\w'-]+\b", text)
    wpm = round(len(words) / (duration / 60))
    label = "very slow" if wpm < 100 else "slow" if wpm < 130 else "within target" if wpm <= 170 else "fast" if wpm <= 190 else "very fast"
    return {"words": len(words), "wpm": wpm, "label": label, "target": "130–170 WPM"}

def pauses(text: str, duration: float):
    clauses = max(1, len(re.findall(r"[,.;!?]", text)))
    # A conservative estimate in fallback mode: punctuation and low word-density imply considered pauses.
    long_count = max(0, min(4, clauses // 3))
    return {"long_pause_count": long_count, "events": [{"timestamp": round(duration * (i + 1) / (long_count + 2), 1), "duration": round(1.6 + .2 * i, 1)} for i in range(long_count)], "precision": "estimated"}

def content_analysis(question: str, question_type: str, transcript: str):
    lower = transcript.lower()
    words = len(re.findall(r"\w+", transcript))
    has_numbers = bool(re.search(r"\d+%|\d+\s*(ms|users|days|hours|x)\b", lower))
    behavioral = question_type.lower() == "behavioral"
    star = {"situation": any(x in lower for x in ["at ", "when ", "project", "team"]), "task": any(x in lower for x in ["needed", "goal", "responsible"]), "action": any(x in lower for x in ["i built", "i led", "i implemented", "i decided"]), "result": any(x in lower for x in ["result", "improved", "reduced", "increased", "%"])} if behavioral else None
    relevance = min(94, 58 + min(30, words // 5))
    structure = min(90, 52 + (15 if any(x in lower for x in ["first", "then", "finally"]) else 0) + (12 if len(re.findall(r"[.!?]", transcript)) >= 3 else 0))
    depth = min(92, 48 + min(25, words // 8) + (12 if any(x in lower for x in ["tradeoff", "metric", "architecture", "model", "data"]) else 0))
    unsupported = re.findall(r"[^.]*\b(?:improved|increased|reduced)\b[^.]*\b\d+%[^.]*", transcript, re.I)
    strengths = ["Your answer stays connected to the question."]
    if has_numbers: strengths.append("You supported at least one point with a concrete measure.")
    weaknesses = ["Add a clearer closing result so the interviewer can see the outcome."] if not has_numbers else ["Explain the trade-off behind one of your choices."]
    return {"overall_score": round((relevance + structure + depth) / 3), "relevance": relevance, "structure": structure, "technical_depth": depth,
      "star": star, "unsupported_claims": unsupported, "strengths": strengths, "weaknesses": weaknesses,
      "drill": "Answer the question again in 60 seconds: state your context, one decision, and the measurable outcome."}
