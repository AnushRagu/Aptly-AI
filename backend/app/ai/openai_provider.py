"""Small OpenAI-compatible provider; selected only when credentials are configured."""
import json
import os
from urllib import request
from .provider import AIProvider

class OpenAICompatibleProvider(AIProvider):
    def __init__(self):
        self.key = os.environ["OPENAI_API_KEY"]
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")

    def _ask(self, system: str, prompt: str) -> str:
        body = json.dumps({"model": self.model, "messages": [{"role":"system", "content":system}, {"role":"user", "content":prompt}], "temperature":0.3}).encode()
        req = request.Request(self.base_url + "/chat/completions", data=body, headers={"Authorization":"Bearer " + self.key, "Content-Type":"application/json"})
        with request.urlopen(req, timeout=20) as response:
            return json.loads(response.read())["choices"][0]["message"]["content"]

    def profile(self, title: str, description: str):
        text = self._ask("Return only valid JSON with role, seniority, skills, technologies, responsibilities, behavioral_competencies, likely_topics.", f"Role: {title}\nJD: {description}")
        return json.loads(text)

    def follow_up(self, title: str, transcript: str, question_type: str):
        return self._ask("You are a concise professional interviewer. Ask exactly one probing follow-up grounded in a concrete phrase from the candidate answer. No praise.", f"Role: {title}\nQuestion type: {question_type}\nCandidate answer: {transcript}")
