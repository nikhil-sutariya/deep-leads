"""
FastAPI Main Application
DeepLeads AI - Intelligent Lead Generation & Outreach System
"""
import sys
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from app.core.lifespan import lifespan
from app.core.config import get_settings
from app.api import leads, campaigns, auth, enums, dashboard, tracking

# Configure logger
logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
    level="INFO"
)
logger.add(
    "logs/deepleads.log",
    rotation="500 MB",
    retention="10 days",
    level="DEBUG"
)

settings = get_settings()


# Create FastAPI app
app = FastAPI(
    title="DeepLeads AI",
    description="""
    Intelligent Lead Generation & Outreach System powered by AI
    
    ## Features
    
    * 🔍 **Smart Lead Discovery** - AI-powered lead finding with Google Search grounding
    * 📊 **Lead Enrichment** - Comprehensive intelligence gathering on prospects
    * 📧 **Personalized Campaigns** - AI-generated, highly personalized email outreach
    * 🎯 **Intelligent Filtering** - Focus on SMBs and optimal company sizes
    * 🌍 **Geographic Targeting** - Tier-based regional strategies
    * 📈 **Campaign Analytics** - Track opens, clicks, responses, and conversions
    
    ## Workflow
    
    1. **Discover Leads** - Search for companies matching your criteria
    2. **Enrich Data** - Gather intelligence on pain points, decision makers, and opportunities
    3. **Create Campaign** - Generate personalized emails for each lead
    4. **Launch & Track** - Send emails and monitor performance
    
    ## Getting Started
    
    1. Configure your API keys in `.env` file
    2. Use `/api/v1/auth/login` to login
    3. Use `/api/v1/leads/discover` to find leads
    4. Use `/api/v1/leads/{id}/enrich` to gather intelligence
    5. Use `/api/v1/campaigns` to create and launch campaigns
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, tags=['Auth'], prefix='/api/v1/auth')
app.include_router(campaigns.router, tags=['Campaigns'], prefix='/api/v1/campaigns')
app.include_router(enums.router, tags=['Enums'], prefix='/api/v1/enums')
app.include_router(leads.router, tags=['Leads'], prefix='/api/v1/leads')
app.include_router(dashboard.router, tags=['Dashboard'], prefix='/api/v1/dashboard')
app.include_router(tracking.router, tags=['Tracking'], prefix='/track')


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "name": "DeepLeads AI",
        "version": "1.0.0",
        "description": "Intelligent Lead Generation & Outreach System",
        "docs": "/docs",
        "health": "/health",
        "endpoints": {
            "auth": "/api/v1/auth",
            "leads": "/api/v1/leads",
            "campaigns": "/api/v1/campaigns"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "environment": settings.environment,
        "version": "1.0.0"
    }


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error": str(exc) if settings.environment == "development" else "An error occurred"
        }
    )


if __name__ == "__main__":
    import uvicorn
    
    logger.info("Starting server...")
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.environment == "development",
        log_level="info"
    )

