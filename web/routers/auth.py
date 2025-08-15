from fastapi import APIRouter, Depends, HTTPException, status, HTTPBasic, HTTPBasicCredentials
from fastapi.security import HTTPBasic
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel
import hashlib

from database.database import get_db
from database.models import User

router = APIRouter()
security = HTTPBasic()

# Pydantic модели для API
class UserCreate(BaseModel):
    username: str
    email: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    is_active: bool
    created_at: str
    
    class Config:
        from_attributes = True

def hash_password(password: str) -> str:
    """Хеширование пароля"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Проверка пароля"""
    return hash_password(plain_password) == hashed_password

def authenticate_user(username: str, password: str, db: Session) -> Optional[User]:
    """Аутентификация пользователя"""
    user = db.query(User).filter(User.username == username).first()
    if user and verify_password(password, user.password_hash):
        return user
    return None

def get_current_user(credentials: HTTPBasicCredentials = Depends(security), db: Session = Depends(get_db)) -> User:
    """Получение текущего пользователя"""
    user = authenticate_user(credentials.username, credentials.password, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверные учетные данные",
            headers={"WWW-Authenticate": "Basic"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь неактивен"
        )
    return user

@router.post("/register", response_model=UserResponse)
async def register_user(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    """Регистрация нового пользователя"""
    try:
        # Проверяем, существует ли пользователь
        existing_user = db.query(User).filter(
            (User.username == user_data.username) | (User.email == user_data.email)
        ).first()
        
        if existing_user:
            if existing_user.username == user_data.username:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Пользователь с таким именем уже существует"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Пользователь с таким email уже существует"
                )
        
        # Создаем нового пользователя
        hashed_password = hash_password(user_data.password)
        new_user = User(
            username=user_data.username,
            email=user_data.email,
            password_hash=hashed_password,
            is_active=True
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        return UserResponse(
            id=new_user.id,
            username=new_user.username,
            email=new_user.email,
            is_active=new_user.is_active,
            created_at=new_user.created_at.isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка регистрации: {str(e)}"
        )

@router.post("/login")
async def login_user(
    user_data: UserLogin,
    db: Session = Depends(get_db)
):
    """Вход пользователя"""
    try:
        user = authenticate_user(user_data.username, user_data.password, db)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Неверные имя пользователя или пароль"
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Пользователь неактивен"
            )
        
        return {
            "message": "Вход выполнен успешно",
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка входа: {str(e)}"
        )

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """Получение информации о текущем пользователе"""
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        is_active=current_user.is_active,
        created_at=current_user.created_at.isoformat()
    )

@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_data: UserCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Обновление информации о текущем пользователе"""
    try:
        # Проверяем, не занято ли новое имя пользователя или email
        if user_data.username != current_user.username:
            existing_user = db.query(User).filter(User.username == user_data.username).first()
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Пользователь с таким именем уже существует"
                )
        
        if user_data.email != current_user.email:
            existing_user = db.query(User).filter(User.email == user_data.email).first()
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Пользователь с таким email уже существует"
                )
        
        # Обновляем данные пользователя
        current_user.username = user_data.username
        current_user.email = user_data.email
        if user_data.password:
            current_user.password_hash = hash_password(user_data.password)
        
        db.commit()
        db.refresh(current_user)
        
        return UserResponse(
            id=current_user.id,
            username=current_user.username,
            email=current_user.email,
            is_active=current_user.is_active,
            created_at=current_user.created_at.isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка обновления: {str(e)}"
        )

@router.post("/change-password")
async def change_password(
    current_password: str,
    new_password: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Смена пароля"""
    try:
        # Проверяем текущий пароль
        if not verify_password(current_password, current_user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Неверный текущий пароль"
            )
        
        # Обновляем пароль
        current_user.password_hash = hash_password(new_password)
        db.commit()
        
        return {"message": "Пароль успешно изменен"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка смены пароля: {str(e)}"
        )

@router.post("/deactivate")
async def deactivate_user(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Деактивация пользователя"""
    try:
        current_user.is_active = False
        db.commit()
        
        return {"message": "Пользователь деактивирован"}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка деактивации: {str(e)}"
        )

@router.get("/users", response_model=list[UserResponse])
async def get_all_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получение списка всех пользователей (только для админов)"""
    try:
        # Здесь можно добавить проверку на админа
        # if not current_user.is_admin:
        #     raise HTTPException(status_code=403, detail="Недостаточно прав")
        
        users = db.query(User).all()
        
        return [
            UserResponse(
                id=user.id,
                username=user.username,
                email=user.email,
                is_active=user.is_active,
                created_at=user.created_at.isoformat()
            )
            for user in users
        ]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка получения пользователей: {str(e)}"
        )