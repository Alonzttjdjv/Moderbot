from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class User(Base):
    """Пользователь платформы"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, index=True)
    email = Column(String(255), unique=True, index=True)
    password_hash = Column(String(255))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Связи
    bots = relationship("Bot", back_populates="owner")
    bot_configs = relationship("BotConfig", back_populates="user")

class Bot(Base):
    """Бот пользователя"""
    __tablename__ = "bots"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String(100), nullable=False)
    platform = Column(String(50), nullable=False)  # telegram, discord, vk
    token = Column(String(500), nullable=False)
    webhook_url = Column(String(500))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Связи
    owner = relationship("User", back_populates="bots")
    configs = relationship("BotConfig", back_populates="bot")

class BotConfig(Base):
    """Конфигурация бота для конкретного чата/сервера"""
    __tablename__ = "bot_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    bot_id = Column(Integer, ForeignKey("bots.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    chat_id = Column(String(100), nullable=False)  # ID чата/сервера
    chat_name = Column(String(200))
    chat_type = Column(String(50))  # group, private, channel
    
    # Настройки бота
    welcome_message = Column(Text)
    commands = Column(JSON)  # Кастомные команды
    responses = Column(JSON)  # Автоответы
    filters = Column(JSON)  # Фильтры сообщений
    permissions = Column(JSON)  # Права доступа
    
    # Статистика
    message_count = Column(Integer, default=0)
    last_activity = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Связи
    bot = relationship("Bot", back_populates="configs")
    user = relationship("User", back_populates="bot_configs")

class BotTemplate(Base):
    """Шаблоны ботов для быстрого создания"""
    __tablename__ = "bot_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    platform = Column(String(50), nullable=False)
    config_schema = Column(JSON)  # Схема конфигурации
    default_config = Column(JSON)  # Конфигурация по умолчанию
    is_public = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)