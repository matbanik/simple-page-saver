"""
FastAPI Backend for Simple Page Saver
Main application with REST API endpoints, logging, and settings management
"""

from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from contextlib import asynccontextmanager
import os
import re
import logging

from preprocessing import HTMLPreprocessor, count_tokens
from ai_converter import AIConverter, estimate_cost
from settings_manager import SettingsManager
from logging_config import setup_logging, start_queue_listener, stop_queue_listener, log_ai_request, log_ai_response
from job_manager import JobManager, Job

# Import diagnostics if enabled
try:
    ENABLE_DIAGNOSTICS = os.getenv('ENABLE_DIAGNOSTICS', 'false').lower() == 'true'
    if ENABLE_DIAGNOSTICS:
        from diagnostics import diagnostic_monitor, track_request
        logger = None  # Will be set after setup
    else:
        diagnostic_monitor = None
        track_request = None
except ImportError:
    ENABLE_DIAGNOSTICS = False
    diagnostic_monitor = None
    track_request = None

# Initialize settings
settings = SettingsManager()

# Check if logging is enabled
ENABLE_LOGGING = os.getenv('ENABLE_LOGGING', 'true').lower() == 'true'

if ENABLE_LOGGING:
    logger = setup_logging(log_level=settings.get('log_level', 'INFO'))
else:
    # Create a dummy logger that does nothing
    logger = logging.getLogger('simple_page_saver')
    logger.addHandler(logging.NullHandler())
    print("[WARNING] Logging is DISABLED - running without log files for debugging")

# Export settings as environment variables for compatibility
env_vars = settings.export_for_env()
for key, value in env_vars.items():
    os.environ[key] = value

if ENABLE_LOGGING:
    logger.info("=== Simple Page Saver Backend Starting ===")
    logger.info(f"Server Port: {settings.get('server_port')}")
    logger.info(f"Default Model: {settings.get('default_model')}")
    logger.info(f"Log Level: {settings.get('log_level')}")
    logger.info(f"API Key Configured: {bool(settings.get_api_key())}")
