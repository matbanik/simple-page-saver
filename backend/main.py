"""
FastAPI Backend for Simple Page Saver
Main application with REST API endpoints
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import os
from dotenv import load_dotenv
import re

from preprocessing import HTMLPreprocessor, estimate_tokens
from ai_converter import AIConverter, estimate_cost

load_dotenv()

app = FastAPI(
    title="Simple Page Saver API",
    description="Backend service for converting web pages to markdown",
    version="1.0.0"
)

# Enable CORS for Chrome extension
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify extension ID
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize processors
preprocessor = HTMLPreprocessor()
converter = AIConverter()


# Request/Response Models
class ProcessHTMLRequest(BaseModel):
    url: str
    html: str
    title: Optional[str] = ""


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
    return {
        "status": "healthy",
        "service": "Simple Page Saver API",
        "version": "1.0.0",
        "ai_enabled": bool(os.getenv('OPENROUTER_API_KEY'))
    }


@app.post("/process-html", response_model=ProcessHTMLResponse)
async def process_html(request: ProcessHTMLRequest):
    """
    Main processing endpoint: preprocess HTML and convert to markdown
    """
    try:
        # Step 1: Preprocess HTML
        cleaned_html, prep_metadata = preprocessor.preprocess(request.html, request.url)

        # Step 2: Estimate tokens
        token_count = estimate_tokens(cleaned_html)
        prep_metadata['estimated_tokens'] = token_count

        # Step 3: Extract media links
        links_data = preprocessor.extract_links(request.html, request.url)
        media_urls = links_data['media_links']

        # Step 4: Convert to markdown (with chunking if needed)
        if token_count > 20000:  # ~80K characters
            markdown, used_ai, error = converter.convert_large_html(cleaned_html, request.title)
        else:
            markdown, used_ai, error = converter.convert_to_markdown(cleaned_html, request.title)

        # Step 5: Generate filename from title or URL
        filename = _generate_filename(request.title or request.url)

        # Step 6: Count words in markdown
        word_count = len(re.findall(r'\w+', markdown))

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
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/extract-links", response_model=ExtractLinksResponse)
async def extract_links(request: ExtractLinksRequest):
    """
    Extract and categorize links from HTML
    """
    try:
        links_data = preprocessor.extract_links(request.html, request.base_url)

        return ExtractLinksResponse(
            internal_links=links_data['internal_links'],
            external_links=links_data['external_links'],
            media_links=links_data['media_links'],
            success=True
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/estimate-cost", response_model=EstimateCostResponse)
async def estimate_cost_endpoint(request: EstimateCostRequest):
    """
    Estimate the cost of processing HTML with AI
    """
    try:
        # Preprocess first to get realistic token count
        cleaned_html, _ = preprocessor.preprocess(request.html)

        model = request.model or os.getenv('DEFAULT_MODEL', 'deepseek/deepseek-chat')
        cost_data = estimate_cost(cleaned_html, model)

        return EstimateCostResponse(**cost_data)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _generate_filename(text: str) -> str:
    """
    Generate a valid filename from title or URL

    Args:
        text: Title or URL string

    Returns:
        Valid filename string
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

    port = int(os.getenv('SERVER_PORT', '8077'))

    print(f"""
    ╔═══════════════════════════════════════════════════╗
    ║      Simple Page Saver API Server                ║
    ╚═══════════════════════════════════════════════════╝

    🚀 Server starting on http://localhost:{port}
    📝 API Documentation: http://localhost:{port}/docs
    🔑 AI Enabled: {bool(os.getenv('OPENROUTER_API_KEY'))}

    Press CTRL+C to stop the server
    """)

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info"
    )
