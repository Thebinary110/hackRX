import os
from dotenv import load_dotenv
load_dotenv()

def get_env_variable(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ValueError(f"Environment variable '{name}' not set")
    return value
