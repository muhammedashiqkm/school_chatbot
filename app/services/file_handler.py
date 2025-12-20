import os
import aiofiles
from fastapi import UploadFile
from app.config import settings

class FileHandler:
    @staticmethod
    async def save_upload(file: UploadFile, file_name: str) -> str:
        """
        Saves an UploadFile to disk asynchronously to avoid blocking the event loop.
        Returns the absolute path.
        """
        if not os.path.exists(settings.UPLOAD_FOLDER):
            os.makedirs(settings.UPLOAD_FOLDER)

        file_path = os.path.join(settings.UPLOAD_FOLDER, file_name)
        
        async with aiofiles.open(file_path, "wb") as buffer:
            while content := await file.read(1024 * 1024):
                await buffer.write(content)
                
        return file_path

    @staticmethod
    def delete_file(file_path: str):
        """Synchronous deletion is generally fine for OS operations."""
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError as e:
                print(f"Error deleting file {file_path}: {e}")