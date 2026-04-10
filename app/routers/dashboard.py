import random
import string
from datetime import datetime, timezone
from fastapi import APIRouter, Request, Depends, Cookie, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from app.core.security import jwt
from app.core.config import settings
from app.models.user import User, Assessment, Class, Enrollment, ConversationThread, ConversationMessage
from app.core.security import verify_password, get_password_hash
from app.services.scoring import ScoringService
from app.services.agent import AgentService
from pydantic import BaseModel
from typing import List, Optional

from app.services.email import send_class_email
from app.services.rag import RAGService

class EmailRequest(BaseModel):
    recipients: List[str]
    subject: str
    message: str


class ConversationCreateRequest(BaseModel):
    chat_type: str
    title: Optional[str] = None


class ConversationUpdateRequest(BaseModel):
    chat_type: str
    title: Optional[str] = None
    is_pinned: Optional[bool] = None

router = APIRouter(tags=["dashboard"])
templates = Jinja2Templates(directory="app/templates")


async def get_current_user(access_token: str = Cookie(None)):
    if not access_token:
        return None
    try:
        payload = jwt.decode(access_token.replace("Bearer ", ""), settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return await User.find_one(User.email == payload.get("sub"))
    except (jwt.JWTError, KeyError, ValueError):
        return None


MAX_MESSAGES_PER_THREAD = 100
MAX_HISTORY_CONTENT_LENGTH = 2000
MAX_USER_MESSAGE_CONTENT_LENGTH = 4000
MAX_ASSISTANT_MESSAGE_CONTENT_LENGTH = 12000


def _normalize_chat_type(chat_type: str) -> str:
    normalized = (chat_type or "").strip().lower()
    if normalized not in {"teacher", "student"}:
        raise ValueError("chat_type must be either 'teacher' or 'student'.")
    return normalized


def _summarize_title_from_message(message: str) -> str:
    cleaned = " ".join((message or "").strip().split())
    if not cleaned:
        return "New Chat"
    return cleaned[:60] + ("..." if len(cleaned) > 60 else "")


def _normalize_history_from_thread(thread: ConversationThread) -> list[dict]:
    history = []
    for turn in thread.messages[-8:]:
        role = str(getattr(turn, "role", "user") or "user").strip().lower()
        role = "assistant" if role in {"assistant", "ai"} else "user"
        content = str(getattr(turn, "content", "") or "").strip()
        if content:
            history.append({"role": role, "content": content})
    return history


def _sanitize_history(raw_history: object) -> list[dict]:
    cleaned = []
    if not isinstance(raw_history, list):
        return cleaned

    for turn in raw_history[-8:]:
        if not isinstance(turn, dict):
            continue
        role = str(turn.get("role", "user")).strip().lower()
        role = "assistant" if role in {"assistant", "ai"} else "user"
        content = str(turn.get("content", "")).strip()
        if content:
            cleaned.append({"role": role, "content": content[:MAX_HISTORY_CONTENT_LENGTH]})
    return cleaned


def _thread_preview(thread: ConversationThread) -> dict:
    return {
        "id": str(thread.id),
        "title": thread.title,
        "is_pinned": thread.is_pinned,
        "updated_at": thread.updated_at.isoformat(),
        "created_at": thread.created_at.isoformat(),
        "message_count": len(thread.messages),
    }


async def _resolve_thread_for_user(
    thread_id: Optional[str],
    owner_email: str,
    owner_role: str,
    first_message: str,
) -> ConversationThread:
    if thread_id:
        thread = await ConversationThread.get(thread_id)
        if thread and thread.owner_email == owner_email and thread.owner_role == owner_role:
            return thread

    now = datetime.now(timezone.utc)
    thread = ConversationThread(
        owner_email=owner_email,
        owner_role=owner_role,
        title=_summarize_title_from_message(first_message),
        created_at=now,
        updated_at=now,
    )
    await thread.insert()
    return thread


def _append_turn(thread: ConversationThread, role: str, content: str) -> bool:
    limit = MAX_ASSISTANT_MESSAGE_CONTENT_LENGTH if role == "assistant" else MAX_USER_MESSAGE_CONTENT_LENGTH
    original = (content or "").strip()
    trimmed = original[:limit]
    if not trimmed:
        return False
    is_truncated = len(original) > len(trimmed)
    thread.messages.append(ConversationMessage(role=role, content=trimmed, is_truncated=is_truncated))
    if len(thread.messages) > MAX_MESSAGES_PER_THREAD:
        thread.messages = thread.messages[-MAX_MESSAGES_PER_THREAD:]
    thread.updated_at = datetime.now(timezone.utc)
    return is_truncated


@router.get("/dashboard/conversations")
async def list_conversations(chat_type: str, user: User = Depends(get_current_user)):
    if not user:
        return JSONResponse(status_code=401, content={"error": "Unauthorized"})

    try:
        normalized_type = _normalize_chat_type(chat_type)
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"error": str(exc)})

    if user.role != normalized_type:
        return JSONResponse(status_code=403, content={"error": "Forbidden"})

    threads = await ConversationThread.find(
        ConversationThread.owner_email == user.email,
        ConversationThread.owner_role == normalized_type,
    ).sort([
        ("is_pinned", -1),
        ("updated_at", -1),
    ]).to_list()

    return {"conversations": [_thread_preview(thread) for thread in threads]}


