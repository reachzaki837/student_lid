import os
from langchain_groq import ChatGroq
from langchain_classic.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool
from app.services.rag import RAGService


# Initialize Groq Model
def get_llm():
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY is missing from environment")
    return ChatGroq(
        temperature=0,
        model_name="llama-3.3-70b-versatile",
        groq_api_key=api_key,
    )


# ----- TOOLS -----

@tool
def search_web(query: str) -> str:
    """Search the internet for real-time information, facts, research, or any topic the student asks about."""
    try:
        from ddgs import DDGS
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=5):
                results.append(r)
        if not results:
            return "No search results found. Try rephrasing the query."
        output_parts = []
        for r in results:
            title = r.get("title", "No title")
            body = r.get("body", "")
            href = r.get("href", "")
            output_parts.append(f"**{title}**\n{body}\nURL: {href}")
        return "\n\n---\n\n".join(output_parts)
    except Exception as e:
        return f"Web search error: {str(e)}. Try a more specific query."


@tool
def send_email_to_student(recipient_email: str, subject: str, message_body: str) -> str:
    """
    Send an email directly from the instructor to a specific student's email address.
    CRITICAL FORMATTING RULE: The `message_body` MUST be structured cleanly with line breaks (\n\n) 
    to separate the greeting, paragraphs, and sign-off. Do not provide a single wall of text!
    """
    try:
        from app.services.email import send_class_email_sync
        success = send_class_email_sync([recipient_email], subject, message_body)
        if success:
            return f"Successfully sent the email with subject '{subject}' to {recipient_email}."
        else:
            return f"Failed to send email to {recipient_email}. Ensure SMTP credentials are configured."
    except Exception as e:
        return f"Email dispatch error: {str(e)}"


@tool
def search_uploaded_course_materials(query: str) -> str:
    """Search internal uploaded course documents, PDFs, and curriculum materials for relevant content."""
    try:
        return RAGService.query_documents(query)
    except Exception as e:
        return f"Course material search error: {str(e)}"


@tool
def execute_python_code(code: str) -> str:
    """Execute Python code to run calculations, demonstrate algorithms, or simulate logic. Returns printed output."""
    try:
        import io
        import sys

        output = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = output

        safe_globals = {
            "__builtins__": __builtins__,
            "print": print,
            "sum": sum,
            "len": len,
            "list": list,
            "dict": dict,
            "set": set,
            "range": range,
            "enumerate": enumerate,
            "zip": zip,
            "map": map,
            "filter": filter,
            "sorted": sorted,
            "min": min,
            "max": max,
            "abs": abs,
            "round": round,
        }

        exec(code, safe_globals)
        sys.stdout = old_stdout
        result = output.getvalue()
        return result if result.strip() else "Code executed successfully (no output)."
    except Exception as e:
        sys.stdout = sys.__stdout__
        return f"Code Execution Error: {str(e)}"


# ----- AGENTS -----

