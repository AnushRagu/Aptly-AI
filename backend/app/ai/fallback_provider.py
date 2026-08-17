import re
from .provider import AIProvider

class FallbackProvider(AIProvider):
    def profile(self, title, description):
        skills = [s for s in ["Python", "SQL", "Machine Learning", "React", "Communication", "System design"] if s.lower() in (title + description).lower()]
        return {"role": title, "seniority": "Early-to-mid career", "skills": skills or ["Communication", "Problem solving", "Collaboration"], "technologies": [s for s in skills if s in ["Python", "SQL", "Machine Learning", "React"]] or ["Role-specific tools"], "responsibilities": ["Deliver measurable outcomes", "Collaborate across teams", "Explain decisions clearly"], "behavioral_competencies": ["Ownership", "Structured communication", "Adaptability"], "likely_topics": ["Experience overview", "Role-specific decisions", "Project impact", "Collaboration"]}
    def follow_up(self, title, transcript, question_type):
        nouns = re.findall(r"\b(?:model|system|project|team|pipeline|feature|architecture|data|customer|metric)\b", transcript, re.I)
        anchor = nouns[0].lower() if nouns else "that approach"
        return f"You mentioned {anchor}. What trade-off did you make there, and how did you know the result was successful?"
