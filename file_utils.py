import os
import json
import shutil
import logging
import asyncio
import aiofiles
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Any
from pathlib import Path
import sqlite3
import zipfile
import tempfile

from config import (
    BACKUP_ENABLED, BACKUP_INTERVAL_HOURS, BACKUP_RETENTION_DAYS, 
    BACKUP_PATH, DATABASE_PATH
)
from utils import create_backup_filename, safe_json_dumps, safe_json_loads

logger = logging.getLogger(__name__)

class FileManager:
    """Класс для управления файлами и резервными копиями"""
    
    def __init__(self):
        self.backup_path = Path(BACKUP_PATH)
        self.backup_path.mkdir(parents=True, exist_ok=True)
        self.last_backup = None
        
    async def create_backup(self, backup_type: str = "full") -> Optional[str]:
        """Создание резервной копии"""
        try:
            if not BACKUP_ENABLED:
                logger.info("Создание резервных копий отключено")
                return None
            
            timestamp = datetime.now()
            backup_filename = create_backup_filename(f"{backup_type}_backup")
            backup_filepath = self.backup_path / backup_filename
            
            if backup_type == "full":
                success = await self._create_full_backup(backup_filepath)
            elif backup_type == "database":
                success = await self._create_database_backup(backup_filepath)
            elif backup_type == "config":
                success = await self._create_config_backup(backup_filepath)
            else:
                logger.error(f"Неизвестный тип резервной копии: {backup_type}")
                return None
            
            if success:
                self.last_backup = timestamp
                logger.info(f"Резервная копия создана: {backup_filename}")
                return str(backup_filepath)
            else:
                logger.error("Ошибка создания резервной копии")
                return None
                
        except Exception as e:
            logger.error(f"Ошибка создания резервной копии: {e}")
            return None
    
    async def _create_full_backup(self, backup_filepath: Path) -> bool:
        """Создание полной резервной копии"""
        try:
            # Создаем временную директорию
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # Копируем базу данных
                if os.path.exists(DATABASE_PATH):
                    db_backup_path = temp_path / "database.db"
                    shutil.copy2(DATABASE_PATH, db_backup_path)
                
                # Копируем конфигурационные файлы
                config_files = ["config.py", ".env"]
                for config_file in config_files:
                    if os.path.exists(config_file):
                        shutil.copy2(config_file, temp_path / config_file)
                
                # Создаем ZIP архив
                with zipfile.ZipFile(backup_filepath, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for file_path in temp_path.rglob('*'):
                        if file_path.is_file():
                            arcname = file_path.relative_to(temp_path)
                            zipf.write(file_path, arcname)
                
                return True
                
        except Exception as e:
            logger.error(f"Ошибка создания полной резервной копии: {e}")
            return False
    
    async def _create_database_backup(self, backup_filepath: Path) -> bool:
        """Создание резервной копии базы данных"""
        try:
            if not os.path.exists(DATABASE_PATH):
                logger.warning("Файл базы данных не найден")
                return False
            
            # Создаем резервную копию SQLite
            with sqlite3.connect(DATABASE_PATH) as source_conn:
                with sqlite3.connect(backup_filepath) as backup_conn:
                    source_conn.backup(backup_conn)
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка создания резервной копии БД: {e}")
            return False
    
    async def _create_config_backup(self, backup_filepath: Path) -> bool:
        """Создание резервной копии конфигурации"""
        try:
            config_data = {}
            
            # Читаем конфигурационные файлы
            config_files = ["config.py", ".env"]
            for config_file in config_files:
                if os.path.exists(config_file):
                    try:
                        with open(config_file, 'r', encoding='utf-8') as f:
                            config_data[config_file] = f.read()
                    except Exception as e:
                        logger.warning(f"Не удалось прочитать {config_file}: {e}")
            
            # Сохраняем в JSON
            with open(backup_filepath, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, ensure_ascii=False, indent=2)
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка создания резервной копии конфигурации: {e}")
            return False
    
    async def restore_backup(self, backup_filepath: str, restore_type: str = "auto") -> bool:
        """Восстановление из резервной копии"""
        try:
            backup_path = Path(backup_filepath)
            if not backup_path.exists():
                logger.error(f"Файл резервной копии не найден: {backup_filepath}")
                return False
            
            # Определяем тип резервной копии
            if restore_type == "auto":
                if backup_path.suffix == '.zip':
                    restore_type = "full"
                elif backup_path.suffix == '.db':
                    restore_type = "database"
                else:
                    restore_type = "config"
            
            if restore_type == "full":
                success = await self._restore_full_backup(backup_path)
            elif restore_type == "database":
                success = await self._restore_database_backup(backup_path)
            elif restore_type == "config":
                success = await self._restore_config_backup(backup_path)
            else:
                logger.error(f"Неизвестный тип восстановления: {restore_type}")
                return False
            
            if success:
                logger.info(f"Резервная копия восстановлена: {backup_filepath}")
            
            return success
            
        except Exception as e:
            logger.error(f"Ошибка восстановления резервной копии: {e}")
            return False
    
    async def _restore_full_backup(self, backup_path: Path) -> bool:
        """Восстановление полной резервной копии"""
        try:
            # Создаем временную директорию
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # Распаковываем ZIP
                with zipfile.ZipFile(backup_path, 'r') as zipf:
                    zipf.extractall(temp_path)
                
                # Восстанавливаем базу данных
                db_backup = temp_path / "database.db"
                if db_backup.exists():
                    # Создаем резервную копию текущей БД
                    current_backup = f"{DATABASE_PATH}.backup.{int(datetime.now().timestamp())}"
                    if os.path.exists(DATABASE_PATH):
                        shutil.copy2(DATABASE_PATH, current_backup)
                    
                    # Восстанавливаем БД
                    shutil.copy2(db_backup, DATABASE_PATH)
                
                # Восстанавливаем конфигурационные файлы
                config_files = ["config.py", ".env"]
                for config_file in config_files:
                    config_backup = temp_path / config_file
                    if config_backup.exists():
                        # Создаем резервную копию текущего файла
                        current_backup = f"{config_file}.backup.{int(datetime.now().timestamp())}"
                        if os.path.exists(config_file):
                            shutil.copy2(config_file, current_backup)
                        
                        # Восстанавливаем файл
                        shutil.copy2(config_backup, config_file)
                
                return True
                
        except Exception as e:
            logger.error(f"Ошибка восстановления полной резервной копии: {e}")
            return False
    
    async def _restore_database_backup(self, backup_path: Path) -> bool:
        """Восстановление базы данных"""
        try:
            # Создаем резервную копию текущей БД
            current_backup = f"{DATABASE_PATH}.backup.{int(datetime.now().timestamp())}"
            if os.path.exists(DATABASE_PATH):
                shutil.copy2(DATABASE_PATH, current_backup)
            
            # Восстанавливаем БД
            shutil.copy2(backup_path, DATABASE_PATH)
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка восстановления БД: {e}")
            return False
    
    async def _restore_config_backup(self, backup_path: Path) -> bool:
        """Восстановление конфигурации"""
        try:
            with open(backup_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            for filename, content in config_data.items():
                # Создаем резервную копию текущего файла
                if os.path.exists(filename):
                    current_backup = f"{filename}.backup.{int(datetime.now().timestamp())}"
                    shutil.copy2(filename, current_backup)
                
                # Восстанавливаем файл
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(content)
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка восстановления конфигурации: {e}")
            return False
    
    async def cleanup_old_backups(self) -> int:
        """Очистка старых резервных копий"""
        try:
            if not BACKUP_ENABLED:
                return 0
            
            cutoff_date = datetime.now() - timedelta(days=BACKUP_RETENTION_DAYS)
            deleted_count = 0
            
            for backup_file in self.backup_path.glob("*"):
                if backup_file.is_file():
                    # Получаем время создания файла
                    file_time = datetime.fromtimestamp(backup_file.stat().st_mtime)
                    
                    if file_time < cutoff_date:
                        try:
                            backup_file.unlink()
                            deleted_count += 1
                            logger.info(f"Удалена старая резервная копия: {backup_file.name}")
                        except Exception as e:
                            logger.warning(f"Не удалось удалить {backup_file.name}: {e}")
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"Ошибка очистки старых резервных копий: {e}")
            return 0
    
    async def get_backup_info(self) -> Dict[str, Any]:
        """Получение информации о резервных копиях"""
        try:
            backup_files = list(self.backup_path.glob("*"))
            backup_info = {
                'total_backups': len(backup_files),
                'backup_path': str(self.backup_path),
                'last_backup': self.last_backup.isoformat() if self.last_backup else None,
                'backups': []
            }
            
            for backup_file in backup_files:
                if backup_file.is_file():
                    file_stat = backup_file.stat()
                    backup_info['backups'].append({
                        'filename': backup_file.name,
                        'size': file_stat.st_size,
                        'created': datetime.fromtimestamp(file_stat.st_mtime).isoformat(),
                        'type': self._detect_backup_type(backup_file)
                    })
            
            # Сортируем по времени создания
            backup_info['backups'].sort(key=lambda x: x['created'], reverse=True)
            
            return backup_info
            
        except Exception as e:
            logger.error(f"Ошибка получения информации о резервных копиях: {e}")
            return {}
    
    def _detect_backup_type(self, file_path: Path) -> str:
        """Определение типа резервной копии по расширению"""
        if file_path.suffix == '.zip':
            return 'full'
        elif file_path.suffix == '.db':
            return 'database'
        else:
            return 'config'
    
    async def export_data(self, export_type: str, filepath: str) -> bool:
        """Экспорт данных в различные форматы"""
        try:
            if export_type == "json":
                return await self._export_to_json(filepath)
            elif export_type == "csv":
                return await self._export_to_csv(filepath)
            elif export_type == "sql":
                return await self._export_to_sql(filepath)
            else:
                logger.error(f"Неизвестный тип экспорта: {export_type}")
                return False
                
        except Exception as e:
            logger.error(f"Ошибка экспорта данных: {e}")
            return False
    
    async def _export_to_json(self, filepath: str) -> bool:
        """Экспорт данных в JSON"""
        try:
            # Здесь можно добавить логику экспорта данных из БД
            export_data = {
                'export_date': datetime.now().isoformat(),
                'export_type': 'json',
                'data': {}
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка экспорта в JSON: {e}")
            return False
    
    async def _export_to_csv(self, filepath: str) -> bool:
        """Экспорт данных в CSV"""
        try:
            # Здесь можно добавить логику экспорта данных из БД
            import csv
            
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['export_date', 'export_type'])
                writer.writerow([datetime.now().isoformat(), 'csv'])
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка экспорта в CSV: {e}")
            return False
    
    async def _export_to_sql(self, filepath: str) -> bool:
        """Экспорт данных в SQL"""
        try:
            # Здесь можно добавить логику экспорта данных из БД
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"-- Экспорт данных от {datetime.now().isoformat()}\n")
                f.write("-- Здесь будут SQL команды для восстановления данных\n")
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка экспорта в SQL: {e}")
            return False
    
    async def validate_file_integrity(self, filepath: str) -> Dict[str, Any]:
        """Проверка целостности файла"""
        try:
            file_path = Path(filepath)
            if not file_path.exists():
                return {'valid': False, 'error': 'Файл не найден'}
            
            file_stat = file_path.stat()
            
            # Проверяем размер файла
            if file_stat.st_size == 0:
                return {'valid': False, 'error': 'Файл пустой'}
            
            # Проверяем права доступа
            if not os.access(filepath, os.R_OK):
                return {'valid': False, 'error': 'Нет прав на чтение файла'}
            
            # Проверяем тип файла
            file_type = self._detect_file_type(file_path)
            
            return {
                'valid': True,
                'size': file_stat.st_size,
                'type': file_type,
                'created': datetime.fromtimestamp(file_stat.st_ctime).isoformat(),
                'modified': datetime.fromtimestamp(file_stat.st_mtime).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Ошибка проверки целостности файла: {e}")
            return {'valid': False, 'error': str(e)}
    
    def _detect_file_type(self, file_path: Path) -> str:
        """Определение типа файла"""
        if file_path.suffix == '.db':
            return 'sqlite_database'
        elif file_path.suffix == '.zip':
            return 'zip_archive'
        elif file_path.suffix == '.json':
            return 'json_data'
        elif file_path.suffix == '.py':
            return 'python_script'
        elif file_path.suffix == '.env':
            return 'environment_config'
        else:
            return 'unknown'
    
    async def get_disk_usage(self) -> Dict[str, Any]:
        """Получение информации об использовании диска"""
        try:
            import shutil
            
            total, used, free = shutil.disk_usage(self.backup_path)
            
            return {
                'total': total,
                'used': used,
                'free': free,
                'percent_used': (used / total) * 100,
                'backup_path': str(self.backup_path),
                'backup_size': self._get_directory_size(self.backup_path)
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения информации о диске: {e}")
            return {}
    
    def _get_directory_size(self, directory: Path) -> int:
        """Получение размера директории"""
        try:
            total_size = 0
            for file_path in directory.rglob('*'):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
            return total_size
        except Exception as e:
            logger.error(f"Ошибка получения размера директории: {e}")
            return 0

# Создаем глобальный экземпляр
file_manager = FileManager()