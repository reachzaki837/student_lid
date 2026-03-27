import os
import json
import re
from datetime import datetime, timezone
from groq import AsyncGroq, BadRequestError, APIConnectionError, APITimeoutError, RateLimitError, APIStatusError
from typing import Dict, Any
from dotenv import load_dotenv
load_dotenv()

GROQ_MODEL_CANDIDATES = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
]

DEPARTMENT_BY_CODE = {
    "ise": "Information Science and Engineering",
    "cs": "Computer Science",
    "ad": "Artificial Intelligence and Data Science",
    "al": "Artificial Intelligence and Machine Learning",
    "cd": "Computer Science and Design",
    "ag": "Agricultural Engineering",
    "bm": "Biomedical Engineering",
    "bt": "Biotechnology",
    "ce": "Civil Engineering",
    "cb": "Computer Science and Business Systems",
    "ct": "Computer Technology",
    "ee": "Electrical and Electronics Engineering",
    "ec": "Electronics and Communication Engineering",
    "ei": "Electronics and Instrumentation Engineering",
    "ft": "Fashion Technology",
    "fd": "Food Technology",
    "it": "Information Technology",
    "me": "Mechanical Engineering",
    "mz": "Mechatronics Engineering",
    "tt": "Textile Technology",
}

BTECH_DEPARTMENTS = {
    "Agricultural Engineering",
    "Artificial Intelligence and Data Science",
    "Biotechnology",
}

YEAR_LABELS = {
    1: "I Year",
    2: "II Year",
    3: "III Year",
    4: "IV Year",
}

DEPARTMENT_PATTERN = re.compile(
    r"(" + "|".join(sorted(DEPARTMENT_BY_CODE.keys(), key=len, reverse=True)) + r")(\d{2})"
)