class AgentService:

    @staticmethod
    async def get_teacher_agent_response(message: str, stats_str: str, teacher_name: str = "Instructor", teacher_email: str = "") -> str:
        """Handles the Teacher AI Chatbot using an Agent with GraphRAG and web search access."""
        try:
            llm = get_llm()
            agent_tools = [search_uploaded_course_materials, search_web, send_email_to_student]

            prompt = ChatPromptTemplate.from_messages([
                ("system", (
                    "You are an expert pedagogical AI teaching assistant for a university instructor.\n"
                    "Instructor Name: {teacher_name}\n"
                    "Instructor Email: {teacher_email}\n"
                    "You are currently analyzing the following live classroom analytics:\n\n"
                    "{stats}\n\n"
                    "Use the available tools when needed:\n"
                    "- 'search_uploaded_course_materials': Reference uploaded syllabus, curriculum or lesson content.\n"
                    "- 'search_web': Find real-time educational research or teaching strategies.\n"
                    "- 'send_email_to_student': Physically dispatch an email directly to a student's inbox.\n\n"
                    "Help the teacher design personalized lessons based on their students' learning styles. "
                    "Be thorough, structured, and pedagogically sound.\n\n"
                    "Rules:\n"
                    "1. If the teacher just says hi, hello, or asks a generic conversational question, reply directly to them warmly. Do NOT attempt to use tools for simple greetings.\n"
                    "2. Only use search tools when you explicitly need course context or external research to answer the teacher's question.\n"
                    "3. If the teacher asks you to draft an email or write a document, ALWAYS provide a drafted template immediately. Do not stubbornly refuse or demand more context; just use placeholders like [Student Name] or [Specific Topic].\n"
                    "4. If the teacher explicitly asks you to SEND an email to a specific student, you must use the 'send_email_to_student' tool immediately. Your drafted 'message_body' MUST contain paragraph breaks (\\n\\n) to nicely separate the greeting, main body, and sign-off so it looks clean and professional.\n"
                    "5. You MUST sign off every email using the instructor's EXACT Full Name ({teacher_name}) and Email ({teacher_email}) without shortening or omitting it."
                )),
                ("human", "{input}"),
                ("placeholder", "{agent_scratchpad}"),
            ])

            agent = create_tool_calling_agent(llm, agent_tools, prompt)
            executor = AgentExecutor(
                agent=agent,
                tools=agent_tools,
                verbose=True,
                handle_parsing_errors=True,
                max_iterations=5,
            )

            result = await executor.ainvoke({
                "input": message,
                "stats": stats_str,
                "teacher_name": teacher_name,
                "teacher_email": teacher_email,
            })

            return result.get("output", "No response generated.")
        except Exception as e:
            print(f"Teacher Agent Error: {e}")
            return f"Agent Generation Failed: {str(e)}"

    @staticmethod
    async def get_student_tutor_response(
        message: str, vark_style: str, hm_style: str, chat_history: list = None
    ) -> str:
        """Handles the Student AI Study Chatbot using an Agent tailored to their exact learning style."""
        try:
            llm = get_llm()
            agent_tools = [search_uploaded_course_materials, search_web, execute_python_code]

            prompt = ChatPromptTemplate.from_messages([
                ("system", (
                    "You are a world-class 1-on-1 AI Study Tutor, fully personalized for this student.\n\n"
                    "Student Learning Profile:\n"
                    "- VARK Style (how they absorb info): {vark_style}\n"
                    "- HM Style (how they think): {hm_style}\n\n"
                    "Adapt your teaching style accordingly:\n"
                    "- Visual: Use markdown tables, ASCII diagrams, bullet hierarchies, spatial language.\n"
                    "- Aural: Write conversationally with rhythm, use analogies.\n"
                    "- Read/Write: Use numbered lists, dense text explanations, suggest note-taking.\n"
                    "- Kinesthetic: Provide hands-on thought experiments, real-world applications, runnable code.\n\n"
                    "Available tools:\n"
                    "- 'search_web': Search the internet for facts, research, or explanations.\n"
                    "- 'search_uploaded_course_materials': Look up the student's uploaded class materials.\n"
                    "- 'execute_python_code': Run Python code to demonstrate algorithms or calculations.\n\n"
                    "Rules:\n"
                    "1. If the student greets you (hi/hello/hey), warmly greet them and ask what topic they want to study. Do NOT start teaching unprompted.\n"
                    "2. Give thorough, crystal-clear, markdown-formatted responses with headers, bold text, tables, and code blocks where appropriate.\n"
                    "3. Always use tools when the student asks you to search or calculate something."
                )),
                ("human", "{input}"),
                ("placeholder", "{agent_scratchpad}"),
            ])

            agent = create_tool_calling_agent(llm, agent_tools, prompt)
            executor = AgentExecutor(
                agent=agent,
                tools=agent_tools,
                verbose=True,
                handle_parsing_errors=True,
                max_iterations=6,
            )

            result = await executor.ainvoke({
                "input": message,
                "vark_style": vark_style,
                "hm_style": hm_style,
            })

            return result.get("output", "No response generated.")
        except Exception as e:
            print(f"Student Agent Error: {e}")
            return f"Agent Tutor Failed: {str(e)}"
