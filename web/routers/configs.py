from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from database.database import get_db
from database.models import Bot, BotConfig, User
from web.routers import auth

router = APIRouter()

# Pydantic модели для API
class ConfigUpdate(BaseModel):
    welcome_message: Optional[str] = None
    commands: Optional[dict] = None
    responses: Optional[dict] = None
    filters: Optional[dict] = None
    permissions: Optional[dict] = None

class ConfigResponse(BaseModel):
    id: int
    bot_id: int
    chat_id: str
    chat_name: Optional[str] = None
    chat_type: Optional[str] = None
    welcome_message: Optional[str] = None
    commands: Optional[dict] = None
    responses: Optional[dict] = None
    filters: Optional[dict] = None
    permissions: Optional[dict] = None
    message_count: int
    last_activity: Optional[str] = None
    created_at: str
    updated_at: str
    
    class Config:
        from_attributes = True

class TemplateResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    platform: str
    config_schema: Optional[dict] = None
    default_config: Optional[dict] = None
    is_public: bool
    created_at: str
    
    class Config:
        from_attributes = True

@router.get("/templates", response_model=List[TemplateResponse])
async def get_bot_templates(
    platform: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Получение шаблонов ботов"""
    try:
        query = db.query(BotTemplate)
        
        if platform:
            query = query.filter(BotTemplate.platform == platform)
        
        templates = query.filter(BotTemplate.is_public == True).all()
        
        return [
            TemplateResponse(
                id=template.id,
                name=template.name,
                description=template.description,
                platform=template.platform,
                config_schema=template.config_schema,
                default_config=template.default_config,
                is_public=template.is_public,
                created_at=template.created_at.isoformat()
            )
            for template in templates
        ]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка получения шаблонов: {str(e)}"
        )

@router.get("/templates/{template_id}", response_model=TemplateResponse)
async def get_bot_template(
    template_id: int,
    db: Session = Depends(get_db)
):
    """Получение конкретного шаблона бота"""
    try:
        template = db.query(BotTemplate).filter(BotTemplate.id == template_id).first()
        
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Шаблон не найден"
            )
        
        return TemplateResponse(
            id=template.id,
            name=template.name,
            description=template.description,
            platform=template.platform,
            config_schema=template.config_schema,
            default_config=template.default_config,
            is_public=template.is_public,
            created_at=template.created_at.isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка получения шаблона: {str(e)}"
        )

@router.post("/templates/{template_id}/apply")
async def apply_template(
    template_id: int,
    bot_id: int,
    chat_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth.get_current_user)
):
    """Применение шаблона к боту"""
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
        
        # Получаем шаблон
        template = db.query(BotTemplate).filter(BotTemplate.id == template_id).first()
        
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Шаблон не найден"
            )
        
        # Проверяем совместимость платформ
        if template.platform != bot.platform:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Шаблон не совместим с платформой бота"
            )
        
        # Получаем или создаем конфигурацию
        config = db.query(BotConfig).filter(
            BotConfig.bot_id == bot_id,
            BotConfig.chat_id == chat_id
        ).first()
        
        if not config:
            config = BotConfig(
                bot_id=bot_id,
                user_id=current_user.id,
                chat_id=chat_id
            )
            db.add(config)
        
        # Применяем настройки из шаблона
        if template.default_config:
            if template.default_config.get("welcome_message"):
                config.welcome_message = template.default_config["welcome_message"]
            if template.default_config.get("auto_responses"):
                config.responses = template.default_config["auto_responses"]
            if template.default_config.get("blocked_words"):
                config.filters = {"blocked_words": template.default_config["blocked_words"]}
        
        db.commit()
        
        return {"message": "Шаблон успешно применен"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка применения шаблона: {str(e)}"
        )

@router.get("/bots/{bot_id}/chats", response_model=List[ConfigResponse])
async def get_bot_chats(
    bot_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth.get_current_user)
):
    """Получение всех чатов бота"""
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
        
        # Получаем конфигурации чатов
        configs = db.query(BotConfig).filter(BotConfig.bot_id == bot_id).all()
        
        return [
            ConfigResponse(
                id=config.id,
                bot_id=config.bot_id,
                chat_id=config.chat_id,
                chat_name=config.chat_name,
                chat_type=config.chat_type,
                welcome_message=config.welcome_message,
                commands=config.commands,
                responses=config.responses,
                filters=config.filters,
                permissions=config.permissions,
                message_count=config.message_count,
                last_activity=config.last_activity.isoformat() if config.last_activity else None,
                created_at=config.created_at.isoformat(),
                updated_at=config.updated_at.isoformat()
            )
            for config in configs
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка получения чатов: {str(e)}"
        )

@router.get("/bots/{bot_id}/chats/{chat_id}", response_model=ConfigResponse)
async def get_chat_config(
    bot_id: int,
    chat_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth.get_current_user)
):
    """Получение конфигурации конкретного чата"""
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
        
        # Получаем конфигурацию чата
        config = db.query(BotConfig).filter(
            BotConfig.bot_id == bot_id,
            BotConfig.chat_id == chat_id
        ).first()
        
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Конфигурация чата не найдена"
            )
        
        return ConfigResponse(
            id=config.id,
            bot_id=config.bot_id,
            chat_id=config.chat_id,
            chat_name=config.chat_name,
            chat_type=config.chat_type,
            welcome_message=config.welcome_message,
            commands=config.commands,
            responses=config.responses,
            filters=config.filters,
            permissions=config.permissions,
            message_count=config.message_count,
            last_activity=config.last_activity.isoformat() if config.last_activity else None,
            created_at=config.created_at.isoformat(),
            updated_at=config.updated_at.isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка получения конфигурации: {str(e)}"
        )

@router.put("/bots/{bot_id}/chats/{chat_id}")
async def update_chat_config(
    bot_id: int,
    chat_id: str,
    config_data: ConfigUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth.get_current_user)
):
    """Обновление конфигурации чата"""
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

@router.delete("/bots/{bot_id}/chats/{chat_id}")
async def delete_chat_config(
    bot_id: int,
    chat_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth.get_current_user)
):
    """Удаление конфигурации чата"""
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
        
        # Получаем конфигурацию
        config = db.query(BotConfig).filter(
            BotConfig.bot_id == bot_id,
            BotConfig.chat_id == chat_id
        ).first()
        
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Конфигурация чата не найдена"
            )
        
        # Удаляем конфигурацию
        db.delete(config)
        db.commit()
        
        return {"message": "Конфигурация чата удалена"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка удаления конфигурации: {str(e)}"
        )

@router.post("/bots/{bot_id}/chats/{chat_id}/reset")
async def reset_chat_config(
    bot_id: int,
    chat_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth.get_current_user)
):
    """Сброс конфигурации чата к значениям по умолчанию"""
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
        
        # Получаем конфигурацию
        config = db.query(BotConfig).filter(
            BotConfig.bot_id == bot_id,
            BotConfig.chat_id == chat_id
        ).first()
        
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Конфигурация чата не найдена"
            )
        
        # Сбрасываем настройки
        config.welcome_message = None
        config.commands = None
        config.responses = None
        config.filters = None
        config.permissions = None
        
        db.commit()
        
        return {"message": "Конфигурация сброшена к значениям по умолчанию"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка сброса конфигурации: {str(e)}"
        )

@router.post("/bots/{bot_id}/chats/{chat_id}/export")
async def export_chat_config(
    bot_id: int,
    chat_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth.get_current_user)
):
    """Экспорт конфигурации чата"""
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
        
        # Получаем конфигурацию
        config = db.query(BotConfig).filter(
            BotConfig.bot_id == bot_id,
            BotConfig.chat_id == chat_id
        ).first()
        
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Конфигурация чата не найдена"
            )
        
        # Формируем данные для экспорта
        export_data = {
            "bot_name": bot.name,
            "platform": bot.platform,
            "chat_id": config.chat_id,
            "chat_name": config.chat_name,
            "chat_type": config.chat_type,
            "welcome_message": config.welcome_message,
            "commands": config.commands,
            "responses": config.responses,
            "filters": config.filters,
            "permissions": config.permissions,
            "exported_at": config.updated_at.isoformat()
        }
        
        return export_data
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка экспорта: {str(e)}"
        )