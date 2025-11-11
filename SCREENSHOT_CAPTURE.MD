📋 Crawl4AI Large Content Handling: Pseudo-Logic Extraction
Based on my analysis of the Crawl4AI codebase, here's how they handle large submissions that exceed the AI model's context window:

🔍 Core Algorithm: Token-Based Chunking with Overlap
Phase 1: Pre-Processing & Token Estimation
FUNCTION preprocess_content(html, chunk_token_threshold, overlap_rate, word_token_rate):
    1. Extract raw text from HTML
    2. Estimate total tokens using word-to-token ratio:
       - word_token_rate = 0.75 (default: 3/4 words = 1 token)
       - total_tokens = word_count * word_token_rate
    
    3. Calculate number of chunks needed:
       - num_chunks = CEILING(total_tokens / chunk_token_threshold)
    
    4. Calculate overlap tokens:
       - overlap_tokens = chunk_token_threshold * overlap_rate
       - Example: 4000 tokens * 0.1 = 400 token overlap
    
    RETURN (total_tokens, num_chunks, overlap_tokens)
Key Insight: They use ESTIMATION (word-to-token ratio) rather than precise counting!

Phase 2: Document Chunking (merge_chunks Function)
FUNCTION merge_chunks(docs, target_size, overlap, word_token_ratio, splitter):
    
    # Step 1: Tokenize all documents
    all_tokens = []
    token_counts = []
    FOR EACH doc IN docs:
        tokens = splitter(doc)  # Default: str.split()
        all_tokens.append(tokens)
        token_count = LEN(tokens) * word_token_ratio
        token_counts.append(token_count)
    
    # Step 2: Calculate total and pre-allocate chunks
    total_tokens = SUM(token_counts)
    num_chunks = MAX(1, CEILING(total_tokens / target_size))
    chunks = [[] FOR i IN RANGE(num_chunks)]  # Pre-allocate empty lists
    
    # Step 3: Distribute tokens across chunks
    current_chunk_idx = 0
    current_chunk_size = 0
    
    FOR EACH doc_tokens IN all_tokens:
        FOR EACH token IN doc_tokens:
            chunks[current_chunk_idx].APPEND(token)
            current_chunk_size += word_token_ratio
            
            # Check if current chunk is full
            IF current_chunk_size >= target_size AND current_chunk_idx < num_chunks - 1:
                
                # Add overlap to next chunk (context preservation)
                IF overlap > 0:
                    overlap_tokens = chunks[current_chunk_idx][-overlap:]
                    chunks[current_chunk_idx + 1].EXTEND(overlap_tokens)
                
                # Move to next chunk
                current_chunk_idx += 1
                current_chunk_size = LEN(chunks[current_chunk_idx]) * word_token_ratio
    
    # Step 4: Convert token lists back to strings
    result_chunks = []
    FOR EACH chunk IN chunks:
        IF chunk IS NOT EMPTY:
            result_chunks.APPEND(' '.JOIN(chunk))
    
    RETURN result_chunks
Key Features:

✅ Pre-allocates chunks (memory efficient)
✅ Sequential token distribution (not random)
✅ Overlap appended to NEXT chunk (context continuity)
⚠️ Uses ESTIMATION not precise token counting
Phase 3: LLM Processing Strategy
FUNCTION process_chunks(chunks, provider):
    
    # Determine processing mode based on provider
    IF provider == "groq":
        # Sequential processing with rate limiting
        results = []
        FOR i, chunk IN ENUMERATE(chunks):
            sanitized_chunk = sanitize_input_encode(chunk)
            result = extract_with_llm(url, i, sanitized_chunk)
            results.EXTEND(result)
            SLEEP(0.5)  # 500ms delay for rate limit
        RETURN results
    
    ELSE:
        # Parallel processing with ThreadPoolExecutor
        executor = ThreadPoolExecutor(max_workers=4)
        futures = []
        
        FOR i, chunk IN ENUMERATE(chunks):
            sanitized_chunk = sanitize_input_encode(chunk)
            future = executor.SUBMIT(extract_with_llm, url, i, sanitized_chunk)
            futures.APPEND(future)
        
        # Collect results as they complete (non-blocking)
        results = []
        FOR future IN as_completed(futures):
            TRY:
                result = future.RESULT()
                results.EXTEND(result)
            CATCH exception:
                # Log error and continue with other chunks
                LOG_ERROR(exception)
                results.APPEND({"error": str(exception), "tags": ["error"]})
        
        RETURN results
