import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///app.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Stripe API Keys
    STRIPE_ACCOUNT_1_KEY = os.environ.get('STRIPE_ACCOUNT_1_KEY')
    STRIPE_ACCOUNT_2_KEY = os.environ.get('STRIPE_ACCOUNT_2_KEY')
    STRIPE_ACCOUNT_3_KEY = os.environ.get('STRIPE_ACCOUNT_3_KEY')
    
    @staticmethod
    def init_app(app):
        pass