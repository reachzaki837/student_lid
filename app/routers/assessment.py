from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from app.routers.dashboard import get_current_user
from app.models.user import User, Assessment
from app.services.scoring import ScoringService

router = APIRouter(prefix="/assessment", tags=["assessment"])
templates = Jinja2Templates(directory="app/templates")

@router.get("/", response_class=HTMLResponse)
async def assessment_form(request: Request, user: User = Depends(get_current_user)):
    if not user:
        return RedirectResponse(url="/auth/login")
    return templates.TemplateResponse("assessment/form.html", {"request": request, "user": user})

@router.post("/submit")
async def submit_assessment(request: Request, user: User = Depends(get_current_user)):
    if not user:
        return RedirectResponse(url="/auth/login")
    

    form_data = await request.form()
    answers = dict(form_data)
    
    vark_scores = ScoringService.calculate_vark(answers)
    hm_scores = ScoringService.calculate_hm(answers)
    
    vark_style = ScoringService.get_dominant_style(vark_scores)
    hm_style = ScoringService.get_dominant_style(hm_scores)
    dominant_style = f"The {vark_style} {hm_style}"
    
    
    assessment = Assessment(
        user_email=user.email,
        vark_scores=vark_scores,
        hm_scores=hm_scores,
        dominant_style=dominant_style
    )
    await assessment.insert()
    
    return RedirectResponse(url="/dashboard", status_code=302)