@router.post("/dashboard/conversations")
async def create_conversation(payload: ConversationCreateRequest, user: User = Depends(get_current_user)):
    if not user:
        return JSONResponse(status_code=401, content={"error": "Unauthorized"})

    try:
        normalized_type = _normalize_chat_type(payload.chat_type)
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"error": str(exc)})

    if user.role != normalized_type:
        return JSONResponse(status_code=403, content={"error": "Forbidden"})

    now = datetime.now(timezone.utc)
    thread = ConversationThread(
        owner_email=user.email,
        owner_role=normalized_type,
        title=(payload.title or "New Chat").strip()[:80] or "New Chat",
        created_at=now,
        updated_at=now,
    )
    await thread.insert()
    return {"conversation": _thread_preview(thread)}


@router.get("/dashboard/conversations/{conversation_id}")
async def get_conversation(conversation_id: str, chat_type: str, user: User = Depends(get_current_user)):
    if not user:
        return JSONResponse(status_code=401, content={"error": "Unauthorized"})

    try:
        normalized_type = _normalize_chat_type(chat_type)
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"error": str(exc)})

    thread = await ConversationThread.get(conversation_id)
    if not thread or thread.owner_email != user.email or thread.owner_role != normalized_type:
        return JSONResponse(status_code=404, content={"error": "Conversation not found"})

    return {
        "conversation": _thread_preview(thread),
        "messages": [
            {
                "id": msg.message_id,
                "role": msg.role,
                "content": msg.content,
                "is_truncated": getattr(msg, "is_truncated", False),
                "created_at": msg.created_at.isoformat(),
            }
            for msg in thread.messages
        ],
    }


@router.patch("/dashboard/conversations/{conversation_id}")
async def update_conversation(
    conversation_id: str,
    payload: ConversationUpdateRequest,
    user: User = Depends(get_current_user),
):
    if not user:
        return JSONResponse(status_code=401, content={"error": "Unauthorized"})

    try:
        normalized_type = _normalize_chat_type(payload.chat_type)
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"error": str(exc)})

    thread = await ConversationThread.get(conversation_id)
    if not thread or thread.owner_email != user.email or thread.owner_role != normalized_type:
        return JSONResponse(status_code=404, content={"error": "Conversation not found"})

    if payload.title is not None:
        updated_title = payload.title.strip()[:80]
        if updated_title:
            thread.title = updated_title

    if payload.is_pinned is not None:
        thread.is_pinned = payload.is_pinned

    thread.updated_at = datetime.now(timezone.utc)
    await thread.save()
    return {"conversation": _thread_preview(thread)}


@router.delete("/dashboard/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str, chat_type: str, user: User = Depends(get_current_user)):
    if not user:
        return JSONResponse(status_code=401, content={"error": "Unauthorized"})

    try:
        normalized_type = _normalize_chat_type(chat_type)
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"error": str(exc)})

    thread = await ConversationThread.get(conversation_id)
    if not thread or thread.owner_email != user.email or thread.owner_role != normalized_type:
        return JSONResponse(status_code=404, content={"error": "Conversation not found"})

    await thread.delete()
    return {"status": "deleted"}


