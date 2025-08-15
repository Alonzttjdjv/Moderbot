from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy.orm import Session
import uvicorn
import os

from database.models import User, Bot, BotConfig
from database.database import get_db
from web.routers import auth, bots, configs

app = FastAPI(title="Bot Platform", version="1.0.0")

# Подключаем статические файлы
app.mount("/static", StaticFiles(directory="web/static"), name="static")

# Подключаем шаблоны
templates = Jinja2Templates(directory="web/templates")

# Подключаем роутеры
app.include_router(auth.router, prefix="/auth", tags=["authentication"])
app.include_router(bots.router, prefix="/bots", tags=["bots"])
app.include_router(configs.router, prefix="/configs", tags=["configurations"])

# Базовая аутентификация
security = HTTPBasic()

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Главная страница"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, credentials: HTTPBasicCredentials = Depends(security), db: Session = Depends(get_db)):
    """Панель управления"""
    # Проверяем аутентификацию
    user = auth.authenticate_user(credentials.username, credentials.password, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверные учетные данные",
            headers={"WWW-Authenticate": "Basic"},
        )
    
    # Получаем ботов пользователя
    user_bots = db.query(Bot).filter(Bot.user_id == user.id).all()
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user": user,
        "bots": user_bots
    })

@app.get("/bot/{bot_id}", response_class=HTMLResponse)
async def bot_detail(request: Request, bot_id: int, credentials: HTTPBasicCredentials = Depends(security), db: Session = Depends(get_db)):
    """Страница детальной информации о боте"""
    # Проверяем аутентификацию
    user = auth.authenticate_user(credentials.username, credentials.password, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверные учетные данные",
            headers={"WWW-Authenticate": "Basic"},
        )
    
    # Получаем бота
    bot = db.query(Bot).filter(Bot.id == bot_id, Bot.user_id == user.id).first()
    if not bot:
        raise HTTPException(status_code=404, detail="Бот не найден")
    
    # Получаем конфигурации бота
    configs = db.query(BotConfig).filter(BotConfig.bot_id == bot_id).all()
    
    return templates.TemplateResponse("bot_detail.html", {
        "request": request,
        "user": user,
        "bot": bot,
        "configs": configs
    })

@app.get("/bot/{bot_id}/config/{chat_id}", response_class=HTMLResponse)
async def bot_config(request: Request, bot_id: int, chat_id: str, credentials: HTTPBasicCredentials = Depends(security), db: Session = Depends(get_db)):
    """Страница настройки бота для конкретного чата"""
    # Проверяем аутентификацию
    user = auth.authenticate_user(credentials.username, credentials.password, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверные учетные данные",
            headers={"WWW-Authenticate": "Basic"},
        )
    
    # Получаем бота
    bot = db.query(Bot).filter(Bot.id == bot_id, Bot.user_id == user.id).first()
    if not bot:
        raise HTTPException(status_code=404, detail="Бот не найден")
    
    # Получаем конфигурацию чата
    config = db.query(BotConfig).filter(
        BotConfig.bot_id == bot_id,
        BotConfig.chat_id == chat_id
    ).first()
    
    if not config:
        raise HTTPException(status_code=404, detail="Конфигурация чата не найдена")
    
    return templates.TemplateResponse("bot_config.html", {
        "request": request,
        "user": user,
        "bot": bot,
        "config": config
    })

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)