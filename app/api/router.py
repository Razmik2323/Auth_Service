from fastapi import APIRouter

from app.api.v1 import admin, auth, business, users

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(admin.router)
api_router.include_router(business.router)