async def _build_teacher_stats(user_email: str) -> tuple[str, dict, int, int]:
    classes = await Class.find(Class.teacher_email == user_email).to_list()
    enrollments = []
    for cls in classes:
        cls_enrolls = await Enrollment.find(Enrollment.class_code == cls.code).to_list()
        enrollments.extend(cls_enrolls)

    unique_emails = list(set([e.student_email for e in enrollments]))
    style_counts = {"Visual": 0, "Aural": 0, "Read/Write": 0, "Kinesthetic": 0}

    for email in unique_emails:
        assessment = await Assessment.find_one(Assessment.user_email == email, sort=[("created_at", -1)])
        if assessment and assessment.vark_scores:
            style_name = max(assessment.vark_scores, key=assessment.vark_scores.get)
            if style_name in style_counts:
                style_counts[style_name] += 1

    stats_str = (
        f"Total Students: {len(unique_emails)}. Learning Styles Breakdown -> "
        f"Visual: {style_counts['Visual']}, "
        f"Aural: {style_counts['Aural']}, "
        f"Read/Write: {style_counts['Read/Write']}, "
        f"Kinesthetic: {style_counts['Kinesthetic']}."
    )
    return stats_str, style_counts, len(classes), len(unique_emails)


def get_settings_feedback(request: Request) -> dict:
    """Collect one-time settings status messages from query params."""
    return {
        "profile_success": request.query_params.get("profile_success"),
        "profile_error": request.query_params.get("profile_error"),
        "password_success": request.query_params.get("password_success"),
        "password_error": request.query_params.get("password_error"),
        "prefs_success": request.query_params.get("prefs_success"),
        "prefs_error": request.query_params.get("prefs_error"),
    }

@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, user: User = Depends(get_current_user)):
    if not user: return RedirectResponse(url="/auth/login")

    # STUDENT VIEW
    if user.role == "student":
        email_profile = ScoringService.get_student_email_profile(user.email)
        assessment = await Assessment.find_one(Assessment.user_email == user.email, sort=[("created_at", -1)])
        recommendations = {}
        if assessment:
            vark = ScoringService.get_dominant_style(assessment.vark_scores)
            hm = ScoringService.get_dominant_style(assessment.hm_scores)
            recommendations = await ScoringService.get_study_recommendations(vark, hm)
        
        enrollments = await Enrollment.find(Enrollment.student_email == user.email).to_list()
        classes = []
        for e in enrollments:
            cls = await Class.find_one(Class.code == e.class_code)
            if cls: classes.append(cls)
            
        return templates.TemplateResponse(request, "dashboard/student.html", {
            "user": user, "assessment": assessment, 
            "recommendations": recommendations, "classes": classes,
            "email_profile": email_profile
        })
    
    # TEACHER VIEW
    classes = await Class.find(Class.teacher_email == user.email).to_list()
    
    enrollments = []
    class_enrollments = {}
    for cls in classes:
        cls_enrolls = await Enrollment.find(Enrollment.class_code == cls.code).to_list()
        enrollments.extend(cls_enrolls)
        class_enrollments[cls.code] = [e.student_email for e in cls_enrolls]
        
    unique_emails = list(set([e.student_email for e in enrollments]))
    
    student_data = []
    style_counts = {"Visual": 0, "Aural": 0, "Read/Write": 0, "Kinesthetic": 0}
    
    for email in unique_emails:
        student = await User.find_one(User.email == email)
        assessment = await Assessment.find_one(Assessment.user_email == email, sort=[("created_at", -1)])
        email_profile = ScoringService.get_student_email_profile(email)

        saved_department = (getattr(student, "department", "") or "").strip() if student else ""
        saved_degree = (getattr(student, "degree", "") or "").strip() if student else ""
        saved_semester = (getattr(student, "semester", "") or "").strip() if student else ""

        display_department = saved_department or email_profile["department"]
        display_degree = saved_degree or email_profile["degree"]
        display_progress = saved_semester or email_profile["academic_progress"]
        
        style_name = "Pending"
        if assessment:
            style_name = max(assessment.vark_scores, key=assessment.vark_scores.get) if assessment.vark_scores else "Unknown"
            if style_name in style_counts:
                style_counts[style_name] += 1
                
        student_data.append({
            "name": student.name if student else "Unknown",
            "email": email,
            "style": style_name,
            "vark_scores": assessment.vark_scores if assessment else {},
            "hm_scores": assessment.hm_scores if assessment else {},
            "department": display_department,
            "degree": display_degree,
            "academic_progress": display_progress
        })

    all_students = await User.find(User.role == "student").to_list()

    return templates.TemplateResponse(request, "dashboard/teacher.html", {
        "user": user, 
        "classes": classes,  
        "active_classes": len(classes),
        "total_students": len(unique_emails),
        "student_data": student_data,
        "style_counts": style_counts,
        "all_students": all_students,
        "class_enrollments": class_enrollments
    })


