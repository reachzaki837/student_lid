import os
import logging
from typing import Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_classic.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool
from app.services.rag import RAGService

logger = logging.getLogger(__name__)


# Initialize Google Gemini Model
def get_llm(force_provider: Optional[str] = None) -> object:
    if force_provider == "google":
        google_api_key: Optional[str] = os.getenv("GOOGLE_API_KEY")
        if google_api_key:
            return ChatGoogleGenerativeAI(
                temperature=0,
                model="gemini-2.5-flash",
                google_api_key=google_api_key,
            )
        raise ValueError("GOOGLE_API_KEY must be configured for Google provider")

    if force_provider == "groq":
        groq_api_key: Optional[str] = os.getenv("GROQ_API_KEY")
        if groq_api_key:
            return ChatGroq(
                temperature=0,
                model="llama-3.3-70b-versatile",
                api_key=groq_api_key,
            )
        raise ValueError("GROQ_API_KEY must be configured for Groq provider")

    google_api_key: Optional[str] = os.getenv("GOOGLE_API_KEY")
    if google_api_key:
        return ChatGoogleGenerativeAI(
            temperature=0,
            model="gemini-2.5-flash",
            google_api_key=google_api_key,
        )

    groq_api_key: Optional[str] = os.getenv("GROQ_API_KEY")
    if groq_api_key:
        return ChatGroq(
            temperature=0,
            model="llama-3.3-70b-versatile",
            api_key=groq_api_key,
        )

    raise ValueError("Either GOOGLE_API_KEY or GROQ_API_KEY must be configured")


# ----- TOOLS -----

@tool
def search_web(query: str) -> str:
    """Search the internet for real-time information, facts, research, or any topic the student asks about."""
    try:
        from ddgs import DDGS
        from ddgs.exceptions import DDGSException, RatelimitException, TimeoutException

        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=3):
                results.append(r)
                
        if not results:
            return "No search results found for the query."
            
        output_parts = []

        for r in results:
            title = r.get("title", "No title")
            snippet = r.get("body", "")
            href = r.get("href", "")

            entry = f"Title: {title}\nURL: {href}\nSnippet: {snippet}\n"
            output_parts.append(entry)
            
        return "\n\n---\n\n".join(output_parts)
    except (RatelimitException, TimeoutException) as e:
        logger.warning("Web search temporarily unavailable: %s", e)
        return "Web search is temporarily unavailable. Please try again in a minute."
    except DDGSException as e:
        logger.info("Web search returned no usable results: %s", e)
        return "No web search results were found for this query."
    except (ImportError, RuntimeError, ValueError) as e:
        logger.exception("Web search tool failed")
        return f"Web search error: {str(e)}"


@tool
def search_youtube(query: str) -> str:
    """Search for educational YouTube videos related to the topic. Returns titles and links."""
    try:
        from ddgs import DDGS
        from ddgs.exceptions import DDGSException, RatelimitException, TimeoutException
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
    except (RatelimitException, TimeoutException) as e:
        logger.warning("YouTube search temporarily unavailable: %s", e)
        return "YouTube search is temporarily unavailable. Please try again in a minute."
    except DDGSException as e:
        logger.info("YouTube search returned no usable results: %s", e)
        return "No relevant YouTube videos were found for this topic."
    except (ImportError, RuntimeError, ValueError) as e:
        logger.exception("YouTube search tool failed")
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
    except (ImportError, RuntimeError, ValueError) as e:
        logger.exception("Email tool failed")
        return f"Email dispatch error: {str(e)}"


@tool
def search_uploaded_course_materials(query: str) -> str:
    """Search internal uploaded course materials (PDFs, text files, and analyzed images) for relevant content."""
    try:
        return RAGService.query_documents(query)
    except (RuntimeError, ValueError) as e:
        logger.exception("Course material search failed")
        return f"Course material search error: {str(e)}"


# ----- AGENTS -----

