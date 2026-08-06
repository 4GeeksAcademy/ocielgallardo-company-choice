from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from services.app.routers.incidents import router as incidents_router
from services.app.routers.suppliers import router as suppliers_router
from services.app.routers.users import router as users_router



app = FastAPI(title="HealthCore API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(incidents_router)
app.include_router(suppliers_router)
app.include_router(users_router)