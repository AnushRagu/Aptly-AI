import re
from typing import List, Dict, Any


# ---------------------------------------------------------
# FILLER WORD DETECTION
# ---------------------------------------------------------

FILLER_PHRASES = [
    "you know",
    "i mean",
    "kind of",
    "sort of",
    "you see",
]

FILLER_WORDS = {
    "um",
    "umm",
    "ummm",
    "uh",
    "uhh",
    "uhhh",
    "er",
    "erm",
    "hmm",
    "hm",
    "like",
    "basically",
    "actually",
    "literally",
    "obviously",
}


def _normalise(text: str) -> str:
    return re.sub(
        r"\s+",
        " ",
        (text or "").lower()
    ).strip()


def filler_analysis(
    transcript: str,
    words=None
) -> Dict[str, Any]:

    text = _normalise(transcript)

    events = []

    # -----------------------------------------------------
    # Use timestamped transcription words when available
    # -----------------------------------------------------

    if words:

        for word_data in words:

            try:
                word = str(
                    word_data.get("word", "")
                ).strip()

                clean = re.sub(
                    r"[^a-zA-Z']",
                    "",
                    word.lower()
                )

                if clean in FILLER_WORDS:

                    events.append({
                        "word": word,
                        "timestamp": float(
                            word_data.get("start", 0)
                        ),
                        "estimated": False
                    })

            except (TypeError, ValueError, AttributeError):
                continue

    # -----------------------------------------------------
    # Fallback to transcript-based detection
    # -----------------------------------------------------

    if not events and text:

        # Multi-word fillers
        for phrase in FILLER_PHRASES:

            pattern = (
                r"\b"
                + re.escape(phrase)
                + r"\b"
            )

            for match in re.finditer(
                pattern,
                text
            ):

                events.append({
                    "word": phrase,
                    "timestamp": 0,
                    "estimated": True
                })

        # Single-word fillers
        tokens = re.findall(
            r"\b[\w']+\b",
            text
        )

        for token in tokens:

            if token in FILLER_WORDS:

                events.append({
                    "word": token,
                    "timestamp": 0,
                    "estimated": True
                })

    events.sort(
        key=lambda x: x["timestamp"]
    )

    # -----------------------------------------------------
    # Calculate filler rate
    # -----------------------------------------------------

    tokens = re.findall(
        r"\b[\w']+\b",
        text
    )

    total_words = len(tokens)
    total_fillers = len(events)

    filler_rate = (
        round(
            (total_fillers / total_words) * 100,
            2
        )
        if total_words
        else 0.0
    )

    return {
        "total": total_fillers,
        "events": events,
        "rate": filler_rate,
        "rate_per_minute": 0,
        "spikes": []
    }


# ---------------------------------------------------------
# SPEAKING RATE
# ---------------------------------------------------------

def pacing(
    transcript: str,
    duration_seconds: float
) -> Dict[str, Any]:

    text = _normalise(transcript)

    words = re.findall(
        r"\b[\w']+\b",
        text
    )

    word_count = len(words)

    duration = max(
        float(duration_seconds or 0),
        0.1
    )

    wpm = round(
        (word_count / duration) * 60
    )

    if wpm < 100:
        assessment = "Slow pace"

    elif wpm <= 160:
        assessment = "Good pace"

    elif wpm <= 190:
        assessment = "Fast pace"

    else:
        assessment = "Very fast pace"

    return {
        "wpm": wpm,
        "word_count": word_count,
        "assessment": assessment,
    }


# ---------------------------------------------------------
# PAUSE ANALYSIS
# ---------------------------------------------------------

def pauses(
    transcript: str,
    duration_seconds: float,
    words: List[Dict[str, Any]]
) -> Dict[str, Any]:

    if not words or len(words) < 2:

        return {
            "count": 0,
            "total_seconds": 0.0,
            "longest_seconds": 0.0,
            "assessment": "Not enough timing data",
            "events": []
        }

    gaps = []
    events = []

    for previous, current in zip(
        words,
        words[1:]
    ):

        try:

            previous_end = float(
                previous.get("end", 0)
            )

            current_start = float(
                current.get("start", 0)
            )

            gap = current_start - previous_end

            if gap >= 0.5:

                gap = round(gap, 2)

                gaps.append(gap)

                events.append({
                    "timestamp": round(
                        current_start,
                        2
                    ),
                    "duration": gap,
                    "estimated": False
                })

        except (
            TypeError,
            ValueError,
            AttributeError
        ):
            continue

    total_pause = round(
        sum(gaps),
        2
    )

    longest_pause = round(
        max(gaps),
        2
    ) if gaps else 0.0

    if longest_pause >= 3:

        assessment = "Frequent long pauses"

    elif longest_pause >= 2:

        assessment = "Some long pauses"

    elif gaps:

        assessment = "Natural pauses"

    else:

        assessment = "Very few pauses"

    return {
        "count": len(gaps),
        "total_seconds": total_pause,
        "longest_seconds": longest_pause,
        "assessment": assessment,
        "events": events
    }


