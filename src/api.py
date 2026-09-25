from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .models import MinimalSource
from .search import Search


class SearchRequest(BaseModel):