@router.get("/dashboard/settings", response_class=HTMLResponse)
async def settings_page(request: Request, user: User = Depends(get_current_user)):
    if not user:
        return RedirectResponse(url="/auth/login")

    email_profile = ScoringService.get_student_email_profile(user.email)

    return templates.TemplateResponse(request, "dashboard/settings.html", {
        "user": user,
        "settings_feedback": get_settings_feedback(request),
        "email_profile": email_profile
    })

@router.post("/dashboard/create_class")
async def create_class(name: str = Form(...), user: User = Depends(get_current_user)):
    if not user or user.role != "teacher": return RedirectResponse(url="/auth/login")
    code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    await Class(name=name, code=code, teacher_email=user.email).insert()
    return RedirectResponse(url="/dashboard", status_code=302)

@router.post("/dashboard/join_class")
async def join_class(request: Request, code: str = Form(...), user: User = Depends(get_current_user)):
    if not user:
        return RedirectResponse(url="/auth/login")
    
    cls = await Class.find_one(Class.code == code)
    if not cls:
        # Fetch the student's existing enrolled classes for the template
        enrollments = await Enrollment.find(Enrollment.student_email == user.email).to_list()
        classes = []
        for e in enrollments:
            enrolled_cls = await Class.find_one(Class.code == e.class_code)
            if enrolled_cls:
                classes.append(enrolled_cls)
        
        email_profile = ScoringService.get_student_email_profile(user.email)
        assessment = await Assessment.find_one(Assessment.user_email == user.email, sort=[("created_at", -1)])
        recommendations = {}
        if assessment:
            vark = ScoringService.get_dominant_style(assessment.vark_scores)
            hm = ScoringService.get_dominant_style(assessment.hm_scores)
            recommendations = await ScoringService.get_study_recommendations(vark, hm)

        return templates.TemplateResponse(request, "dashboard/student.html", {
            "user": user,
            "error": "Invalid class code",
            "classes": classes,
            "assessment": assessment,
            "recommendations": recommendations,
            "email_profile": email_profile
        })
    
    existing = await Enrollment.find_one(Enrollment.student_email == user.email, Enrollment.class_code == code)
    if existing:
        return RedirectResponse(url="/dashboard", status_code=302)
    
    await Enrollment(student_email=user.email, class_code=code).insert()
    return RedirectResponse(url="/dashboard", status_code=302)

@router.post("/dashboard/manual_enroll")
async def manual_enroll(request: Request, user: User = Depends(get_current_user)):
    if not user or user.role != "teacher":
        return RedirectResponse(url="/auth/login")
        
    form_data = await request.form()
    class_code = form_data.get("class_code")
    student_emails = form_data.getlist("student_emails")
    
    if not class_code or not student_emails:
        return RedirectResponse(url="/dashboard", status_code=302)
        
    # Verify teacher owns this class
    cls = await Class.find_one(Class.code == class_code, Class.teacher_email == user.email)
    if not cls:
        return RedirectResponse(url="/dashboard", status_code=302)
        
    for email in student_emails:
        existing = await Enrollment.find_one(Enrollment.student_email == email, Enrollment.class_code == class_code)
        if not existing:
            await Enrollment(student_email=email, class_code=class_code).insert()
            
    return RedirectResponse(url="/dashboard", status_code=302)

@router.post("/dashboard/reset_assessment")
async def reset_assessment(student_email: str = Form(...), user: User = Depends(get_current_user)):
    if not user or user.role != "teacher": return RedirectResponse(url="/auth/login")
    await Assessment.find(Assessment.user_email == student_email).delete()
    return RedirectResponse(url="/dashboard", status_code=302)

