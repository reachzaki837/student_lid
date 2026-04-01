import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_classic.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool
from app.services.rag import RAGService


# Initialize Google Gemini Model
def get_llm():
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY is missing from environment")
    return ChatGoogleGenerativeAI(
        temperature=0,
        model="gemini-3.1-pro-preview",
        google_api_key=api_key,
    )


# ----- TOOLS -----

@tool
def search_web(query: str) -> str:
    """Search the internet for real-time information, facts, research, or any topic the student asks about."""
    try:
        from ddgs import DDGS
        import requests
        from bs4 import BeautifulSoup
        
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=3):
                results.append(r)
                
        if not results:
            return "No search results found for the query."
            
        output_parts = []
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        for r in results:
            title = r.get("title", "No title")
            snippet = r.get("body", "")
            href = r.get("href", "")
            
            scraped_text = ""
            try:
                resp = requests.get(href, headers=headers, timeout=4)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
                        tag.decompose()
                    text = soup.get_text(separator=' ', strip=True)
                    scraped_text = text[:1500] + ("..." if len(text) > 1500 else "")
            except Exception:
                pass
                
            entry = f"Title: {title}\nURL: {href}\nSnippet: {snippet}\n"
            if scraped_text:
                entry += f"Scraped Page Content: {scraped_text}\n"
            output_parts.append(entry)
            
        return "\n\n---\n\n".join(output_parts)
    except Exception as e:
        return f"Web search error: {str(e)}"


@tool
def search_youtube(query: str) -> str:
    """Search for educational YouTube videos related to the topic. Returns titles and links."""
    try:
        from ddgs import DDGS
        results = []
        with DDGS() as ddgs:
            # Use 'videos' method from ddgs to find YouTube content
            for r in ddgs.videos(query, max_results=4):
                results.append(r)
        
        if not results:
            return "No YouTube videos found. Try a different query."
            
        output_parts = []
        for r in results:
            title = r.get("title", "No title")
            link = r.get("content", r.get("embed_url", "No link"))
            description = r.get("description", "")
            output_parts.append(f"**{title}**\nLink: {link}\n{description}")
            
        return "\n\n---\n\n".join(output_parts)
    except Exception as e:
        return f"YouTube search error: {str(e)}"


@tool
def send_email_to_student(recipient_email: str, subject: str, message_body: str) -> str:
    """
    Send an email directly from the instructor to a specific student's email address.
    CRITICAL FORMATTING RULE: The `message_body` MUST be structured cleanly using explicitly escaped string sequences (\\n\\n) for paragraph breaks, otherwise the JSON parser will fail! Do NOT use actual literal line breaks.
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
        """Handles the Teacher AI Chatbot using an Agent with Perplexity-style research capabilities."""
        try:
            llm = get_llm()
            agent_tools = [search_uploaded_course_materials, search_web, search_youtube, send_email_to_student]

            prompt = ChatPromptTemplate.from_messages([
                ("system", (
                    "You are a world-class educational research assistant for {teacher_name} ({teacher_email}).\n"
                    "Your mission is to provide deep, Perplexity-style classroom insights using every tool in your belt.\n\n"
                    "INSTRUCTIONS:\n"
                    "1. For any conceptual or research question, ALWAYS use search_web, search_youtube, and search_uploaded_course_materials to gather data first.\n"
                    "2. Use stats to personalize advice: {stats}\n"
                    "3. Format your final report with clear H1/H2 headers, bold text, and numbered lists.\n"
                    "4. Include '### Recommended Videos' at the end of research answers.\n"
                    "5. Cite web sources directly: [Source](URL).\n\n"
                    "Rules: Only respond directly to greetings like 'hi' or 'hello'. For all other requests, you MUST trigger your search tools."
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
            agent_tools = [search_uploaded_course_materials, search_web, search_youtube, execute_python_code]

            prompt = ChatPromptTemplate.from_messages([
                ("system", (
                    "You are a world-class 1-on-1 AI Study Tutor and Researcher, acting like a high-end research engine (Perplexity style).\n"
                    "CORE INSTRUCTION: You MUST use your tools (search_web, search_youtube, search_uploaded_course_materials) for EVERY user query, even if you think you know the answer. Gather deep research first.\n\n"
                    "STUDENT PROFILE:\n"
                    "- VARK: {vark_style} | HM: {hm_style}\n\n"
                    "YOUR MISSION:\n"
                    "1. DEEP DIVE: For every topic, search the web, course files, and YouTube.\n"
                    "2. PERPLEXITY STYLE: Output answers in a structured, clean format with citations.\n"
                    "3. VISUALS & VIDEOS: Always end by suggesting '### Watch & Learn' with YouTube video links.\n"
                    "4. STYLE ADAPTATION: Adapt your response to their learning style.\n\n"
                    "Rules:\n"
                    "- Use headers, bold text, and numbered lists.\n"
                    "- Cite web sources directly.\n"
                    "- Warm greetings only for the first message."
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