else:
    print("=== Simple Page Saver Backend Starting (Logging DISABLED) ===")
    print(f"Server Port: {settings.get('server_port')}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan context manager
    Handles startup and shutdown of background services like the logging queue listener
    """
    # Startup: Start the queue listener for non-blocking logging (only if logging enabled)
    if ENABLE_LOGGING:
        start_queue_listener()
        logger.info("Application startup complete - all background services running")

        if ENABLE_DIAGNOSTICS and diagnostic_monitor:
            logger.info("="*80)
            logger.info("DIAGNOSTIC MODE ENABLED")
            logger.info("Detailed request lifecycle and lock monitoring is active")
            logger.info("Performance may be impacted - disable for production")
            logger.info("="*80)
    else:
        print("Application startup complete (logging disabled)")
        if ENABLE_DIAGNOSTICS and diagnostic_monitor:
            print("="*80)
            print("DIAGNOSTIC MODE ENABLED")
            print("="*80)

    yield

    # Shutdown: Stop the queue listener and flush remaining log messages (only if logging enabled)
    if ENABLE_LOGGING:
        logger.info("Application shutting down - stopping background services...")
        stop_queue_listener()
    else:
        print("Application shutting down")


app = FastAPI(
    title="Simple Page Saver API",
    description="Backend service for converting web pages to markdown",
    lifespan=lifespan,  # Register lifespan context manager
    version="1.0.0"
)

# Enable CORS for Chrome extension
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize processors with light preprocessing mode (preserves more content)
preprocessor = HTMLPreprocessor(mode='light')
converter = AIConverter(
    api_key=settings.get_api_key(),
    model=settings.get('default_model')
)

# Initialize job manager
job_manager = JobManager(max_jobs=100, ttl_hours=24)
logger.info("Job manager initialized")

# Log diagnostic status
if ENABLE_DIAGNOSTICS and diagnostic_monitor:
    logger.warning("=" * 80)
    logger.warning("DIAGNOSTIC MODE ENABLED")
    logger.warning("Detailed request lifecycle and lock monitoring is active")
    logger.warning("Performance may be impacted - disable for production")
    logger.warning("=" * 80)


# Request/Response Models
class ProcessHTMLRequest(BaseModel):
    url: str
    html: str
    title: Optional[str] = ""
    use_ai: Optional[bool] = True
    custom_prompt: Optional[str] = ""
    extraction_mode: Optional[str] = "balanced"  # 'balanced', 'recall', 'precision'
    job_id: Optional[str] = None  # If provided, update existing job


class ProcessHTMLResponse(BaseModel):
    markdown: str
    media_urls: List[str]
    filename: str
    word_count: int
    success: bool
    used_ai: bool
    error: Optional[str] = None
    metadata: dict
    job_id: Optional[str] = None  # Job ID if job tracking is enabled


class ExtractLinksRequest(BaseModel):
    html: str
    base_url: str


class ExtractLinksResponse(BaseModel):
    internal_links: List[str]
    external_links: List[str]
    media_links: List[str]
    success: bool


class SiteMapRequest(BaseModel):
    start_url: str
    max_depth: Optional[int] = 2


class SiteMapProgressRequest(BaseModel):
    job_id: str
    discovered_count: int
    total_to_process: int
    message: Optional[str] = ""


class EstimateCostRequest(BaseModel):
    html: str
    model: Optional[str] = None


class EstimateCostResponse(BaseModel):
    estimated_input_tokens: int
    estimated_output_tokens: int
    estimated_cost_usd: float
    model: str


class JobResponse(BaseModel):
    id: str
    type: str
    status: str
    params: dict
    created_at: str
    started_at: Optional[str]
    completed_at: Optional[str]
    progress: dict
    result: Optional[dict]
    error: Optional[str]


class JobListResponse(BaseModel):
    jobs: List[dict]
    total: int


# Endpoints
@app.get("/")
async def health_check():
    """Health check endpoint"""
    logger.debug("Health check requested")
    return {
        "status": "healthy",
        "service": "Simple Page Saver API",
        "version": "1.0.0",
        "ai_enabled": bool(settings.get_api_key())
    }


@app.get("/settings")
async def get_settings():
    """Get all settings (excluding sensitive data)"""
    logger.debug("Settings requested")
    return settings.get_all_settings()


@app.post("/settings")
async def update_settings(updates: dict = Body(...)):
    """Update one or more settings"""
    logger.info(f"Updating settings: {list(updates.keys())}")

    # Update each setting
    for key, value in updates.items():
        # Skip sensitive keys that shouldn't be updated this way
        if key in ['openrouter_api_key_encrypted', '_salt']:
            logger.warning(f"Attempted to update protected setting: {key}")
            continue

        settings.set(key, value)
        logger.info(f"Updated setting: {key} = {value}")

    return {
        "status": "success",
        "updated": list(updates.keys()),
        "settings": settings.get_all_settings()
    }


@app.post("/process-html", response_model=ProcessHTMLResponse)
async def process_html(request: ProcessHTMLRequest):
    """
    Main processing endpoint: preprocess HTML and convert to markdown
    """
    import uuid
    request_id = str(uuid.uuid4())[:8]

    # Start diagnostic tracking
    if diagnostic_monitor:
        diagnostic_monitor.log_request_start("POST /process-html", request_id, {
            'url': request.url,
            'html_size': len(request.html),
            'use_ai': request.use_ai,
            'extraction_mode': request.extraction_mode
        })

    job = None
    job_id = request.job_id

    try:
        logger.info(f"[{request_id}] Processing request for URL: {request.url}")
        logger.debug(f"[{request_id}] HTML size: {len(request.html)} chars, use_ai: {request.use_ai}")

        # Create or get job if job_id provided
        if job_id:
            job = job_manager.get_job(job_id)
            if not job:
                raise HTTPException(status_code=404, detail="Job not found")
            job.start()
        else:
            # Create new job for tracking
            job = job_manager.create_job(
                job_type=Job.TYPE_SINGLE_PAGE,
                params={'url': request.url, 'title': request.title or 'Unknown'}
            )
            job.start()
            job_id = job.id
            logger.info(f"Created job: {job_id}")

        job.update_progress(0, 4, 'Preprocessing HTML...')

        # Step 1: Preprocess HTML
        cleaned_html, prep_metadata = preprocessor.preprocess(request.html, request.url)
        logger.info(f"Preprocessing complete - reduced from {prep_metadata['original_size']} to {prep_metadata['final_size']} chars ({prep_metadata.get('reduction_percentage', 0)}% reduction)")

        job.update_progress(1, 4, 'Preprocessing complete')

        # Step 2: Count tokens precisely
        token_count = count_tokens(cleaned_html)
        prep_metadata['token_count'] = token_count
        logger.debug(f"Token count: {token_count}")

        # Step 3: Extract media links
        job.update_progress(2, 4, 'Extracting links...')
        links_data = preprocessor.extract_links(request.html, request.url)
        media_urls = links_data['media_links']
        logger.debug(f"Extracted {len(media_urls)} media URLs")

        # Create converter with appropriate extraction mode
        request_converter = AIConverter(
            api_key=settings.get_api_key(),
            model=settings.get('default_model'),
            extraction_mode=request.extraction_mode
        )
        logger.info(f"Using extraction mode: {request.extraction_mode}")

        # Step 4: Convert to markdown (with automatic chunking if needed)
        # ALWAYS use convert_large_html() - it handles chunking logic internally with proper token counting
        job.update_progress(3, 4, 'Converting to markdown...')
        if not request.use_ai:
            logger.info("AI disabled by user, using Trafilatura/html2text fallback")
            log_ai_request(logger, "fallback", len(cleaned_html), {})
            markdown, used_ai, error = request_converter.convert_to_markdown(cleaned_html, request.title, "", use_ai=False)
            log_ai_response(logger, "fallback", len(markdown), False, error)
        else:
            # Always use convert_large_html() - it automatically determines if chunking is needed
            # based on precise token counts including all prompt overhead
            metadata_extra = {}
            if request.custom_prompt:
                metadata_extra['custom_prompt'] = True
                logger.info(f"Using custom prompt (length: {len(request.custom_prompt)} chars)")

            # Get chunking settings from settings manager
            worker_count = settings.get('worker_count', 4)
            overlap_percentage = settings.get('overlap_percentage', 10) / 100.0  # Convert from percentage to decimal
            extraction_strategy = settings.get('extraction_strategy', 'markdown')

            log_ai_request(logger, settings.get('default_model'), len(cleaned_html), metadata_extra)
            markdown, used_ai, error = request_converter.convert_large_html(
                cleaned_html,
                request.title,
                request.custom_prompt,
                extraction_strategy=extraction_strategy,
                worker_count=worker_count,
                overlap_percentage=overlap_percentage
            )
            log_ai_response(logger, settings.get('default_model'), len(markdown), used_ai, error)

        # Step 5: Generate filename from title or URL
        filename = _generate_filename(request.title or request.url)
        logger.debug(f"Generated filename: {filename}")

        # Step 6: Count words in markdown
        word_count = len(re.findall(r'\w+', markdown))

        logger.info(f"[{request_id}] Processing complete - {word_count} words, AI used: {used_ai}")

        # Mark job as complete
        job.update_progress(4, 4, 'Complete!')
        result = {
            'markdown': markdown,
            'media_urls': media_urls,
            'filename': filename,
            'word_count': word_count,
            'used_ai': used_ai
        }
        job.complete(result)

        # End diagnostic tracking (success)
        if diagnostic_monitor:
            diagnostic_monitor.log_request_end(request_id, status="success")

        return ProcessHTMLResponse(
            markdown=markdown,
            media_urls=media_urls,
            filename=filename,
            word_count=word_count,
            success=True,
            used_ai=used_ai,
            error=error,
            metadata=prep_metadata,
            job_id=job_id
        )

    except Exception as e:
        logger.error(f"[{request_id}] Error processing HTML: {str(e)}", exc_info=True)

        # Log exception in diagnostics
        if diagnostic_monitor:
            diagnostic_monitor.log_exception(f"POST /process-html ({request_id})", e)
            diagnostic_monitor.log_request_end(request_id, status="error", error=str(e))

        # Mark job as failed if job exists
        if job:
            job.fail(str(e))

        raise HTTPException(status_code=500, detail=str(e))


@app.post("/extract-links", response_model=ExtractLinksResponse)
async def extract_links(request: ExtractLinksRequest):
    """
    Extract and categorize links from HTML
    """
    try:
        logger.info(f"Extracting links from: {request.base_url}")
        links_data = preprocessor.extract_links(request.html, request.base_url)

        logger.info(f"Links extracted - Internal: {len(links_data['internal_links'])}, External: {len(links_data['external_links'])}, Media: {len(links_data['media_links'])}")

        return ExtractLinksResponse(
            internal_links=links_data['internal_links'],
            external_links=links_data['external_links'],
            media_links=links_data['media_links'],
            success=True
        )

    except Exception as e:
        logger.error(f"Error extracting links: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/site-map/start")
async def start_site_map(request: SiteMapRequest):
    """
    Create a new site mapping job
    """
    try:
        logger.info(f"Starting site map for: {request.start_url} (max_depth: {request.max_depth})")

        # Create a site map job
        job = job_manager.create_job(
            Job.TYPE_SITE_MAP,
            params={
                'start_url': request.start_url,
                'max_depth': request.max_depth
            }
        )

        # Start the job
        job.start()
        job.update_progress(0, 1, f"Starting site discovery from {request.start_url}")

        logger.info(f"Site map job created: {job.id}")

        return {
            "job_id": job.id,
            "success": True,
            "message": "Site mapping job started"
        }

    except Exception as e:
        logger.error(f"Error starting site map: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/site-map/progress")
async def update_site_map_progress(request: SiteMapProgressRequest):
    """
    Update progress of a site mapping job
    """
    try:
        job = job_manager.get_job(request.job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        # Update progress
        job.update_progress(
            request.discovered_count,
            max(request.total_to_process, request.discovered_count),
            request.message or f"Discovered {request.discovered_count} pages"
        )

        return {
            "success": True,
            "message": "Progress updated"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating site map progress: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/site-map/complete")
async def complete_site_map(job_id: str = Body(...), discovered_urls: List[str] = Body(...)):
    """
    Complete a site mapping job
    """
    try:
        job = job_manager.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        # Complete the job
        job.complete({
            'discovered_urls': discovered_urls,
            'total_discovered': len(discovered_urls)
        })

        logger.info(f"Site map job completed: {job_id} - {len(discovered_urls)} URLs discovered")

        return {
            "success": True,
            "message": f"Site mapping completed - {len(discovered_urls)} URLs discovered"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error completing site map: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/estimate-cost", response_model=EstimateCostResponse)
async def estimate_cost_endpoint(request: EstimateCostRequest):
    """
    Estimate the cost of processing HTML with AI
    """
    try:
        logger.debug("Cost estimation requested")
        # Preprocess first to get realistic token count
        cleaned_html, _ = preprocessor.preprocess(request.html)

        model = request.model or settings.get('default_model')
        cost_data = estimate_cost(cleaned_html, model)

        logger.debug(f"Cost estimate: ${cost_data['estimated_cost_usd']} for model {model}")

        return EstimateCostResponse(**cost_data)

    except Exception as e:
        logger.error(f"Error estimating cost: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/jobs", response_model=JobListResponse)
async def list_jobs(status: Optional[str] = None, limit: int = 50):
    """
    List all jobs, optionally filtered by status
    """
    try:
        logger.debug(f"Listing jobs - status: {status}, limit: {limit}")
        jobs = job_manager.list_jobs(status=status, limit=limit)

        return JobListResponse(
            jobs=jobs,
            total=len(jobs)
        )

    except Exception as e:
        logger.error(f"Error listing jobs: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job(job_id: str):
    """
    Get details of a specific job
    """
    try:
        logger.debug(f"Getting job: {job_id}")
        job = job_manager.get_job(job_id)

        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        return JobResponse(**job.to_dict())

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/jobs/{job_id}")
async def delete_job(job_id: str):
    """
    Delete a job
    """
    try:
        logger.debug(f"Deleting job: {job_id}")
        success = job_manager.delete_job(job_id)

        if not success:
            raise HTTPException(status_code=404, detail="Job not found")

        return {"success": True, "message": "Job deleted"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting job: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/jobs/{job_id}/pause")
async def pause_job(job_id: str):
    """
    Pause a running job
    """
    try:
        logger.info(f"Pausing job: {job_id}")
        job = job_manager.get_job(job_id)

        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        success = job_manager.pause_job(job_id)

        if not success:
            raise HTTPException(
                status_code=400,
                detail="Job cannot be paused (must be in processing state)"
            )

        logger.info(f"Job paused successfully: {job_id}")
        return {"success": True, "message": "Job paused", "job": job.to_dict()}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error pausing job: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/jobs/{job_id}/resume")
async def resume_job(job_id: str):
    """
    Resume a paused job
    """
    try:
        logger.info(f"Resuming job: {job_id}")
        job = job_manager.get_job(job_id)

        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        success = job_manager.resume_job(job_id)

        if not success:
            raise HTTPException(
                status_code=400,
                detail="Job cannot be resumed (must be in paused state)"
            )

        logger.info(f"Job resumed successfully: {job_id}")
        return {"success": True, "message": "Job resumed", "job": job.to_dict()}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resuming job: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/jobs/{job_id}/stop")
async def stop_job(job_id: str):
    """
    Stop a job (same as pause, but indicates user intention to stop)
    Job data is preserved so user can still access discovered URLs
    """
    try:
        logger.info(f"Stopping job: {job_id}")
        job = job_manager.get_job(job_id)

        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        # For now, stop is the same as pause
        # The job stays in the system with its current progress
        success = job_manager.pause_job(job_id)

        if not success:
            raise HTTPException(
                status_code=400,
                detail="Job cannot be stopped (must be in processing state)"
            )

        logger.info(f"Job stopped successfully: {job_id}")
        return {
            "success": True,
            "message": "Job stopped. Discovered data is preserved.",
            "job": job.to_dict()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error stopping job: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/diagnostics")
async def get_diagnostics():
    """
    Get diagnostic status report (only available when ENABLE_DIAGNOSTICS=true)
    """
    if not ENABLE_DIAGNOSTICS or not diagnostic_monitor:
        raise HTTPException(status_code=404, detail="Diagnostics not enabled. Set ENABLE_DIAGNOSTICS=true environment variable")

    diagnostic_monitor.print_status_report()
    return diagnostic_monitor.get_status_report()


def _generate_filename(text: str) -> str:
    """
    Generate a valid filename from title or URL
    """
    # Remove protocol and domain if it's a URL
    if text.startswith(('http://', 'https://')):
        text = text.split('//')[-1]
        text = '/'.join(text.split('/')[1:]) or text.split('/')[0]

    # Clean up the text
    text = text.strip()

    # Replace invalid filename characters
    text = re.sub(r'[<>:"/\\|?*]', '_', text)

    # Replace spaces and multiple underscores
    text = re.sub(r'[\s_]+', '_', text)

    # Limit length
    text = text[:100]

    # Remove trailing dots and underscores
    text = text.rstrip('._')

    # Ensure we have something
    if not text:
        text = "page"

    return f"{text}.md"


if __name__ == "__main__":
    import uvicorn

    port = settings.get('server_port', 8077)

    logger.info("=" * 50)
    logger.info("  Simple Page Saver API Server")
    logger.info("=" * 50)
    logger.info(f"Server starting on http://localhost:{port}")
    logger.info(f"API Documentation: http://localhost:{port}/docs")
    logger.info(f"AI Enabled: {bool(settings.get_api_key())}")
    logger.info("Press CTRL+C to stop the server")
    logger.info("=" * 50)

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level=settings.get('log_level', 'INFO').lower()
    )