@router.post("/dashboard/remove_student")
async def remove_student(student_email: str = Form(...), user: User = Depends(get_current_user)):
    if not user or user.role != "teacher": return RedirectResponse(url="/auth/login")
    classes = await Class.find(Class.teacher_email == user.email).to_list()
    for code in [c.code for c in classes]:
        await Enrollment.find(Enrollment.student_email == student_email, Enrollment.class_code == code).delete()
    return RedirectResponse(url="/dashboard", status_code=302)

@router.post("/dashboard/delete_class")
async def delete_class(class_code: str = Form(...), user: User = Depends(get_current_user)):
    if not user or user.role != "teacher": return RedirectResponse(url="/auth/login")
    await Class.find(Class.code == class_code).delete()
    await Enrollment.find(Enrollment.class_code == class_code).delete()
    return RedirectResponse(url="/dashboard", status_code=302)

# NEW ROUTE: Update Profile Settings
@router.post("/dashboard/update_profile")
async def update_profile(
    name: str = Form(...),
    department: str = Form(""),
    degree: str = Form(""),
    semester: str = Form(""),
    user: User = Depends(get_current_user)
):
    if not user:
        return RedirectResponse(url="/auth/login")

    normalized_name = name.strip()
    if not normalized_name:
        return RedirectResponse(url="/dashboard/settings?profile_error=Display+name+cannot+be+empty", status_code=302)

    user.name = normalized_name

    if user.role == "student":
        user.department = department.strip() or None
        user.degree = degree.strip() or None
        user.semester = semester.strip() or None

    await user.save()
    return RedirectResponse(url="/dashboard/settings?profile_success=Profile+updated+successfully", status_code=302)


@router.post("/dashboard/update_password")
async def update_password(
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
    user: User = Depends(get_current_user)
):
    if not user:
        return RedirectResponse(url="/auth/login")

    if not verify_password(current_password, user.password or ""):
        return RedirectResponse(url="/dashboard/settings?password_error=Current+password+is+incorrect", status_code=302)

    if len(new_password) < 6:
        return RedirectResponse(url="/dashboard/settings?password_error=New+password+must+be+at+least+6+characters", status_code=302)

    if new_password != confirm_password:
        return RedirectResponse(url="/dashboard/settings?password_error=New+password+and+confirm+password+must+match", status_code=302)

    user.password = get_password_hash(new_password)
    await user.save()
    return RedirectResponse(url="/dashboard/settings?password_success=Password+updated+successfully", status_code=302)


@router.post("/dashboard/update_preferences")
async def update_preferences(
    theme_mode: str = Form("light"),
    notifications_enabled: str = Form("off"),
    weekly_digest: str = Form("off"),
    focus_mode: str = Form("off"),
    user: User = Depends(get_current_user)
):
    if not user:
        return RedirectResponse(url="/auth/login")

    allowed_themes = {"light", "calm", "contrast"}
    if theme_mode not in allowed_themes:
        return RedirectResponse(url="/dashboard/settings?prefs_error=Invalid+theme+mode", status_code=302)

    user.theme_mode = theme_mode
    user.notifications_enabled = notifications_enabled == "on"
    user.weekly_digest = weekly_digest == "on"
    user.focus_mode = focus_mode == "on"
    await user.save()
    return RedirectResponse(url="/dashboard/settings?prefs_success=Preferences+saved", status_code=302)

@router.post("/dashboard/chat")
async def teacher_chat(request: Request, user: User = Depends(get_current_user)):
    """Handles the AI Teaching Assistant Chatbot"""
    if not user or user.role != "teacher": 
        return {"error": "Unauthorized"}
        
    data = await request.json()
    message = data.get("message", "")
    conversation_id = data.get("conversation_id")
    chat_history = _sanitize_history(data.get("chat_history", []))

    if not message.strip():
        return JSONResponse(status_code=400, content={"error": "Message is required."})

    thread = await _resolve_thread_for_user(conversation_id, user.email, "teacher", message)

    if not chat_history:
        chat_history = _normalize_history_from_thread(thread)

    stats_str, _, _, _ = await _build_teacher_stats(user.email)
    
    # 2. Ask Groq for advice based on these stats
    response = await AgentService.get_teacher_agent_response(
        message,
        stats_str,
        user.name,
        user.email,
        chat_history,
    )

    _append_turn(thread, "user", message)
    response_truncated = _append_turn(thread, "assistant", response)
    if len(thread.messages) <= 2 and thread.title == "New Chat":
        thread.title = _summarize_title_from_message(message)
    await thread.save()

    return {
        "response": response,
        "response_truncated": response_truncated,
        "conversation": _thread_preview(thread),
    }


