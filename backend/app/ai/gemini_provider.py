import json
import os
import time

from google import genai
from google.genai import types


class GeminiProvider:

    MODEL = "gemini-3.6-flash"

    def __init__(self, api_key=None):
        api_key = api_key or os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise ValueError("GEMINI_API_KEY is not set")

        self.client = genai.Client(api_key=api_key)

    # ---------------------------------------------------------
    # Gemini request helper
    # ---------------------------------------------------------

    def _generate(self, prompt, json_mode=False):
        config = None

        if json_mode:
            config = types.GenerateContentConfig(
                response_mime_type="application/json"
            )

        last_error = None

        for attempt in range(3):
            try:
                response = self.client.models.generate_content(
                    model=self.MODEL,
                    contents=prompt,
                    config=config
                )

                text = (response.text or "").strip()

                if not text:
                    raise RuntimeError("Gemini returned an empty response")

                return text

            except Exception as exc:
                last_error = exc

                error_text = str(exc)

                if (
                    "503" in error_text
                    or "UNAVAILABLE" in error_text
                    or "429" in error_text
                    or "RESOURCE_EXHAUSTED" in error_text
                ):
                    time.sleep(2 ** attempt)
                    continue

                raise

        raise RuntimeError(
            f"Gemini request failed after retries: {last_error}"
        )

    # ---------------------------------------------------------
    # JSON helper
    # ---------------------------------------------------------

    def _ask_json(self, prompt):
        text = self._generate(
            prompt,
            json_mode=True
        )

        # Remove markdown fences if Gemini adds them anyway.
        if text.startswith("```"):
            text = text.replace("```json", "")
            text = text.replace("```", "")
            text = text.strip()

        try:
            return json.loads(text)

        except json.JSONDecodeError:
            # Try extracting the JSON object.
            start = text.find("{")
            end = text.rfind("}")

            if start != -1 and end != -1:
                try:
                    return json.loads(
                        text[start:end + 1]
                    )
                except json.JSONDecodeError:
                    pass

            # Try extracting a JSON array.
            start = text.find("[")
            end = text.rfind("]")

            if start != -1 and end != -1:
                try:
                    return json.loads(
                        text[start:end + 1]
                    )
                except json.JSONDecodeError:
                    pass

            raise RuntimeError(
                f"Gemini returned invalid JSON:\n{text}"
            )

    # ---------------------------------------------------------
    # Generate interview profile
    # ---------------------------------------------------------

    def profile(self, title, description):

        prompt = f"""
You are an expert technical recruiter.

Analyze this job description and create an interview profile.

Role:
{title}

Job Description:
{description}

Return ONLY valid JSON.

Use exactly these fields:

{{
    "role": "string",
    "seniority": "string",
    "skills": [],
    "technologies": [],
    "responsibilities": [],
    "behavioral_competencies": [],
    "likely_topics": []
}}

Rules:

- skills must be a JSON array of strings.
- technologies must be a JSON array of strings.
- responsibilities must be a JSON array of strings.
- behavioral_competencies must be a JSON array of strings.
- likely_topics must be a JSON array of strings.
- Do not include markdown.
- Do not include explanations.
"""

        result = self._ask_json(prompt)

        if not isinstance(result, dict):
            raise RuntimeError(
                "Gemini profile response was not a JSON object"
            )

        return result

    # ---------------------------------------------------------
    # Generate interview questions
    # ---------------------------------------------------------

    def generate_questions(
        self,
        title,
        job_description,
        interview_type,
        difficulty
    ):

        prompt = f"""
You are an expert interviewer.

Generate exactly 5 interview questions for this position.

Role:
{title}

Job Description:
{job_description}

Interview Type:
{interview_type}

Difficulty:
{difficulty}

Return ONLY valid JSON in exactly this structure:

{{
    "questions": [
        {{
            "question": "question text",
            "type": "technical"
        }},
        {{
            "question": "question text",
            "type": "behavioral"
        }},
        {{
            "question": "question text",
            "type": "technical"
        }},
        {{
            "question": "question text",
            "type": "behavioral"
        }},
        {{
            "question": "question text",
            "type": "technical"
        }}
    ]
}}

Rules:

- Generate exactly 5 questions.
- Mix technical and behavioral questions.
- Questions must be relevant to the role.
- Questions must match the requested difficulty.
- Do not include answers.
- Do not include markdown.
- Do not include explanations.
"""

        result = self._ask_json(prompt)

        if not isinstance(result, dict):
            raise RuntimeError(
                "Gemini questions response was not a JSON object"
            )

        questions = result.get("questions")

        if not isinstance(questions, list):
            raise RuntimeError(
                "Gemini questions response does not contain a questions array"
            )

        # Make sure every question has the expected fields.
        cleaned_questions = []

        for item in questions[:5]:

            if not isinstance(item, dict):
                continue

            question = item.get("question")

            if not question:
                continue

            cleaned_questions.append({
                "question": str(question).strip(),
                "type": str(
                    item.get("type", "behavioral")
                ).strip().lower()
            })

        if not cleaned_questions:
            raise RuntimeError(
                "Gemini generated no usable interview questions"
            )

        return {
            "questions": cleaned_questions
        }
        # ---------------------------------------------------------
        # Evaluate interview answer
        # ---------------------------------------------------------

        def evaluate_answer(
            self,
            title,
            question,
            question_type,
            transcript
        ):

            prompt = f"""
    You are an expert technical interviewer evaluating a candidate's answer.

    Role:
    {title}

    Question Type:
    {question_type}

    Interview Question:
    {question}

    Candidate Answer:
    {transcript}

    Evaluate ONLY this specific answer.

    Return ONLY valid JSON in exactly this structure:

    {{
        "relevance": 0,
        "structure": 0,
        "technical_depth": 0,
        "overall_score": 0,
        "feedback": "string",
        "drill": "string",
        "strengths": [],
        "weaknesses": [],
        "unsupported_claims": [],
        "should_follow_up": false,
        "follow_up_reason": "string"
    }}

    Rules:

    - Scores must be integers from 0 to 100.
    - relevance = how directly the answer addresses the question.
    - structure = clarity, organization, and logical flow.
    - technical_depth = quality of technical reasoning where applicable.
    - overall_score must reflect the three scores.
    - For behavioral questions, technical_depth should measure reasoning,
    decision-making, ownership, and specificity rather than pure technical knowledge.
    - Feedback MUST be specific to the candidate's actual answer.
    - NEVER use generic feedback such as:
    "The answer has useful detail, but it would be stronger..."
    - Identify the single most important weakness.
    - Mention something concrete from the candidate's answer when giving feedback.
    - If the answer is already strong, say specifically what made it strong.
    - The drill must directly target the weakest area.
    - strengths must contain 1-3 specific strengths.
    - weaknesses must contain 1-3 specific weaknesses.
    - unsupported_claims must be an array of objects with:
    {{"claim": "string", "reason": "string"}}
    - Only include unsupported_claims when the candidate makes a claim that
    cannot be supported by their answer.
    - should_follow_up should be true only when the answer gives the interviewer
    a specific point worth probing.
    - follow_up_reason should explain exactly what should be probed.
    - Do not invent achievements, metrics, technologies, or experience.
    - Do not include markdown.
    """

            result = self._ask_json(prompt)

            if not isinstance(result, dict):
                raise RuntimeError(
                    "Gemini answer evaluation was not a JSON object"
                )

            return result
    # ---------------------------------------------------------
    # Generate follow-up question
    # ---------------------------------------------------------

    def follow_up(
        self,
        title,
        transcript,
        question_type
    ):

        prompt = f"""
You are conducting a realistic job interview.

Role:
{title}

Question Type:
{question_type}

Candidate's Answer:
{transcript}

Generate ONE natural follow-up interview question.

The follow-up must:

- Directly relate to something in the candidate's answer.
- Probe deeper into their experience, reasoning, or technical understanding.
- Be specific rather than generic.
- Sound like a real interviewer.
- Not repeat the candidate's answer.
- Not ask "tell me more" without being specific.
- Be concise.

Return ONLY the question.
Do not include quotation marks.
Do not include explanations.
Do not include markdown.
"""

        result = self._generate(prompt)

        return result.strip()