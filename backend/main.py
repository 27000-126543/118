from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

from backend.config import settings
from backend.database import engine, Base
from backend.api import auth, simulations, monitoring, reports, approvals

Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    from backend.database import SessionLocal
    db = SessionLocal()

    from backend.models import User, UserRole
    existing = db.query(User).filter(User.role == UserRole.ADMIN).first()
    if not existing:
        from backend.auth import get_password_hash
        admin = User(
            username="admin",
            email="admin@geodynamo.edu",
            full_name="System Administrator",
            role=UserRole.ADMIN,
            hashed_password=get_password_hash("admin123")
        )
        db.add(admin)

        users = [
            User(username="postdoc1", email="postdoc1@geodynamo.edu", full_name="张博士后",
                 role=UserRole.POSTDOC, hashed_password=get_password_hash("postdoc123")),
            User(username="professor1", email="professor1@geodynamo.edu", full_name="李教授",
                 role=UserRole.PROFESSOR, hashed_password=get_password_hash("professor123")),
            User(username="geophysicist1", email="geo1@geodynamo.edu", full_name="王地磁学家",
                 role=UserRole.GEOPHYSICIST, hashed_password=get_password_hash("geo123")),
            User(username="chief1", email="chief@geodynamo.edu", full_name="陈首席科学家",
                 role=UserRole.CHIEF_SCIENTIST, hashed_password=get_password_hash("chief123")),
            User(username="researcher1", email="researcher1@geodynamo.edu", full_name="刘研究员",
                 role=UserRole.RESEARCHER, hashed_password=get_password_hash("researcher123")),
        ]
        for user in users:
            db.add(user)

        db.commit()

    db.close()
    yield

    db.close()


app = FastAPI(
    title="地核多物理场耦合模拟与地磁场长期演化预测平台",
    description="Geodynamo Multi-Physics Coupling Simulation and Geomagnetic Field Long-term Evolution Prediction Platform",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(simulations.router, prefix="/api")
app.include_router(monitoring.router, prefix="/api")
app.include_router(reports.router, prefix="/api")
app.include_router(approvals.router, prefix="/api")

app.mount("/static", StaticFiles(directory=settings.REPORT_DIR), name="reports")
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")
app.mount("/outputs", StaticFiles(directory=settings.OUTPUT_DIR), name="outputs")


@app.get("/")
async def root():
    return {
        "message": "地核多物理场耦合模拟与地磁场长期演化预测平台 API",
        "version": "1.0.0",
        "docs": "/docs",
        "api_endpoints": [
            "/api/auth/*",
            "/api/simulations/*",
            "/api/monitoring/*",
            "/api/reports/*",
            "/api/approvals/*",
            "/api/statistics/*"
        ],
        "default_credentials": {
            "admin": "admin / admin123",
            "postdoc": "postdoc1 / postdoc123",
            "professor": "professor1 / professor123",
            "geophysicist": "geophysicist1 / geo123",
            "chief_scientist": "chief1 / chief123",
            "researcher": "researcher1 / researcher123"
        }
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": settings.ensure_dirs()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
