from pydantic import BaseModel
from typing import List

class RequestSchema(BaseModel):
    documents: str
    questions: List[str]