@router.get("/dashboard/assistant", response_class=HTMLResponse)
async def teacher_assistant_page(request: Request, user: User = Depends(get_current_user)):
    if not user or user.role != "teacher":
        return RedirectResponse(url="/auth/login")

    stats_str, style_counts, class_count, student_count = await _build_teacher_stats(user.email)
    return templates.TemplateResponse(request, "dashboard/teacher_assistant.html", {
        "user": user,
        "stats_str": stats_str,
        "style_counts": style_counts,
        "class_count": class_count,
        "student_count": student_count,
    })

@router.post("/dashboard/upload_document")
async def upload_document(file: UploadFile = File(...), user: User = Depends(get_current_user)):
    """Uploads documents/images for RAG query ingestion."""
    if not user:
        return JSONResponse(status_code=401, content={"error": "Unauthorized"})
    content = await file.read()
    success, message = await RAGService.process_upload(content, file.filename, user.email)
    if success:
        return {"filename": file.filename, "status": "success"}

    status_code = 400 if "Unsupported file type" in message or "No readable content" in message else 500
    return JSONResponse(status_code=status_code, content={"error": message or "Failed to process document"})

@router.get("/dashboard/tutor", response_class=HTMLResponse)
async def student_tutor(request: Request, user: User = Depends(get_current_user)):
    """Renders the dedicated Student AI Tutor page."""
    if not user or user.role != "student":
        return RedirectResponse(url="/auth/login")
    
    assessment = await Assessment.find_one(Assessment.user_email == user.email, sort=[("created_at", -1)])
    if not assessment:
        return RedirectResponse(url="/assessment")
        
    return templates.TemplateResponse(request, "dashboard/student_chat.html", {
        "user": user, 
        "assessment": assessment
    })

@router.post("/dashboard/chat_student")
async def student_chat(request: Request, user: User = Depends(get_current_user)):
    """Handles the specialized Student AI Tutor Chatbot logic using ReAct."""
    if not user or user.role != "student":
        return JSONResponse(status_code=401, content={"error": "Unauthorized"})

    try:
        data = await request.json()
        message = data.get("message", "")
        conversation_id = data.get("conversation_id")

        if not message.strip():
            return JSONResponse(status_code=400, content={"error": "Message is required."})

        thread = await _resolve_thread_for_user(conversation_id, user.email, "student", message)

        chat_history = _sanitize_history(data.get("chat_history", []))
        if not chat_history:
            chat_history = _normalize_history_from_thread(thread)

        assessment = await Assessment.find_one(Assessment.user_email == user.email, sort=[("created_at", -1)])
        vark_style = "Unknown"
        hm_style = "Unknown"

        if assessment and assessment.vark_scores and assessment.hm_scores:
            vark_style = max(assessment.vark_scores, key=assessment.vark_scores.get)
            hm_style = max(assessment.hm_scores, key=assessment.hm_scores.get)

        response = await AgentService.get_student_tutor_response(message, vark_style, hm_style, chat_history)

        _append_turn(thread, "user", message)
        response_truncated = _append_turn(thread, "assistant", response)
        if len(thread.messages) <= 2 and thread.title == "New Chat":
            thread.title = _summarize_title_from_message(message)
        await thread.save()

        return {
            "response": response,
            "response_truncated": response_truncated,
            "conversation": _thread_preview(thread),
        }
    except (ValueError, TypeError) as e:
        return JSONResponse(status_code=400, content={"error": str(e)})
    except RuntimeError:
        return JSONResponse(status_code=500, content={"error": "Failed to generate tutor response."})

@router.post("/dashboard/send_email")
async def send_teacher_email(request: EmailRequest, user: User = Depends(get_current_user)):
    """Handles dispatching emails to students using Gmail SMTP in a background thread."""
    if not user or user.role != "teacher":
        return JSONResponse(status_code=401, content={"error": "Unauthorized"})
    
    success = await send_class_email(request.recipients, request.subject, request.message)
    
    if success:
        return {"status": "success", "message": f"Successfully dispatched email to {len(request.recipients)} students."}
    else:
        return JSONResponse(status_code=500, content={"error": "Failed to dispatch email. Check server configuration and App Password."})