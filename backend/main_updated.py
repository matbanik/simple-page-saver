"""
FastAPI Backend for Simple Page Saver
Main application with REST API endpoints, logging, and settings management
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import os
import re

from preprocessing import HTMLPreprocessor, estimate_tokens
from ai_converter import AIConverter, estimate_cost
from settings_manager import SettingsManager
from logging_config import setup_logging, log_ai_request, log_ai_response

# Initialize settings and logging
settings = SettingsManager()
logger = setup_logging(log_level=settings.get('log_level', 'INFO'))

# Export settings as environment variables for compatibility
env_vars = settings.export_for_env()
for key, value in env_vars.items():
    os.environ[key] = value

logger.info("=== Simple Page Saver Backend Starting ===")
logger.info(f"Server Port: {settings.get('server_port')}")
logger.info(f"Default Model: {settings.get('default_model')}")
logger.info(f"Log Level: {settings.get('log_level')}")
logger.info(f"API Key Configured: {bool(settings.get_api_key())}")

app = FastAPI(
    title="Simple Page Saver API",
    description="Backend service for converting web pages to markdown",
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

# Initialize processors
preprocessor = HTMLPreprocessor()
converter = AIConverter(
    api_key=settings.get_api_key(),
    model=settings.get('default_model')
)


# Request/Response Models
class ProcessHTMLRequest(BaseModel):
    url: str
    html: str
    title: Optional[str] = ""
    use_ai: Optional[bool] = True


class ProcessHTMLResponse(BaseModel):
    markdown: str
    media_urls: List[str]
    filename: str
    word_count: int
    success: bool
    used_ai: bool
    error: Optional[str] = None
    metadata: dict


class ExtractLinksRequest(BaseModel):
    html: str
    base_url: str


class ExtractLinksResponse(BaseModel):
    internal_links: List[str]
    external_links: List[str]
    media_links: List[str]
    success: bool


class EstimateCostRequest(BaseModel):
    html: str
    model: Optional[str] = None


class EstimateCostResponse(BaseModel):
    estimated_input_tokens: int
    estimated_output_tokens: int
    estimated_cost_usd: float
    model: str


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


@app.post("/process-html", response_model=ProcessHTMLResponse)
async def process_html(request: ProcessHTMLRequest):
    """
    Main processing endpoint: preprocess HTML and convert to markdown
    """
    try:
        logger.info(f"Processing request for URL: {request.url}")
        logger.debug(f"HTML size: {len(request.html)} chars, use_ai: {request.use_ai}")

        # Step 1: Preprocess HTML
        cleaned_html, prep_metadata = preprocessor.preprocess(request.html, request.url)
        logger.info(f"Preprocessing complete - reduced from {prep_metadata['original_size']} to {prep_metadata['final_size']} chars ({prep_metadata.get('reduction_percentage', 0)}% reduction)")

        # Step 2: Estimate tokens
        token_count = estimate_tokens(cleaned_html)
        prep_metadata['estimated_tokens'] = token_count
        logger.debug(f"Estimated tokens: {token_count}")

        # Step 3: Extract media links
        links_data = preprocessor.extract_links(request.html, request.url)
        media_urls = links_data['media_links']
        logger.debug(f"Extracted {len(media_urls)} media URLs")

        # Step 4: Convert to markdown (with chunking if needed)
        if not request.use_ai:
            logger.info("AI disabled by user, using fallback")
            log_ai_request(logger, "fallback", len(cleaned_html), {})
            markdown = converter._convert_with_html2text(cleaned_html, request.title)
            used_ai = False
            error = "AI disabled by user"
            log_ai_response(logger, "fallback", len(markdown), False, error)
        elif token_count > 20000:
            logger.warning(f"Large content ({token_count} tokens), using chunking")
            log_ai_request(logger, settings.get('default_model'), len(cleaned_html), {'chunked': True})
            markdown, used_ai, error = converter.convert_large_html(cleaned_html, request.title)
            log_ai_response(logger, settings.get('default_model'), len(markdown), used_ai, error)
        else:
            log_ai_request(logger, settings.get('default_model'), len(cleaned_html), {})
            markdown, used_ai, error = converter.convert_to_markdown(cleaned_html, request.title)
            log_ai_response(logger, settings.get('default_model'), len(markdown), used_ai, error)

        # Step 5: Generate filename from title or URL
        filename = _generate_filename(request.title or request.url)
        logger.debug(f"Generated filename: {filename}")

        # Step 6: Count words in markdown
        word_count = len(re.findall(r'\w+', markdown))

        logger.info(f"Processing complete - {word_count} words, AI used: {used_ai}")

        return ProcessHTMLResponse(
            markdown=markdown,
            media_urls=media_urls,
            filename=filename,
            word_count=word_count,
            success=True,
            used_ai=used_ai,
            error=error,
            metadata=prep_metadata
        )

    except Exception as e:
        logger.error(f"Error processing HTML: {str(e)}", exc_info=True)
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
        "main_updated:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level=settings.get('log_level', 'INFO').lower()
    )