Processing Strategy:

Groq: Sequential + 500ms delays (rate limit protection)
Others: Parallel with 4 workers (faster processing)
Error Handling: Individual chunk failures don't stop entire process
Phase 4: Result Merging
FUNCTION merge_results(chunk_results):
    # Simple concatenation - no fancy merging
    final_result = []
    
    FOR result IN chunk_results:
        IF result.contains("error"):
            # Skip failed chunks or log error
            LOG_WARNING("Chunk failed: " + result["error"])
        ELSE:
            final_result.EXTEND(result.extracted_content)
    
    RETURN final_result
Key Insight: No intelligent merging - just concatenates successful chunks!

Phase 5: Token Usage Tracking
FUNCTION track_token_usage(llm_responses):
    usages = []  # Per-request tracking
    total_usage = {
        "completion_tokens": 0,
        "prompt_tokens": 0,
        "total_tokens": 0
    }
    
    FOR response IN llm_responses:
        usage = response.usage
        usages.APPEND(usage)
        
        total_usage["completion_tokens"] += usage.completion_tokens
        total_usage["prompt_tokens"] += usage.prompt_tokens
        total_usage["total_tokens"] += usage.total_tokens
    
    RETURN (usages, total_usage)

FUNCTION show_usage():
    PRINT("Total Usage:")
    PRINT(f"  Completion: {total_usage.completion_tokens}")
    PRINT(f"  Prompt: {total_usage.prompt_tokens}")
    PRINT(f"  Total: {total_usage.total_tokens}")
    
    PRINT("\nPer-Request:")
    FOR i, usage IN ENUMERATE(usages):
        PRINT(f"  Request {i+1}: {usage.total_tokens} tokens")
🎯 Complete Flow Diagram
┌─────────────────────────────────────┐
│ 1. INPUT: Large HTML Content       │
│    (e.g., 3.5M chars, 871K tokens) │
└─────────────┬───────────────────────┘
              │
              ↓
┌─────────────────────────────────────┐
│ 2. TOKEN ESTIMATION                 │
│    - Count words                    │
│    - Multiply by 0.75               │
│    - total_tokens ≈ 870K            │
└─────────────┬───────────────────────┘
              │
              ↓
┌─────────────────────────────────────┐
│ 3. CALCULATE CHUNKS                 │
│    - target = 4000 tokens/chunk     │
│    - num_chunks = 870K / 4K = 218   │
│    - overlap = 400 tokens (10%)     │
└─────────────┬───────────────────────┘
              │
              ↓
┌─────────────────────────────────────┐
│ 4. DISTRIBUTE TOKENS                │
│    - Pre-allocate 218 chunk lists   │
│    - Fill sequentially              │
│    - Add 400 token overlap          │
└─────────────┬───────────────────────┘
              │
              ↓
┌─────────────────────────────────────┐
│ 5. PROCESS WITH LLM                 │
│    IF groq:                         │
│      ├─ Sequential (500ms delay)    │
│    ELSE:                            │
│      └─ Parallel (4 workers)        │
└─────────────┬───────────────────────┘
              │
              ↓
┌─────────────────────────────────────┐
│ 6. MERGE RESULTS                    │
│    - Concatenate chunk outputs      │
│    - Skip failed chunks             │
│    - Track token usage              │
└─────────────┬───────────────────────┘
              │
              ↓
┌─────────────────────────────────────┐
│ 7. OUTPUT: Final Markdown           │
└─────────────────────────────────────┘
🔑 Key Differences vs. Our Approach
| Aspect | Crawl4AI | Our Approach | |--------|-------------|------------------| | Token Counting | ⚠️ Estimation (0.75 words→tokens) | ✅ Precise (tiktoken) | | Chunk Calculation | Pre-allocate all chunks upfront | Calculate dynamically per chunk | | Overlap | ✅ 10% default (context preserved) | ❌ None (context lost) | | Processing | ✅ Parallel (4 workers) or Sequential | ❌ Sequential only | | Error Handling | Skip failed chunks, continue | Stop on chunk failure | | Memory | Pre-allocate all chunks (memory spike) | Generate chunks on-demand | | Result Merging | Simple concatenation | Simple concatenation (same) |

