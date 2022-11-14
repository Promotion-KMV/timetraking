import os

from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    file_state = Field(os.path.dirname(os.path.abspath(__file__))+"/meeting_time.json")

settings = Settings()