import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Flask
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key')

    # OAuth2
    GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')

    # URLs
    BASE_URL = os.getenv('NGROK_URL', 'http://localhost:5000')

    # Определяем redirect URI динамически
    @property
    def GOOGLE_REDIRECT_URI(self):
        return f"{self.BASE_URL}/auth/callback"