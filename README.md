# StudentLID: Student Learning Style Identification System

An AI-powered educational platform designed to identify how students learn best and provide actionable, data-driven insights to both learners and educators. 

By combining established pedagogical frameworks (VARK and Honey & Mumford) with cutting-edge Generative AI, StudentLID transforms a simple quiz into a personalised learning engine.


## ❓ Why is this needed? (The Problem)
In a traditional classroom, a "one-size-fits-all" teaching approach inevitably leaves some students behind. A highly visual learner might struggle through a 45-minute audio lecture, while a kinesthetic learner might lose focus reading dense text. 

**StudentLID solves this by:**
1. Helping students understand their own cognitive wiring so they can study smarter, not harder.
2. Giving teachers instant, bird's-eye visibility into the learning modalities of their classroom.
3. Reducing teacher burnout by using AI to automatically generate lesson plans tailored to the *actual* makeup of their students.


## ✨ What does it do? (Key Features)

### 🧑‍🎓 For Students
* **Dual-Framework Assessment:** Students take a comprehensive quiz evaluating their primary information intake (VARK: Visual, Aural, Read/Write, Kinesthetic) and cognitive processing style (Honey & Mumford).
* **AI-Generated Study Strategies:** Upon completion, the platform queries an LLM to generate a highly personalized study strategy, recommending specific software tools (e.g., Miro for Visual learners, Speechify for Aural) and ideal study schedules.
* **Class Enrollment:** Students can easily join active classes using a 6-character alphanumeric invite code.

### 👩‍🏫 For Teachers
* **Classroom Analytics Dashboard:** Visualizes the distribution of learning styles across all active classes using interactive charts (Chart.js).
* **Roster Management:** View deep-dive profiles into individual student scores, reset assessments, or remove students.
* **1-Click Exports:** Instantly download classroom learning data as PDF, Excel (.xlsx), or CSV files for offline record-keeping.
* **Agentic AI Teaching Assistant:** A floating chatbot integrated directly into the dashboard. It dynamically reads the live database to understand the classroom's learning style distribution before answering, allowing teachers to ask: *"How should I teach gravity to this specific group of students?"*


## ⚙️ How it works (Tech Stack & Architecture)

StudentLID is built on a modern, asynchronous Python stack optimized for speed and real-time AI generation.

* **Backend:** [FastAPI](https://fastapi.tiangolo.com/) (High-performance asynchronous Python web framework).
* **Database:** [MongoDB](https://www.mongodb.com/) (NoSQL database for flexible user, class, and assessment schema storage).
* **Frontend:** HTML5, Bootstrap 5, Jinja2 Templating, and standard Vanilla JS.
* **AI Integration:** [Groq API](https://groq.com/) (Utilizing `llama-3.1-8b-instant` / `groq/compound` via the Groq Python SDK). 
    * *Note on AI:* The backend utilizes advanced Prompt Engineering techniques, specifically forcing **JSON Mode** outputs for the student dashboard to guarantee structured, easily parsed data, and **Context-Injection** for the teacher chatbot.
* **Data Visualization & Parsing:** Chart.js for analytics, Marked.js for rendering AI Markdown, and SheetJS/jsPDF for data exports.