class AgentService:

    @staticmethod
    def _coerce_output_text(output: object) -> str:
        """Normalize provider-specific structured content into plain text for UI rendering."""
        if isinstance(output, str):
            return output

        if isinstance(output, list):
            parts = []
            for item in output:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict):
                    text_part = item.get("text")
                    if text_part:
                        parts.append(str(text_part))
                elif item is not None:
                    parts.append(str(item))
            return "\n".join(part for part in parts if part).strip() or "No response generated."

        if isinstance(output, dict):
            text_part = output.get("text")
            if text_part:
                return str(text_part)

        return str(output) if output is not None else "No response generated."

    @staticmethod
    def _friendly_agent_error(exc: Exception) -> str:
        message = str(exc)
        lowered = message.lower()
        if (
            "503" in lowered
            or "unavailable" in lowered
            or "high demand" in lowered
            or "overloaded" in lowered
            or "service unavailable" in lowered
        ):
            return "AI service is temporarily busy due to high demand. Please retry in about a minute."
        if "429" in lowered or "resource_exhausted" in lowered or "quota" in lowered:
            return "AI service is temporarily rate-limited. Please retry in about a minute."
        if "no results found" in lowered:
            return "I could not find enough external results just now. Please try rephrasing the query or try again shortly."
        return f"Agent request failed: {message}"

    @staticmethod
    def _should_retry_with_groq(exc: Exception) -> bool:
        lowered = str(exc).lower()
        retry_signals = (
            "429",
            "503",
            "quota",
            "resource_exhausted",
            "not found",
            "models/",
            "gemini",
            "rate limit",
            "unavailable",
            "high demand",
            "service unavailable",
            "temporarily unavailable",
            "overloaded",
        )
        return any(signal in lowered for signal in retry_signals)

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

            return AgentService._coerce_output_text(result.get("output", "No response generated."))
        except Exception as e:
            logger.exception("Teacher agent generation failed")

            if AgentService._should_retry_with_groq(e):
                try:
                    logger.warning("Retrying teacher agent with Groq fallback")
                    llm = get_llm(force_provider="groq")
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
                    return AgentService._coerce_output_text(result.get("output", "No response generated."))
                except Exception as fallback_exc:
                    logger.exception("Teacher Groq fallback failed")
                    return AgentService._friendly_agent_error(fallback_exc)

            return AgentService._friendly_agent_error(e)

    @staticmethod
    async def get_student_tutor_response(
        message: str, vark_style: str, hm_style: str, chat_history: list = None
    ) -> str:
        """Handles the Student AI Study Chatbot using an Agent tailored to their exact learning style."""
        try:
            llm = get_llm()
            agent_tools = [search_uploaded_course_materials, search_web, search_youtube]

            history_text = ""
            if chat_history:
                # Keep only a short tail of dialogue for context.
                turns = chat_history[-6:]
                formatted_turns = []
                for turn in turns:
                    role = turn.get("role", "user")
                    content = str(turn.get("content", "")).strip()
                    if content:
                        formatted_turns.append(f"{role}: {content}")
                history_text = "\n".join(formatted_turns)

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
                    "- Warm greetings only for the first message.\n"
                    "- Recent conversation context:\n{history_context}"
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
                "history_context": history_text or "No prior context provided.",
            })

            return AgentService._coerce_output_text(result.get("output", "No response generated."))
        except Exception as e:
            logger.exception("Student tutor agent generation failed")

            if AgentService._should_retry_with_groq(e):
                try:
                    logger.warning("Retrying student tutor with Groq fallback")
                    llm = get_llm(force_provider="groq")
                    agent_tools = [search_uploaded_course_materials, search_web, search_youtube]

                    history_text = ""
                    if chat_history:
                        turns = chat_history[-6:]
                        formatted_turns = []
                        for turn in turns:
                            role = turn.get("role", "user")
                            content = str(turn.get("content", "")).strip()
                            if content:
                                formatted_turns.append(f"{role}: {content}")
                        history_text = "\n".join(formatted_turns)

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
                            "- Warm greetings only for the first message.\n"
                            "- Recent conversation context:\n{history_context}"
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
                        "history_context": history_text or "No prior context provided.",
                    })
                    return AgentService._coerce_output_text(result.get("output", "No response generated."))
                except Exception as fallback_exc:
                    logger.exception("Student Groq fallback failed")
                    return AgentService._friendly_agent_error(fallback_exc)

            return AgentService._friendly_agent_error(e)