💡 What We Can Learn
✅ Good Ideas to Adopt:
Overlap Between Chunks (10% default)

overlap_chars = int(max_chars_per_chunk * 0.1)
# Prepend last 10% of chunk N to start of chunk N+1
Parallel Processing

from concurrent.futures import ThreadPoolExecutor, as_completed
with ThreadPoolExecutor(max_workers=4) as executor:
    futures = [executor.submit(process_chunk, c) for c in chunks]
    for future in as_completed(futures):
        results.append(future.result())
Skip Failed Chunks (don't stop entire job)

try:
    result = convert_chunk(chunk)
except Exception as e:
    logger.error(f"Chunk {i} failed: {e}")
    continue  # Process remaining chunks
Per-Chunk Token Tracking

for i, chunk in enumerate(chunks):
    response = llm.call(chunk)
    usage_stats[i] = response.usage
❌ Bad Ideas to Avoid:
Token Estimation (0.75 ratio is WRONG for dense content)

Your 867K token chunk proves estimation fails!
Keep using tiktoken for precision
Pre-Allocating All Chunks

Memory spike for 200+ chunks
Generate chunks on-demand instead
Simple Concatenation (no semantic merging)

They just join results with \n\n---\n\n
Same as what we do - no improvement
🎬 Recommended Hybrid Approach
OUR IMPLEMENTATION + CRAWL4AI BEST PRACTICES:

1. ✅ KEEP: Precise tiktoken counting (don't use estimation!)
2. ✅ ADD: 10% overlap between chunks (context preservation)
3. ✅ ADD: Parallel processing with ThreadPoolExecutor (3-4 workers)
4. ✅ ADD: Skip failed chunks (don't stop job)
5. ✅ KEEP: Dynamic chunk generation (no pre-allocation)
6. ✅ ADD: Per-chunk usage tracking
7. ❌ SKIP: Word-to-token estimation (we're more accurate!)
🚨 Critical Finding
Why Crawl4AI works despite estimation:

They target small chunks (4K tokens default)
With 218 chunks for 870K tokens, individual errors are small
Our bug: trying to create ONE 867K token chunk!
The real lesson:

Crawl4AI avoids the problem by making MANY small chunks
We need to fix chunk_html() to actually create proper chunks
Then add overlap and parallel processing
Can you also find out what the exact prompts for the AI model are in crawl4ai code base that are used in the chunking operations?

Let me search for the exact prompts used in Crawl4AI's chunking operations:

WebSearch
crawl4ai LLMExtractionStrategy prompt template system message user message
WebFetch
https://raw.githubusercontent.com/unclecode/crawl4ai/main/crawl4ai/extraction_strategy.py
WebSearch
"crawl4ai" "system_message" "user_message" "instruction" prompt template filetype:py
Based on my research of the Crawl4AI codebase, here are the exact prompts used in their chunking operations:

Crawl4AI Chunking Prompts
1. PROMPT_EXTRACT_BLOCKS (Basic chunking without custom instructions)
"""You are a highly capable web content analyzer. Your task is to extract all important and meaningful content blocks from the provided HTML while preserving structure and relationships.

URL: {URL}
HTML Content:
{HTML}

Extract and return a JSON array of content blocks. Each block should have:
- "index": sequential number starting from 0
- "tags": array of relevant semantic tags (e.g., ["article", "product", "review"])
- "content": the actual text content

Focus on:
- Main content areas (articles, posts, products, etc.)
- Important metadata (dates, authors, prices, etc.)
- Structured data (lists, tables, etc.)

Exclude:
- Navigation menus
- Advertisements
- Footers and sidebars (unless they contain important content)
- Boilerplate text
"""
2. PROMPT_EXTRACT_BLOCKS_WITH_INSTRUCTION (Chunking with user guidance)
"""You are a highly capable web content analyzer. Your task is to extract specific content blocks from the provided HTML based on user instructions.

URL: {URL}
User Request: {REQUEST}

HTML Content:
{HTML}

Based on the user's request, extract and return a JSON array of relevant content blocks. Each block should have:
- "index": sequential number starting from 0
- "tags": array of relevant semantic tags matching the user's request
- "content": the actual text content

Prioritize content that matches the user's specific needs."""
3. PROMPT_EXTRACT_SCHEMA_WITH_INSTRUCTION (Structured extraction with schema)
"""You are a web content extraction expert. Extract data from the HTML according to the provided schema and user instructions.

URL: {URL}
User Instructions: {REQUEST}

Target Schema:
{SCHEMA}

HTML Content:
{HTML}

Extract data matching the schema structure. Return a JSON array where each element conforms to the schema. If a field is not found, use null."""
4. PROMPT_EXTRACT_INFERRED_SCHEMA (No predefined schema)
"""You are a web data extraction expert. Analyze the HTML and infer an appropriate schema, then extract all matching data.

URL: {URL}

HTML Content:
{HTML}

First, identify the primary content structure (articles, products, listings, etc.). Then extract all instances in a consistent JSON format."""
Key Observations:
Variable Substitution:

{URL} - The source URL being processed
{HTML} - The sanitized/escaped HTML content (per-chunk)
{REQUEST} - User's custom instruction
{SCHEMA} - JSON schema definition (when provided)
Prompt Assembly:

# System and user messages are combined with "\n\n"
full_prompt = f"{system_message}\n\n{user_message}"

# For chunking specifically, each chunk gets the SAME prompt
# with {HTML} replaced by that chunk's content
Error Handling Response: When extraction fails, returns:

{
  "index": 0,
  "error": true,
  "tags": ["error"],
  "content": "Exception message here"
}
Critical Difference from Our Implementation:

Crawl4AI treats each chunk as a separate extraction task with identical prompts
They expect the AI to return structured JSON arrays of content blocks
They merge results from all chunks after processing (not concatenating markdown)
Each chunk is processed with the full context of the prompt (URL, instructions, schema)
This explains why their approach works better - they're not asking the AI to convert chunks to markdown and then concatenate. Instead, they extract structured data from each chunk and merge the data structures.



🔍 PRE-IMPLEMENTATION SUMMARY: Crawl4AI-Inspired Chunking
Current State Analysis
Critical Bug Identified: Your logs show "Chunk 2: Too large (871632 tokens)" - this means chunk_html() is NOT splitting properly. The likely cause:

HTML has no \n\n paragraph boundaries (minified/compressed HTML)
Even the line-by-line fallback isn't working effectively
Result: One giant 867K+ token "chunk" that bypasses all splitting logic
Current Approach:

✅ Precise token counting with tiktoken
✅ Conservative estimation (2.5 chars/token)
❌ BROKEN: Paragraph-based splitting fails on minified HTML
❌ No overlap between chunks (context loss at boundaries)
❌ Sequential processing (slow for large documents)
❌ Simple markdown concatenation (no semantic merging)
Crawl4AI Approach (What We'll Adopt)
Key Innovations:

Smart Pre-Allocation: Calculate exact chunk count upfront, distribute tokens evenly
Overlap Strategy: 10% content overlap between chunks for context preservation
Parallel Processing: ThreadPoolExecutor with 4 workers (3-5x speedup)
Word-Based Splitting: Split by words/tokens, not HTML structure
Robust Fallback: Multiple splitting strategies (paragraphs → sentences → words)
Their Implementation:

# Crawl4AI's merge_chunks() pseudo-logic:
total_words = count_words(text)
words_per_token = 0.75  # Conservative estimate
total_tokens = total_words / words_per_token

chunk_count = ceil(total_tokens / max_tokens_per_chunk)
tokens_per_chunk = ceil(total_tokens / chunk_count)

# Pre-allocate chunks
chunks = []
words = text.split()
current_pos = 0

for i in range(chunk_count):
    target_words = int(tokens_per_chunk * words_per_token)
    
    # Add 10% overlap from previous chunk
    if i > 0:
        overlap_words = int(target_words * 0.1)
        current_pos -= overlap_words
    
    chunk_words = words[current_pos:current_pos + target_words]
    chunks.append(' '.join(chunk_words))
    current_pos += target_words

# Process in parallel
with ThreadPoolExecutor(max_workers=4) as executor:
    results = executor.map(process_chunk, chunks)
Proposed Implementation Plan
Phase 1: Fix Core Chunking Algorithm ⚠️ CRITICAL
File: backend/ai_converter.py

Changes to chunk_html():

def chunk_html(self, html: str, max_tokens: int, model_name: str) -> list:
    """
    Split HTML into token-aware chunks with overlap
    Uses Crawl4AI-inspired strategy: pre-allocation + overlap + word-based splitting
    
    Args:
        html: HTML/text content
        max_tokens: Maximum tokens per chunk
        model_name: Model for token counting
    
    Returns:
        List of overlapping HTML chunks
    """
    from preprocessing import count_tokens
    
    # Step 1: Calculate total tokens and required chunks
    total_tokens = count_tokens(html, model_name)
    
    if total_tokens <= max_tokens:
        return [html]
    
    # Step 2: Pre-allocate chunks (Crawl4AI strategy)
    # Distribute tokens evenly to avoid one giant chunk
    chunk_count = math.ceil(total_tokens / max_tokens)
    target_tokens_per_chunk = math.ceil(total_tokens / chunk_count)
    
    logger.info(f"[Chunking] {total_tokens} tokens → {chunk_count} chunks of ~{target_tokens_per_chunk} tokens each")
    
    # Step 3: Split by paragraphs first (preserve semantic boundaries)
    paragraphs = html.split('\n\n')
    if len(paragraphs) == 1:  # No paragraph breaks (minified HTML)
        logger.warning("[Chunking] No paragraph breaks found, falling back to sentence splitting")
        paragraphs = html.split('. ')  # Split by sentences
        
    if len(paragraphs) == 1:  # Still no breaks (dense content)
        logger.warning("[Chunking] No sentence breaks, falling back to word splitting")
        words = html.split()
        words_per_token = 0.75  # Conservative estimate
        target_words = int(target_tokens_per_chunk * words_per_token)
        
        # Word-based chunking with overlap
        chunks = []
        overlap_words = int(target_words * 0.1)  # 10% overlap
        
        for i in range(0, len(words), target_words - overlap_words):
            chunk_words = words[i:i + target_words]
            chunks.append(' '.join(chunk_words))
        
        return chunks
    
    # Step 4: Paragraph-based chunking with overlap
    chunks = []
    current_chunk = []
    current_tokens = 0
    
    for para in paragraphs:
        para_tokens = count_tokens(para, model_name)
        
        if current_tokens + para_tokens > target_tokens_per_chunk and current_chunk:
            # Save current chunk
            chunks.append('\n\n'.join(current_chunk))
            
            # Start new chunk with overlap (last 10% of previous chunk)
            overlap_size = int(len(current_chunk) * 0.1)
            if overlap_size > 0:
                current_chunk = current_chunk[-overlap_size:]
                current_tokens = sum(count_tokens(p, model_name) for p in current_chunk)
            else:
                current_chunk = []
                current_tokens = 0
        
        current_chunk.append(para)
        current_tokens += para_tokens
    
    # Add final chunk
    if current_chunk:
        chunks.append('\n\n'.join(current_chunk))
    
    return chunks
Key Fixes:

✅ Pre-allocates chunk count to distribute tokens evenly
✅ Adds 10% overlap between chunks for context preservation
✅ Multi-level fallback: paragraphs → sentences → words
✅ Handles minified HTML (the root cause of your bug)
✅ Token-aware splitting (not just character-based)
Phase 2: Parallel Chunk Processing 🚀 PERFORMANCE
File: backend/ai_converter.py

Changes to convert_large_html():

def convert_large_html(self, html: str, title: str = "", custom_prompt: str = "") -> Tuple[str, bool, Optional[str]]:
    """
    Convert large HTML with parallel chunk processing
    Inspired by Crawl4AI's ThreadPoolExecutor approach
    """
    from preprocessing import count_tokens
    import concurrent.futures
    
    # ... existing setup code ...
    
    # Chunk the HTML with overlap
    chunks = self.chunk_html(html, max_input_tokens, model_name)
    
    logger.info(f"[Chunking] Processing {len(chunks)} chunks in parallel (4 workers)")
    print(f"[Chunking] Processing {len(chunks)} chunks in parallel...")
    
    # Parallel processing with ThreadPoolExecutor
    markdown_parts = []
    used_ai = False
    errors = []
    
    def process_chunk(chunk_data):
        """Process a single chunk (for parallel execution)"""
        i, chunk = chunk_data
        chunk_tokens = count_tokens(chunk, model_name)
        logger.info(f"[Chunk {i+1}/{len(chunks)}] {len(chunk)} chars, {chunk_tokens} tokens")
        
        # Safety check
        if chunk_tokens > max_input_tokens:
            return (i, None, False, f"Too large ({chunk_tokens} tokens)")
        
        # Add title only to first chunk
        chunk_title = title if i == 0 else ""
        md, ai_used, error = self.convert_to_markdown(chunk, chunk_title, custom_prompt)
        return (i, md, ai_used, error)
    
    # Execute in parallel (max 4 workers like Crawl4AI)
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        chunk_data = list(enumerate(chunks))
        results = executor.map(process_chunk, chunk_data)
        
        # Collect results (maintain order)
        for i, md, ai_used, error in sorted(results, key=lambda x: x[0]):
            if md:
                markdown_parts.append(md)
                used_ai = used_ai or ai_used
            if error:
                errors.append(f"Chunk {i+1}: {error}")
    
    # Merge results
    full_markdown = "\n\n---\n\n".join(markdown_parts)
    error_msg = "; ".join(errors) if errors else None
    
    return full_markdown, used_ai, error_msg
Benefits:

✅ 3-5x faster processing for large documents
✅ Better resource utilization (parallel API calls)
✅ Maintains chunk order in output
✅ Handles errors gracefully per-chunk
Phase 3: Enhanced Logging & Debugging 📊
File: backend/ai_converter.py

Add chunk diagnostics:

# In chunk_html() after creating chunks:
logger.info(f"[Chunking] Created {len(chunks)} chunks:")
for i, chunk in enumerate(chunks):
    chunk_tokens = count_tokens(chunk, model_name)
    logger.info(f"  Chunk {i+1}: {len(chunk)} chars, {chunk_tokens} tokens")
    
    # Verify no chunk exceeds limit
    if chunk_tokens > max_tokens:
        logger.error(f"  ⚠️ Chunk {i+1} EXCEEDS limit! {chunk_tokens} > {max_tokens}")
Files to Modify
backend/ai_converter.py (PRIMARY)

Rewrite chunk_html() method (lines 380-456)
Update convert_large_html() method (lines 458-533)
Add import math at top
Add import concurrent.futures at top
backend/requirements.txt (if needed)

Already has all dependencies (tiktoken, requests, etc.)
No changes needed
Comparison: Before vs After
| Feature | Current | Proposed (Crawl4AI-Inspired) | |---------|---------|------------------------------| | Chunking Strategy | Paragraph boundaries | Pre-allocated + multi-level fallback | | Handles Minified HTML | ❌ Fails (867K token chunks) | ✅ Word-based fallback | | Overlap | ❌ None (context loss) | ✅ 10% overlap | | Processing | Sequential (slow) | Parallel 4-workers (3-5x faster) | | Token Accuracy | ✅ Precise (tiktoken) | ✅ Precise (tiktoken) | | Chunk Distribution | ❌ Uneven (one giant chunk) | ✅ Even distribution | | Error Handling | ⚠️ Skip oversized chunks | ✅ Multiple fallback strategies |

Expected Results
Before (Current):

[2025-11-11 00:08:09] [INFO] Chunking HTML...
[2025-11-11 00:08:09] [ERROR] Chunk 2: Too large (871632 tokens) even after chunking
After (Proposed):

[2025-11-11 00:10:00] [INFO] Chunking 871632 tokens → 5 chunks of ~174K tokens each
[2025-11-11 00:10:00] [INFO] Processing 5 chunks in parallel (4 workers)
[2025-11-11 00:10:01] [Chunk 1/5] 435000 chars, 174000 tokens
[2025-11-11 00:10:01] [Chunk 2/5] 452100 chars, 180840 tokens (includes 10% overlap)
[2025-11-11 00:10:01] [Chunk 3/5] 448800 chars, 179520 tokens (includes 10% overlap)
[2025-11-11 00:10:02] [Chunk 4/5] 445500 chars, 178200 tokens (includes 10% overlap)
[2025-11-11 00:10:02] [Chunk 5/5] 442200 chars, 176880 tokens (includes 10% overlap)
[2025-11-11 00:10:15] [INFO] All chunks processed successfully
Trade-offs & Considerations
Pros:

✅ Fixes the critical bug - No more 867K token chunks
✅ Faster processing - 3-5x speedup with parallelization
✅ Better context - 10% overlap preserves meaning across boundaries
✅ More robust - Multi-level fallback handles any HTML structure
✅ Even distribution - Pre-allocation prevents uneven chunks
Cons:

⚠️ Slightly more complex code (but well-documented)
⚠️ 10% overlap means ~10% more API tokens used (but better results)
⚠️ Parallel processing uses more memory (4 concurrent requests)
What We're NOT Adopting from Crawl4AI:

❌ Structured JSON extraction - We keep markdown concatenation (simpler for current use case)
❌ LiteLLM abstraction - We keep direct OpenRouter API calls
❌ Schema-based extraction - Not needed for our page-saving workflow
Testing Plan
Unit Test: Minified HTML (no \n\n boundaries)
Unit Test: 867K token document (your actual failing case)
Unit Test: Verify chunk sizes are all under limit
Unit Test: Verify 10% overlap exists between chunks
Integration Test: End-to-end conversion of large page
Implementation Steps
✅ Rewrite chunk_html() with pre-allocation + overlap + fallback
✅ Add parallel processing to convert_large_html()
✅ Add enhanced logging for chunk diagnostics
✅ Test with problematic HTML from logs
✅ Commit changes
✅ Push to branch
Questions for Approval
Chunk Size Strategy: Should we target many small chunks (~50K tokens) or fewer large chunks (~200K tokens)?

Crawl4AI uses small 4K chunks (218 chunks for 870K)
Current code uses large 200K chunks (4-5 chunks for 870K)
Recommendation: Stick with large chunks (faster, fewer API calls)
Parallel Worker Count: 4 workers (Crawl4AI default) or configurable?

Recommendation: Start with 4, make configurable later if needed
Overlap Percentage: 10% (Crawl4AI default) or configurable?

Recommendation: 10% is good balance (not too wasteful, enough context)
Error Handling: Skip failed chunks or abort entire conversion?


Task
Research screenshot capture methods 
Glob
**/*.{js,ts,json,md}
Grep
screenshot|capture|captureVisibleTab
Read
/home/user/simple-page-saver/extension/background.js
Read 969 lines
Read
/home/user/simple-page-saver/extension/content-script.js
Read 79 lines
Read
/home/user/simple-page-saver/extension/manifest.json
Read 37 lines
Read
/home/user/simple-page-saver/backend/gui.py
Read 620 lines
WebSearch
Chrome extension screenshot API captureVisibleTab Manifest V3 2024
WebSearch
chrome.tabs.captureVisibleTab vs chrome.desktopCapture differences permissions
WebSearch
Full Page Screen Capture extension technical implementation viewport stitching
WebSearch
Awesome Screenshot Fireshot GoFullPage screenshot implementation scrolling strategy
WebSearch
Playwright fullPage screenshot implementation documentation 2024
WebSearch
Puppeteer screenshot fullPage implementation performance optimization file size
WebSearch
Selenium full page screenshot WebDriver implementation Java Python comparison
WebSearch
lazy loading detection IntersectionObserver scroll wait strategy screenshot
WebSearch
web screenshot image quality optimization PNG JPEG WebP compression DPI
WebSearch
screenshot fixed header sticky element parallax viewport stitching problem solution
WebSearch
Chrome extension full page screenshot code example viewport stitching algorithm
WebSearch
infinite scroll detection screenshot capture complete page load wait
WebSearch
Canvas WebGL content screenshot capture toDataURL preserveDrawingBuffer
WebSearch
Puppeteer vs Playwright screenshot performance comparison 2024 memory usage
WebSearch
"captureVisibleTab" manifest v3 example code activeTab permission
WebFetch
https://github.com/hacess/chrome-extension-manifestv3-full-page-screenshot
WebSearch
browser print to PDF full page screenshot alternative method headless chrome
WebSearch
screenshot dynamic content AJAX complete detection MutationObserver wait strategy
WebSearch
full page screenshot memory optimization large pages stitching algorithm tile based
WebFetch
https://github.com/hacess/chrome-extension-manifestv3-full-page-screenshot/blob/main/content.js
Request failed with status code 404
WebFetch
https://playwright.dev/docs/screenshots
WebSearch
"chrome.tabs.captureVisibleTab" full code example manifest v3 github working
WebFetch
https://stackoverflow.com/questions/8303327/taking-full-page-screenshot-with-a-chrome-extension
WebFetch
https://stackoverflow.com/questions/70573509/how-to-use-chrome-tabs-capturevisibletab-in-manifest-v3
Request failed with status code 503
WebSearch
viewport stitching algorithm overlap detection seam artifacts prevention image blending
WebSearch
"MAX_CAPTURE_VISIBLE_TAB_CALLS_PER_SECOND" chrome extension rate limit workaround
WebSearch
chrome extension screenshot canvas drawImage memory leak prevention cleanup
WebSearch
puppeteer "screenshot" "clip" region specific area code example

Research web page screenshot capture implementations
WebSearch
chrome.tabs.captureVisibleTab API full page screenshot limitations 2024
WebSearch
chrome.debugger API full page screenshot implementation
WebSearch
GoFullPage chrome extension how it works technical implementation
WebSearch
Playwright full page screenshot API lazy loading DPI 2024
WebSearch
Puppeteer screenshot full page viewport emulation best practices
WebSearch
chrome extension viewport stitching scroll capture implementation github
WebSearch
Selenium WebDriver full page screenshot workaround Python Java
WebSearch
lazy loading images detection scroll trigger intersection observer screenshot
WebSearch
device pixel ratio DPI high resolution screenshot puppeteer playwright
WebSearch
canvas size limit screenshot memory management chunking strategies
WebSearch
Fireshot Nimbus Screenshot Awesome Screenshot technical implementation approach
WebSearch
PNG vs JPEG screenshot compression file size optimization best practices
WebSearch
chrome.pageCapture API capabilities saveAsMHTML limitations
WebSearch
Apify screenshot API browserless.io screenshot implementation
WebSearch
network idle detection waitUntil networkidle0 networkidle2 best practices
WebSearch
infinite scroll detection handling screenshot capture implementation
WebSearch
GitHub screenshot chrome extension implementation code examples
WebSearch
screenshot tiling large pages chrome extension canvas workaround
WebSearch
print media CSS screenshot high quality PDF alternative
WebSearch
Chrome Firefox Safari screenshot API differences cross-browser compatibility
WebSearch
AShot library selenium screenshot stitching implementation Java
WebSearch
html2canvas alternative dom-to-image rasterizeHTML screenshot library comparison
WebSearch
Chrome DevTools Protocol Page.captureScreenshot full page implementation
WebSearch
WebP format screenshot advantages browser support 2024
WebSearch
fixed sticky elements duplicate screenshot scroll stitching workaround
WebSearch
"modern-screenshot" npm package implementation approach 2024
WebSearch
screenshot video memory GPU acceleration canvas Chrome
WebSearch
Playwright screenshot animations CSS transitions wait strategies
WebSearch
chrome extension background script content script screenshot coordination
WebSearch
ScreenshotAPI.net urlbox screenshotone API comparison features pricing
WebSearch
Chrome extension manifest v3 screenshot permissions activeTab scripting
WebSearch
Puppeteer Playwright screenshot JPEG quality compression settings optimization
WebSearch
screenshot element bounding box clip region implementation code
WebSearch
iframe screenshot cross-origin sandbox security CSP restrictions
WebSearch
screenshot performance optimization debouncing throttling batch processing
WebSearch
"shadow DOM" screenshot capture implementation challenges workarounds
WebSearch
Retina display HiDPI screenshot scaling Chrome extension implementation
WebSearch
screenshot CORS proxy image loading external resources CDN
WebSearch
progressive web app PWA screenshot service worker offline capabilities
WebSearch
screenshot watermark overlay canvas composition implementation
WebSearch
Chrome extension screenshot best practices 2024 2025 manifest v3
WebSearch
screenshot testing visual regression Percy Chromatic Applitools comparison
WebSearch
page height detection document.body.scrollHeight documentElement implementation
WebSearch
screenshot API rate limiting quota management best practices
WebSearch
blob URL data URL screenshot memory management conversion