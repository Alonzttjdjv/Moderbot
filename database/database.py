from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
import os
from typing import Generator
import yaml

from .models import Base

# Загружаем конфигурацию
def load_config():
    """Загрузка конфигурации из файла"""
    config_path = "config/config.yaml"
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as file:
            return yaml.safe_load(file)
    return {}

config = load_config()

# Настройки базы данных
DATABASE_URL = os.getenv("DATABASE_URL", config.get("database", {}).get("url", "sqlite:///./bot_platform.db"))

# Создаем движок базы данных
engine = create_engine(
    DATABASE_URL,
    echo=config.get("database", {}).get("echo", False),
    pool_pre_ping=True
)

# Создаем фабрику сессий
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db() -> Generator[Session, None, None]:
    """Получение сессии базы данных"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def init_db():
    """Инициализация базы данных"""
    try:
        # Создаем все таблицы
        Base.metadata.create_all(bind=engine)
        print("База данных инициализирована успешно")
    except Exception as e:
        print(f"Ошибка инициализации БД: {e}")
        raise

def create_tables():
    """Создание таблиц (синхронная версия)"""
    try:
        Base.metadata.create_all(bind=engine)
        print("Таблицы созданы успешно")
    except Exception as e:
        print(f"Ошибка создания таблиц: {e}")
        raise

def drop_tables():
    """Удаление всех таблиц"""
    try:
        Base.metadata.drop_all(bind=engine)
        print("Таблицы удалены успешно")
    except Exception as e:
        print(f"Ошибка удаления таблиц: {e}")
        raise

# Функции для работы с пользователями
def create_user(username: str, email: str, password_hash: str) -> bool:
    """Создание нового пользователя"""
    from .models import User
    
    db = SessionLocal()
    try:
        # Проверяем, существует ли пользователь
        existing_user = db.query(User).filter(
            (User.username == username) | (User.email == email)
        ).first()
        
        if existing_user:
            print("Пользователь с таким именем или email уже существует")
            return False
        
        # Создаем нового пользователя
        new_user = User(
            username=username,
            email=email,
            password_hash=password_hash
        )
        
        db.add(new_user)
        db.commit()
        print(f"Пользователь {username} создан успешно")
        return True
        
    except Exception as e:
        print(f"Ошибка создания пользователя: {e}")
        db.rollback()
        return False
    finally:
        db.close()

def get_user_by_username(username: str):
    """Получение пользователя по имени"""
    from .models import User
    
    db = SessionLocal()
    try:
        return db.query(User).filter(User.username == username).first()
    finally:
        db.close()

def get_user_by_email(email: str):
    """Получение пользователя по email"""
    from .models import User
    
    db = SessionLocal()
    try:
        return db.query(User).filter(User.email == email).first()
    finally:
        db.close()

# Функции для работы с ботами
def create_bot(user_id: int, name: str, platform: str, token: str):
    """Создание нового бота"""
    from .models import Bot
    
    db = SessionLocal()
    try:
        new_bot = Bot(
            user_id=user_id,
            name=name,
            platform=platform,
            token=token
        )
        
        db.add(new_bot)
        db.commit()
        print(f"Бот {name} создан успешно")
        return new_bot
        
    except Exception as e:
        print(f"Ошибка создания бота: {e}")
        db.rollback()
        return None
    finally:
        db.close()

def get_user_bots(user_id: int):
    """Получение всех ботов пользователя"""
    from .models import Bot
    
    db = SessionLocal()
    try:
        return db.query(Bot).filter(Bot.user_id == user_id).all()
    finally:
        db.close()

def get_bot_by_id(bot_id: int):
    """Получение бота по ID"""
    from .models import Bot
    
    db = SessionLocal()
    try:
        return db.query(Bot).filter(Bot.id == bot_id).first()
    finally:
        db.close()

# Функции для работы с конфигурациями
def create_bot_config(bot_id: int, user_id: int, chat_id: str, chat_name: str = None):
    """Создание конфигурации бота для чата"""
    from .models import BotConfig
    
    db = SessionLocal()
    try:
        new_config = BotConfig(
            bot_id=bot_id,
            user_id=user_id,
            chat_id=chat_id,
            chat_name=chat_name
        )
        
        db.add(new_config)
        db.commit()
        print(f"Конфигурация для чата {chat_id} создана успешно")
        return new_config
        
    except Exception as e:
        print(f"Ошибка создания конфигурации: {e}")
        db.rollback()
        return None
    finally:
        db.close()

def get_bot_config(bot_id: int, chat_id: str):
    """Получение конфигурации бота для чата"""
    from .models import BotConfig
    
    db = SessionLocal()
    try:
        return db.query(BotConfig).filter(
            BotConfig.bot_id == bot_id,
            BotConfig.chat_id == chat_id
        ).first()
    finally:
        db.close()

def update_bot_config(bot_id: int, chat_id: str, config_data: dict) -> bool:
    """Обновление конфигурации бота"""
    from .models import BotConfig
    
    db = SessionLocal()
    try:
        config = db.query(BotConfig).filter(
            BotConfig.bot_id == bot_id,
            BotConfig.chat_id == chat_id
        ).first()
        
        if not config:
            return False
        
        # Обновляем настройки
        for key, value in config_data.items():
            if hasattr(config, key):
                setattr(config, key, value)
        
        db.commit()
        return True
        
    except Exception as e:
        print(f"Ошибка обновления конфигурации: {e}")
        db.rollback()
        return False
    finally:
        db.close()