import random
import string
from fastapi import APIRouter, Request, Depends, Cookie, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from app.core.security import jwt
from app.core.config import settings
from app.models.user import User, Assessment, Class, Enrollment, Material
from app.services.scoring import ScoringService
from app.services.agent import AgentService
from app.services.rag import RAGService

router = APIRouter(tags=["dashboard"])
templates = Jinja2Templates(directory="app/templates")


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

async def get_current_user(access_token: str = Cookie(None)):
    if not access_token: return None
    try:
        payload = jwt.decode(access_token.replace("Bearer ", ""), settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return await User.find_one(User.email == payload.get("sub"))
    except (jwt.JWTError, KeyError, ValueError):
        return None

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
    for cls in classes:
        cls_enrolls = await Enrollment.find(Enrollment.class_code == cls.code).to_list()
        enrollments.extend(cls_enrolls)
        
    unique_emails = list(set([e.student_email for e in enrollments]))
    
    student_data = []
    style_counts = {"Visual": 0, "Aural": 0, "Read/Write": 0, "Kinesthetic": 0}
    
    for email in unique_emails:
        student = await User.find_one(User.email == email)
        assessment = await Assessment.find_one(Assessment.user_email == email, sort=[("created_at", -1)])
        email_profile = ScoringService.get_student_email_profile(email)
        
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
            "department": email_profile["department"],
            "degree": email_profile["degree"],
            "academic_progress": email_profile["academic_progress"]
        })

    return templates.TemplateResponse(request, "dashboard/teacher.html", {
        "user": user, 
        "classes": classes,  
        "active_classes": len(classes),
        "total_students": len(unique_emails),
        "student_data": student_data,
        "style_counts": style_counts
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
async def update_profile(name: str = Form(...), user: User = Depends(get_current_user)):
    if not user:
        return RedirectResponse(url="/auth/login")

    normalized_name = name.strip()
    if not normalized_name:
        return RedirectResponse(url="/dashboard/settings?profile_error=Display+name+cannot+be+empty", status_code=302)

    user.name = normalized_name
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

    if user.password != current_password:
        return RedirectResponse(url="/dashboard/settings?password_error=Current+password+is+incorrect", status_code=302)

    if len(new_password) < 6:
        return RedirectResponse(url="/dashboard/settings?password_error=New+password+must+be+at+least+6+characters", status_code=302)

    if new_password != confirm_password:
        return RedirectResponse(url="/dashboard/settings?password_error=New+password+and+confirm+password+must+match", status_code=302)

    user.password = new_password
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
    
    # 1. Dynamically calculate the live class stats
    classes = await Class.find(Class.teacher_email == user.email).to_list()
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
                
    stats_str = f"Total Students: {len(unique_emails)}. Learning Styles Breakdown -> Visual: {style_counts['Visual']}, Aural: {style_counts['Aural']}, Read/Write: {style_counts['Read/Write']}, Kinesthetic: {style_counts['Kinesthetic']}."
    
    # 2. Ask Groq for advice based on these stats
    response = await AgentService.get_teacher_agent_response(message, stats_str)
    return {"response": response}

@router.post("/dashboard/upload_document")
async def upload_document(file: UploadFile = File(...), user: User = Depends(get_current_user)):
    """Uploads document for GraphRAG query ingestion."""
    if not user:
        return JSONResponse(status_code=401, content={"error": "Unauthorized"})
    content = await file.read()
    success = await RAGService.process_upload(content, file.filename, user.email)
    if success:
        return {"filename": file.filename, "status": "success"}
    return JSONResponse(status_code=500, content={"error": "Failed to process document"})

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
        return {"error": "Unauthorized"}
        
    data = await request.json()
    message = data.get("message", "")
    
    assessment = await Assessment.find_one(Assessment.user_email == user.email, sort=[("created_at", -1)])
    vark_style = "Unknown"
    hm_style = "Unknown"
    if assessment:
        vark_style = max(assessment.vark_scores, key=assessment.vark_scores.get)
        hm_style = max(assessment.hm_scores, key=assessment.hm_scores.get)
        
    response = await AgentService.get_student_tutor_response(message, vark_style, hm_style)
    return {"response": response}