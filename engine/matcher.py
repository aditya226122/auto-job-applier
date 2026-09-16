import json
import re
from typing import Dict, Any, Tuple
import config

class CandidateProfile:
    def __init__(self, profile_path=config.CANDIDATE_PROFILE_PATH):
        with open(profile_path, "r", encoding="utf-8") as f:
            self.data = json.load(f)

    @property
    def personal_info(self) -> Dict[str, Any]:
        return self.data.get("personal_info", {})

    @property
    def skills(self) -> Dict[str, Any]:
        return self.data.get("technical_skills", {})

    @property
    def projects(self) -> list:
        return self.data.get("projects", [])

    @property
    def education(self) -> list:
        return self.data.get("education", [])

    @property
    def preferences(self) -> Dict[str, Any]:
        return self.data.get("job_search_preferences", {})


class JobMatcher:
    def __init__(self, profile: CandidateProfile = None):
        self.profile = profile or CandidateProfile()
        self._build_keyword_index()

    def _build_keyword_index(self):
        # Extract skills and relevant keywords
        self.keywords = set()
        for prog in self.profile.skills.get("programming_languages", []):
            self.keywords.add(prog.lower())
        for tool in self.profile.skills.get("tools_and_platforms", []):
            self.keywords.add(tool.lower())
        for domain in self.profile.skills.get("domains_and_technical_skills", []):
            for word in domain.lower().split():
                if len(word) > 2:
                    self.keywords.add(word)
        for role in self.profile.preferences.get("target_roles", []):
            for word in role.lower().split():
                if len(word) > 2:
                    self.keywords.add(word)

        # Essential fresher / entry-level keywords
        self.fresher_indicators = {"fresher", "entry level", "trainee", "graduate", "junior", "associate", "intern", "b.tech", "eee", "0-1"}

    def is_location_in_india(self, location: str, description: str = "") -> bool:
        """Strictly checks if a job listing is located in India."""
        if not config.ONLY_INDIA:
            return True

        loc_text = f"{location} {description}".lower()

        # Reject obvious international locations
        non_india_keywords = [
            "germany", "deutschland", "berlin", "munich", "münchen", "leipzig", "rottenburg", 
            "hamburg", "frankfurt", "united states", "usa", "us", "united kingdom", "uk", "london", 
            "canada", "australia", "singapore", "austria", "switzerland", "m/w/d", "d/w/m", "gmbh"
        ]
        if any(re.search(r'\b' + re.escape(kw) + r'\b', loc_text) for kw in non_india_keywords):
            return False

        # Must match Indian cities or country
        return any(ind_loc in loc_text for ind_loc in config.INDIAN_LOCATIONS)

    def calculate_match_score(self, job: Dict[str, Any]) -> Tuple[int, str]:
        """Calculates relevance match score (0-100) and rationale for a job."""
        title = job.get("title", "").lower()
        location = job.get("location", "")
        description = job.get("description", "").lower()
        combined_text = f"{title} {description} {job.get('company', '').lower()}"

        # 1. Enforce Strict India Location Filter
        if not self.is_location_in_india(location, description):
            return 0, f"Rejected: Location '{location}' is outside India."

        score = 40  # baseline for verified fresher openings in India

        # Bonus for target titles
        matched_roles = []
        for target_role in self.profile.preferences.get("target_roles", []):
            if any(term in title for term in target_role.lower().split() if len(term) > 3):
                score += 15
                matched_roles.append(target_role)
                break

        # Bonus for fresher keywords
        if any(ind in combined_text for ind in self.fresher_indicators):
            score += 15

        # Check technical skills
        matched_skills = []
        for kw in ["iot", "embedded", "c programming", "c ", "sql", "arduino", "power bi", "power systems", "electric machines", "web dashboard", "excel", "n8n", "ai", "microcontroller", "hardware", "software"]:
            if re.search(r'\b' + re.escape(kw) + r'\b', combined_text):
                matched_skills.append(kw)
                score += 5

        final_score = min(98, max(30, score))
        rationale = f"Matched target role concepts ({', '.join(matched_roles) if matched_roles else 'Fresher Entry'}) and skills: {', '.join(matched_skills) if matched_skills else 'General Engineering'}."
        
        return final_score, rationale

    def generate_cover_letter_or_answer(self, question: str, job: Dict[str, Any]) -> str:
        """Intelligently answers dynamic application questions using candidate's resume context."""
        q_lower = question.lower()
        p_info = self.profile.personal_info
        
        if "why" in q_lower and ("hire" in q_lower or "fit" in q_lower or "interested" in q_lower):
            return (
                f"As an Electrical and Electronics Engineering student at JNTUK with hands-on project experience in IoT, "
                f"embedded microcontrollers, C programming, and SQL, I am eager to apply my analytical abilities and rapid learning skills "
                f"to the {job.get('title', 'role')} at {job.get('company', 'your organization')}. I bring strong teamwork, design thinking, and a passionate drive to build impactful real-world solutions."
            )
        elif "experience" in q_lower or "project" in q_lower:
            return (
                "During my internship at HMIES Pvt. Ltd. and academic projects, I built multi-parameter decision-making adaptive irrigation "
                "systems with cloud-edge architectures and voice-controlled smart dashboard systems interfacing microcontrollers, sensors, and cloud services."
            )
        elif "salary" in q_lower or "ctc" in q_lower:
            return "As per industry standards for freshers / negotiable."
        elif "notice" in q_lower or "joining" in q_lower:
            return "Immediate / Available immediately"
        elif "authorized" in q_lower or "visa" in q_lower or "sponsorship" in q_lower:
            return "Yes, legally authorized to work in India without sponsorship."
        elif "relocate" in q_lower:
            return "Yes, willing to relocate."
        elif "gpa" in q_lower or "cgpa" in q_lower:
            return "7.4 CGPA"
        else:
            return f"Motivated fresher ready to contribute effectively to {job.get('company')} with strong foundational engineering and technical skills."

matcher = JobMatcher()
