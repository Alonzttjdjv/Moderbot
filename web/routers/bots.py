from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from database.database import get_db
from database.models import Bot, BotConfig, User
from web.routers import auth

router = APIRouter()

# Pydantic модели для API
class BotCreate(BaseModel):
    name: str
    platform: str
    token: str

class BotUpdate(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None

class BotResponse(BaseModel):
    id: int
    name: str
    platform: str
    is_active: bool
    created_at: str
    
    class Config:
        from_attributes = True

class BotConfigUpdate(BaseModel):
    welcome_message: Optional[str] = None
    commands: Optional[dict] = None
    responses: Optional[dict] = None
    filters: Optional[dict] = None
    permissions: Optional[dict] = None

@router.post("/", response_model=BotResponse)
async def create_bot(
    bot_data: BotCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth.get_current_user)
):
    """Создание нового бота"""
    try:
        # Проверяем, что платформа поддерживается
        supported_platforms = ["telegram", "discord", "vk"]
        if bot_data.platform not in supported_platforms:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Неподдерживаемая платформа. Поддерживаемые: {', '.join(supported_platforms)}"
            )
        
        # Создаем бота
        new_bot = Bot(
            user_id=current_user.id,
            name=bot_data.name,
            platform=bot_data.platform,
            token=bot_data.token,
            is_active=True
        )
        
        db.add(new_bot)
        db.commit()
        db.refresh(new_bot)
        
        return BotResponse(
            id=new_bot.id,
            name=new_bot.name,
            platform=new_bot.platform,
            is_active=new_bot.is_active,
            created_at=new_bot.created_at.isoformat()
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка создания бота: {str(e)}"
        )

@router.get("/", response_model=List[BotResponse])
async def get_user_bots(
    db: Session = Depends(get_db),
    current_user: User = Depends(auth.get_current_user)
):
    """Получение всех ботов пользователя"""
    try:
        bots = db.query(Bot).filter(Bot.user_id == current_user.id).all()
        
        return [
            BotResponse(
                id=bot.id,
                name=bot.name,
                platform=bot.platform,
                is_active=bot.is_active,
                created_at=bot.created_at.isoformat()
            )
            for bot in bots
        ]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка получения ботов: {str(e)}"
        )

@router.get("/{bot_id}", response_model=BotResponse)
async def get_bot(
    bot_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth.get_current_user)
):
    """Получение конкретного бота"""
    try:
        bot = db.query(Bot).filter(
            Bot.id == bot_id,
            Bot.user_id == current_user.id
        ).first()
        
        if not bot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Бот не найден"
            )
        
        return BotResponse(
            id=bot.id,
            name=bot.name,
            platform=bot.platform,
            is_active=bot.is_active,
            created_at=bot.created_at.isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка получения бота: {str(e)}"
        )

@router.put("/{bot_id}", response_model=BotResponse)
async def update_bot(
    bot_id: int,
    bot_data: BotUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth.get_current_user)
):
    """Обновление бота"""
    try:
        bot = db.query(Bot).filter(
            Bot.id == bot_id,
            Bot.user_id == current_user.id
        ).first()
        
        if not bot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Бот не найден"
            )
        
        # Обновляем поля
        if bot_data.name is not None:
            bot.name = bot_data.name
        if bot_data.is_active is not None:
            bot.is_active = bot_data.is_active
        
        db.commit()
        db.refresh(bot)
        
        return BotResponse(
            id=bot.id,
            name=bot.name,
            platform=bot.platform,
            is_active=bot.is_active,
            created_at=bot.created_at.isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка обновления бота: {str(e)}"
        )

@router.delete("/{bot_id}")
async def delete_bot(
    bot_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth.get_current_user)
):
    """Удаление бота"""
    try:
        bot = db.query(Bot).filter(
            Bot.id == bot_id,
            Bot.user_id == current_user.id
        ).first()
        
        if not bot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Бот не найден"
            )
        
        # Удаляем бота
        db.delete(bot)
        db.commit()
        
        return {"message": "Бот успешно удален"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка удаления бота: {str(e)}"
        )

@router.post("/{bot_id}/start")
async def start_bot(
    bot_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth.get_current_user)
):
    """Запуск бота"""
    try:
        bot = db.query(Bot).filter(
            Bot.id == bot_id,
            Bot.user_id == current_user.id
        ).first()
        
        if not bot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Бот не найден"
            )
        
        # Здесь должна быть логика запуска бота
        # Пока просто обновляем статус
        bot.is_active = True
        db.commit()
        
        return {"message": f"Бот {bot.name} запущен"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка запуска бота: {str(e)}"
        )

@router.post("/{bot_id}/stop")
async def stop_bot(
    bot_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth.get_current_user)
):
    """Остановка бота"""
    try:
        bot = db.query(Bot).filter(
            Bot.id == bot_id,
            Bot.user_id == current_user.id
        ).first()
        
        if not bot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Бот не найден"
            )
        
        # Здесь должна быть логика остановки бота
        # Пока просто обновляем статус
        bot.is_active = False
        db.commit()
        
        return {"message": f"Бот {bot.name} остановлен"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка остановки бота: {str(e)}"
        )

@router.get("/{bot_id}/configs")
async def get_bot_configs(
    bot_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth.get_current_user)
):
    """Получение конфигураций бота"""
    try:
        # Проверяем, что бот принадлежит пользователю
        bot = db.query(Bot).filter(
            Bot.id == bot_id,
            Bot.user_id == current_user.id
        ).first()
        
        if not bot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Бот не найден"
            )
        
        # Получаем конфигурации
        configs = db.query(BotConfig).filter(BotConfig.bot_id == bot_id).all()
        
        return [
            {
                "id": config.id,
                "chat_id": config.chat_id,
                "chat_name": config.chat_name,
                "chat_type": config.chat_type,
                "message_count": config.message_count,
                "last_activity": config.last_activity.isoformat() if config.last_activity else None,
                "created_at": config.created_at.isoformat()
            }
            for config in configs
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка получения конфигураций: {str(e)}"
        )

@router.put("/{bot_id}/configs/{chat_id}")
async def update_bot_config(
    bot_id: int,
    chat_id: str,
    config_data: BotConfigUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth.get_current_user)
):
    """Обновление конфигурации бота для конкретного чата"""
    try:
        # Проверяем, что бот принадлежит пользователю
        bot = db.query(Bot).filter(
            Bot.id == bot_id,
            Bot.user_id == current_user.id
        ).first()
        
        if not bot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Бот не найден"
            )
        
        # Получаем или создаем конфигурацию
        config = db.query(BotConfig).filter(
            BotConfig.bot_id == bot_id,
            BotConfig.chat_id == chat_id
        ).first()
        
        if not config:
            # Создаем новую конфигурацию
            config = BotConfig(
                bot_id=bot_id,
                user_id=current_user.id,
                chat_id=chat_id
            )
            db.add(config)
        
        # Обновляем настройки
        if config_data.welcome_message is not None:
            config.welcome_message = config_data.welcome_message
        if config_data.commands is not None:
            config.commands = config_data.commands
        if config_data.responses is not None:
            config.responses = config_data.responses
        if config_data.filters is not None:
            config.filters = config_data.filters
        if config_data.permissions is not None:
            config.permissions = config_data.permissions
        
        db.commit()
        
        return {"message": "Конфигурация обновлена успешно"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка обновления конфигурации: {str(e)}"
        )