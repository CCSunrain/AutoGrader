"""Aggregate all API routers."""
from fastapi import APIRouter

from app.api import auth, courses, health, reviews, rubrics, submissions

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(courses.router)
api_router.include_router(rubrics.router)
api_router.include_router(submissions.router)
api_router.include_router(reviews.router)