class ScoringService:
    @staticmethod
    def get_student_email_profile(email: str) -> Dict[str, Any]:
        default_profile = {
            "department_code": "N/A",
            "department": "Unknown Department",
            "degree": "N/A Degree",
            "join_year": None,
            "batch": "N/A Batch",
            "study_year": "N/A",
            "semester": "N/A",
            "academic_progress": "N/A Progress",
        }

        if not email or "@" not in email:
            return default_profile

        local_part = email.split("@", 1)[0].lower()
        matches = list(DEPARTMENT_PATTERN.finditer(local_part))
        if not matches:
            return default_profile

        match = matches[-1]
        department_code = match.group(1)
        join_year = 2000 + int(match.group(2))
        department = DEPARTMENT_BY_CODE.get(department_code, "Unknown Department")

        degree_prefix = "B.Tech." if department in BTECH_DEPARTMENTS else "B.E."
        degree = f"{degree_prefix} - {department}" if department != "Unknown Department" else "N/A Degree"

        now = datetime.now(timezone.utc)
        # Academic year runs Jul-Jun. Jan-Jun belongs to the previous academic year's even semester.
        if now.month >= 7:
            academic_year_offset = now.year - join_year
            semester_number = academic_year_offset * 2 + 1  # odd sem (Jul-Dec)
        else:
            academic_year_offset = now.year - join_year - 1
            semester_number = academic_year_offset * 2 + 2  # even sem (Jan-Jun)
        semester_number = min(max(semester_number, 1), 8)
        year_number = min(max(academic_year_offset + 1, 1), 4)

        batch = f"{join_year}-{join_year + 4}"
        study_year = YEAR_LABELS.get(year_number, "N/A")
        semester = f"Sem {semester_number}"
        academic_progress = f"{batch} | {study_year} | {semester}"

        return {
            "department_code": department_code.upper(),
            "department": department,
            "degree": degree,
            "join_year": join_year,
            "batch": batch,
            "study_year": study_year,
            "semester": semester,
            "academic_progress": academic_progress,
        }

    @staticmethod
    def calculate_vark(answers: Dict[str, str]) -> Dict[str, int]:
        scores = {"Visual": 0, "Aural": 0, "Read/Write": 0, "Kinesthetic": 0}
        for k, v in answers.items():
            if k.startswith("vark_") and v in scores: scores[v] += 1
        return scores

    @staticmethod
    def calculate_hm(answers: Dict[str, str]) -> Dict[str, int]:
        scores = {"Activist": 0, "Reflector": 0, "Theorist": 0, "Pragmatist": 0}
        for k, v in answers.items():
            if k.startswith("hm_") and v in scores: scores[v] += 1
        return scores

    @staticmethod
    def get_dominant_style(scores: Dict[str, int]) -> str:
        return max(scores, key=scores.get) if scores else "Unknown"

    @staticmethod
    async def get_study_recommendations(vark_style: str, hm_style: str) -> Dict[str, Any]:
        
        # 1. ATTEMPT TO GET DYNAMIC AI RECOMMENDATIONS VIA GROQ
        api_key = os.getenv("GROQ_API_KEY")
        
        if api_key:
            try:
                # Initialize the Async Groq client
                client = AsyncGroq(api_key=api_key)
                
                prompt = f"""
                A student has the following learning profile:
                - Primary Information Intake (VARK): {vark_style}
                - Primary Cognitive Processing (Honey & Mumford): {hm_style}

                Provide a highly personalized study strategy tailored to this exact combination.
                You MUST return ONLY valid JSON in the exact following structure. Do not include any markdown formatting.
                {{
                    "tips": [
                        "Actionable tip 1 combining both styles",
                        "Actionable tip 2 combining both styles",
                        "Actionable tip 3 combining both styles",
                        "Actionable tip 4 combining both styles"
                    ],
                    "tools": [
                        "Software/App 1 (Brief description of why it fits their {vark_style} style)",
                        "Software/App 2 (Brief description of why it fits their {vark_style} style)",
                        "Software/App 3 (Brief description of why it fits their {vark_style} style)"
                    ],
                    "schedule": "A specific paragraph describing their ideal study block schedule and routine based heavily on their {hm_style} trait."
                }}
                """
                
                # Make the API call enforcing JSON mode and gracefully fall back between model options.
                chat_completion = None
                for model_name in GROQ_MODEL_CANDIDATES:
                    try:
                        chat_completion = await client.chat.completions.create(
                            messages=[
                                {
                                    "role": "system",
                                    "content": "You are an expert academic advisor. You strictly output valid JSON."
                                },
                                {
                                    "role": "user",
                                    "content": prompt
                                }
                            ],
                            model=model_name,
                            response_format={"type": "json_object"}, 
                        )
                        break
                    except (BadRequestError, APIStatusError) as model_error:
                        print(f"Groq model '{model_name}' unavailable: {model_error}")

                if chat_completion is None:
                    raise ValueError("No available Groq models for recommendations")
                
                # Extract and parse the JSON response
                raw_text = chat_completion.choices[0].message.content
                ai_recommendations = json.loads(raw_text)
                
                # Verify the AI returned the exact keys we need for the HTML
                if all(k in ai_recommendations for k in ("tips", "tools", "schedule")):
                    return ai_recommendations

            except (json.JSONDecodeError, KeyError, ValueError, APIConnectionError, APITimeoutError, RateLimitError, APIStatusError, BadRequestError) as e:
                print(f"Groq AI Generation failed: {e}. Falling back to static rules.")

        # 2. FAILSAFE FALLBACK (If API Key is missing, rate-limited, or generation fails)
        vark_tips = {
            "Visual": ["Convert your notes into diagrams, charts, or mind maps.", "Use different color highlighters to group distinct concepts together."],
            "Aural": ["Record lectures and listen to them again.", "Discuss topics with other students or your teachers."],
            "Read/Write": ["Write your notes out repeatedly to memorize them.", "Use bulleted lists and headings to organize your thoughts."],
            "Kinesthetic": ["Use real-life examples and case studies to understand theories.", "Create physical models or perform hands-on experiments."]
        }
        hm_tips = {
            "Activist": ["Brainstorm ideas with a group.", "Jump into problems and learn by doing."],
            "Reflector": ["Take time to review and reflect before making decisions.", "Gather as much data as possible before starting an assignment."],
            "Theorist": ["Look for the underlying logic and patterns in the material.", "Organize your notes systematically and logically."],
            "Pragmatist": ["Focus on how to apply the theory to real-world problems.", "Experiment with new study techniques to see if they work."]
        }
        tools = {
            "Visual": ["Miro (Digital Mind Mapping)", "Canva (Visual Notes)", "Lucidchart (Flowcharts)"],
            "Aural": ["Speechify (Text-to-Speech)", "Otter.ai (Lecture Recording)", "Audible (Audiobooks)"],
            "Read/Write": ["Notion (Note Organization)", "Evernote", "Quizlet (Text Flashcards)"],
            "Kinesthetic": ["Forest (Interactive Focus Timer)", "Labster (Virtual Labs)", "Anki (Active Recall)"]
        }
        schedules = {
            "Activist": "Short, intense bursts. Try the Pomodoro technique (25 mins work, 5 mins break) to keep your energy high and avoid boredom.",
            "Reflector": "Longer, uninterrupted blocks. Give yourself generous 60-90 minute sessions to deeply read, review, and thoroughly process information.",
            "Theorist": "Structured 45-minute blocks. Spend 30 minutes reading the core theory, and 15 minutes organizing your notes into a strict, logical framework.",
            "Pragmatist": "Project-based sessions. Instead of studying by time, study by task. Focus on completing one practical problem or case study per session."
        }

        return {
            "tips": vark_tips.get(vark_style, []) + hm_tips.get(hm_style, []),
            "tools": tools.get(vark_style, ["Notion", "Quizlet"]),
            "schedule": schedules.get(hm_style, "Standard Pomodoro (25m study / 5m break)")
        }
    @staticmethod
    async def get_teacher_chat_response(message: str, stats: str) -> str:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            return "Please configure the GROQ_API_KEY in your .env file."
        
        try:
            client = AsyncGroq(api_key=api_key)
            system_prompt = f"""You are an expert pedagogical AI assistant integrated into a Teacher Dashboard. 
            Here is the live makeup of this teacher's class right now:
            {stats}
            
            Based on this exact data, answer the teacher's questions, suggest lesson plans, or give specific teaching activities that cater to these dominant learning modalities. 
            Keep your answers concise, actionable, and formatted clearly."""
            
            chat_completion = None
            for model_name in GROQ_MODEL_CANDIDATES:
                try:
                    chat_completion = await client.chat.completions.create(
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": message}
                        ],
                        model=model_name,
                    )
                    break
                except (BadRequestError, APIStatusError) as model_error:
                    print(f"Groq model '{model_name}' unavailable for teacher chat: {model_error}")

            if chat_completion is None:
                return "AI assistant is temporarily unavailable. Please try again shortly."

            return chat_completion.choices[0].message.content
        except (ConnectionError, ValueError, KeyError, APIConnectionError, APITimeoutError, RateLimitError, APIStatusError, BadRequestError) as e:
            return f"AI Generation failed: {e}"