# ---------------------------------------------------------
# CONTENT ANALYSIS
# ---------------------------------------------------------

def content_analysis(
    question: str,
    question_type: str,
    transcript: str
) -> Dict[str, Any]:

    text = _normalise(transcript)

    words = re.findall(r"\b[\w']+\b", text)
    word_count = len(words)

    if not text:
        return {
            "relevance": 0,
            "structure": 0,
            "technical_depth": 0,
            "overall_score": 0,
            "feedback": "No answer was detected.",
            "drill": "Answer the question directly and give one concrete example.",
            "strengths": [],
            "weaknesses": ["No answer detected."],
            "unsupported_claims": [],
            "should_follow_up": False,
            "follow_up_reason": ""
        }

    lower = text.lower()

    # ---------------------------------------------------------
    # RELEVANCE
    # ---------------------------------------------------------

    question_words = set(
        re.findall(r"\b[a-zA-Z]{4,}\b", question.lower())
    )

    answer_words = set(words)

    overlap = len(
        question_words.intersection(answer_words)
    )

    relevance = min(
        90,
        max(
            45,
            50 + overlap * 5
        )
    )

    # ---------------------------------------------------------
    # STRUCTURE
    # ---------------------------------------------------------

    structure = 48

    structure_markers = [
        "first",
        "second",
        "then",
        "finally",
        "because",
        "however",
        "therefore",
        "result",
        "outcome",
        "initially",
        "after",
        "before",
        "finally",
    ]

    structure_hits = sum(
        1
        for marker in structure_markers
        if re.search(
            r"\b" + re.escape(marker) + r"\b",
            lower
        )
    )

    structure += min(
        30,
        structure_hits * 6
    )

    if word_count >= 80:
        structure += 8

    structure = min(90, structure)

    # ---------------------------------------------------------
    # TECHNICAL DEPTH
    # ---------------------------------------------------------

    technical_terms = [
        "model",
        "algorithm",
        "dataset",
        "feature",
        "training",
        "testing",
        "accuracy",
        "precision",
        "recall",
        "python",
        "sql",
        "api",
        "docker",
        "deployment",
        "database",
        "architecture",
        "pipeline",
        "backend",
        "frontend",
        "machine learning",
        "deep learning",
        "neural network",
        "tf-idf",
        "cosine similarity",
        "random forest",
        "regression",
        "classification",
    ]

    technical_hits = sum(
        1
        for term in technical_terms
        if term in lower
    )

    technical_depth = min(
        90,
        max(
            45,
            48 + technical_hits * 6
        )
    )

    # ---------------------------------------------------------
    # EVIDENCE / RESULTS
    # ---------------------------------------------------------

    result_terms = [
        "accuracy",
        "percent",
        "%",
        "improved",
        "reduced",
        "increased",
        "decreased",
        "result",
        "outcome",
        "achieved",
        "measured",
        "score",
        "users",
        "seconds",
        "ms",
    ]

    has_evidence = any(
        term in lower
        for term in result_terms
    )

    # ---------------------------------------------------------
    # PERSONAL OWNERSHIP
    # ---------------------------------------------------------

    ownership_terms = [
        "i built",
        "i implemented",
        "i developed",
        "i designed",
        "i created",
        "i decided",
        "i chose",
        "i used",
        "my role",
        "my contribution",
        "i worked",
    ]

    has_ownership = any(
        phrase in lower
        for phrase in ownership_terms
    )

    # ---------------------------------------------------------
    # QUESTION TYPE SPECIFIC ANALYSIS
    # ---------------------------------------------------------

    strengths = []
    weaknesses = []

    if word_count >= 60:
        strengths.append(
            "The answer provides enough context to understand your approach."
        )
    else:
        weaknesses.append(
            "The answer is quite brief and leaves important details unexplained."
        )

    if has_ownership:
        strengths.append(
            "You clearly describe your personal involvement rather than only describing the project."
        )
    else:
        weaknesses.append(
            "Your personal contribution is not clearly separated from the overall project."
        )

    if has_evidence:
        strengths.append(
            "You include evidence or measurable details that support your answer."
        )
    else:
        weaknesses.append(
            "The answer does not include a concrete result or measurable outcome."
        )

    if technical_hits >= 2:
        strengths.append(
            "You reference relevant technical concepts rather than keeping the answer purely high-level."
        )
    else:
        weaknesses.append(
            "The technical explanation stays mostly at a high level."
        )

    # ---------------------------------------------------------
    # GENERATE SPECIFIC, NON-REPETITIVE FEEDBACK
    # ---------------------------------------------------------

    feedback_options = []

    if not has_ownership:

        feedback_options.extend([
            (
                "Your response explains the topic, but your individual "
                "contribution is still unclear. State exactly what you "
                "built, changed, or decided."
            ),
            (
                "The project context is understandable, but the interviewer "
                "needs more ownership. Focus on one action you personally "
                "took and explain why."
            ),
            (
                "You describe the overall work more than your role. Highlight "
                "one decision you made and the responsibility you personally "
                "handled."
            ),
        ])

    if not has_evidence:

        feedback_options.extend([
            (
                "The response explains the work but stops before showing its "
                "impact. Add a concrete result such as accuracy, latency, "
                "dataset size, or user outcome."
            ),
            (
                "Your approach is mentioned, but there is no clear proof of "
                "its impact. Finish with a measurable result or a specific "
                "before-and-after comparison."
            ),
            (
                "The answer would be more convincing with evidence. Mention "
                "what changed after your solution was implemented."
            ),
        ])

    if structure < 60:

        feedback_options.extend([
            (
                "The ideas arrive as a continuous explanation. Give the "
                "interviewer a clearer sequence: problem, approach, "
                "decision, and result."
            ),
            (
                "The main point is there, but the answer needs a cleaner "
                "flow. Start with the problem, explain your action, then "
                "close with the outcome."
            ),
            (
                "Your content is useful, but the narrative is difficult to "
                "follow. Separate the situation, your responsibility, "
                "your action, and the result."
            ),
        ])

    if technical_depth < 60:

        feedback_options.extend([
            (
                "The technical explanation stays fairly high-level. Explain "
                "why you chose the approach and mention one alternative or "
                "trade-off."
            ),
            (
                "You identify the technical idea, but the reasoning is thin. "
                "Explain how your solution worked and why it was appropriate."
            ),
            (
                "The answer names the technical problem without unpacking "
                "the solution. Describe the mechanism, the decision, and "
                "the trade-off you considered."
            ),
        ])

    if relevance < 60:

        feedback_options.extend([
            (
                "The response only partially answers the question. Lead with "
                "the direct answer before adding project background."
            ),
            (
                "Some context is useful, but the central question gets "
                "buried. Answer it directly first, then support your point "
                "with an example."
            ),
        ])

    if not feedback_options:

        feedback_options.extend([
            (
                "This is a solid response. Make it stronger by connecting "
                "your key decision directly to the result it produced."
            ),
            (
                "The answer covers the main idea well. Add one concrete "
                "example to make your reasoning easier to evaluate."
            ),
            (
                "You have a good foundation here. The next improvement is "
                "to make the technical or behavioral impact more specific."
            ),
        ])

    # Deterministic selection based on the actual question + answer.
    # This prevents identical fallback feedback across different answers
    # while keeping results reproducible.
    feedback_seed = (
        question.strip().lower()
        + "|"
        + text
        + "|"
        + question_type.strip().lower()
    )

    feedback_hash = 0

    for character in feedback_seed:

        feedback_hash = (
            (feedback_hash * 31)
            + ord(character)
        ) & 0xFFFFFFFF

    feedback = feedback_options[
        feedback_hash % len(feedback_options)
    ]

    if not has_ownership:

        drill = (
            "State your role, describe one action you personally took, "
            "and explain why you made that choice."
        )

    elif not has_evidence:

        drill = (
            "Finish with one measurable result or concrete outcome "
            "that shows the impact of your work."
        )

    elif technical_depth < 60:

        drill = (
            "Explain your approach, one alternative, the trade-off, "
            "and why you selected your final solution."
        )

    elif structure < 60:

        drill = (
            "Structure the answer as Problem → Approach → Decision → Result."
        )

    elif relevance < 60:

        drill = (
            "Answer the question in your first sentence, then provide "
            "supporting details and one example."
        )

    elif (
        question_type.lower() == "behavioral"
        and structure < 75
    ):

        drill = (
            "Use STAR: Situation → Task → Action → Result."
        )

    else:

        drill = (
            "Add one concrete example that demonstrates the impact "
            "of your decision."
        )

    # ---------------------------------------------------------
    # OVERALL SCORE
    # ---------------------------------------------------------

    overall_score = round(
        relevance * 0.35 +
        structure * 0.25 +
        technical_depth * 0.40
    )

    return {
        "relevance": relevance,
        "structure": structure,
        "technical_depth": technical_depth,
        "overall_score": overall_score,

        "feedback": feedback,

        "drill": drill,

        "strengths": strengths[:3],

        "weaknesses": weaknesses[:3],

        "unsupported_claims": [],

        "should_follow_up": (
            word_count >= 50
            and (
                question_type.lower() == "technical"
                or technical_hits >= 2
            )
        ),

        "follow_up_reason": (
            "Probe the candidate's technical decision-making and "
            "the reasoning behind their chosen approach."
            if question_type.lower() == "technical"
            else ""
        ),
    }