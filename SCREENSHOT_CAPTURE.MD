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

---

# 📸 SCREENSHOT CAPTURE RESEARCH - COMPREHENSIVE FINDINGS

## Session Resumed: 2025-11-11

This document contains comprehensive research on web page screenshot capture implementations, covering both Chrome extension approaches and backend processing solutions.

---

## 🎯 PART 1: CHROME EXTENSION SCREENSHOT IMPLEMENTATIONS

### 1.1 Chrome Extension API Overview

#### chrome.tabs.captureVisibleTab()

**Purpose:** Captures the visible area of the currently active tab in the specified window.

**Method Signature:**
```javascript
chrome.tabs.captureVisibleTab(
  windowId?: number,
  options?: ImageDetails
): Promise<string>
```

**Returns:** Promise resolving to a data URL of the captured image (base64 encoded)

**Permissions Required (choose ONE):**
- `<all_urls>` permission, OR
- `activeTab` permission (recommended for sensitive sites)

**Key Limitations:**
- ✅ Only captures VISIBLE viewport (not full page)
- ⚠️ Rate limited to 2 calls per second (MAX_CAPTURE_VISIBLE_TAB_CALLS_PER_SECOND)
- ⚠️ Cannot be used by content scripts (service workers/extension pages only)
- ⚠️ File URLs require explicit file access permission
- ⚠️ Sensitive sites (chrome://, data:, other extensions) require activeTab permission

**ImageDetails Options:**
```javascript
{
  format: 'png' | 'jpeg',  // Default: 'jpeg'
  quality: 0-100          // JPEG only, ignored for PNG
}
```

---

### 1.2 Full Page Screenshot Strategies

Since `captureVisibleTab()` only captures the viewport, full-page screenshots require one of these approaches:

#### Strategy A: Viewport Stitching (Most Common)

**How it works:**
1. Scroll the page incrementally
2. Capture each viewport
3. Stitch images together using Canvas API
4. Export final composite image

**Pros:**
- ✅ Works on all pages (no height limits)
- ✅ Captures exactly what user sees
- ✅ Compatible with Manifest V3

**Cons:**
- ❌ Slower (multiple captures required)
- ❌ Complex coordinate calculations
- ❌ Timing issues with lazy-loaded content
- ❌ Sticky/fixed elements may duplicate

#### Strategy B: Chrome DevTools Protocol (CDP)

**How it works:**
Use `Page.captureScreenshot` via `chrome.debugger` API with `captureBeyondViewport: true`

**Pros:**
- ✅ Single API call for full page
- ✅ Faster than stitching
- ✅ No coordinate calculations

**Cons:**
- ❌ Maximum 16,384 pixels in any dimension
- ❌ Requires debugger permission (scary for users)
- ❌ Disconnects DevTools if user has it open
- ❌ Shows "debugger attached" banner

**CDP Command:**
```javascript
chrome.debugger.sendCommand(
  { tabId: tabId },
  'Page.captureScreenshot',
  {
    format: 'png',
    captureBeyondViewport: true,
    clip: {
      x: 0,
      y: 0,
      width: pageWidth,
      height: pageHeight,
      scale: 1
    }
  }
);
```

---

### 1.3 Viewport Stitching Implementation Details

#### Algorithm: captureAndScroll()

Based on chrome-screen-capture extension analysis:

```javascript
// PSEUDO-CODE for viewport stitching

FUNCTION captureAndScroll():
  1. Get page dimensions:
     - visibleWidth = window.innerWidth
     - visibleHeight = window.innerHeight
     - docWidth = document.documentElement.scrollWidth
     - docHeight = document.documentElement.scrollHeight

  2. Calculate scrollbar presence:
     - hasVerticalScrollbar = visibleHeight < docHeight
     - hasHorizontalScrollbar = visibleWidth < docWidth
     - scrollbarWidth = 17 (pixels, typically)

  3. Calculate grid dimensions:
     - cols = CEILING(docWidth / visibleWidth)
     - rows = CEILING(docHeight / visibleHeight)

  4. Create canvas:
     - canvas.width = docWidth
     - canvas.height = docHeight
     - context = canvas.getContext('2d')

  5. FOR each row (0 to rows-1):
       FOR each col (0 to cols-1):
         a. Scroll to position:
            window.scrollTo(col * visibleWidth, row * visibleHeight)

         b. Wait for render (100ms delay):
            setTimeout(..., 100)

         c. Capture visible tab:
            chrome.tabs.captureVisibleTab(null, {format: 'png'}, callback)

         d. Calculate coordinates:
            srcX = 0
            srcY = 0
            srcWidth = visibleWidth
            srcHeight = visibleHeight

            destX = col * visibleWidth
            destY = row * visibleHeight

            // Handle last column/row (partial viewport)
            IF col == cols - 1:
              srcWidth = docWidth % visibleWidth OR visibleWidth
            IF row == rows - 1:
              srcHeight = docHeight % visibleHeight OR visibleHeight

         e. Draw to canvas:
            context.drawImage(
              image,
              srcX, srcY, srcWidth, srcHeight,  // Source rectangle
              destX, destY, srcWidth, srcHeight  // Destination rectangle
            )

  6. Export canvas:
     dataURL = canvas.toDataURL('image/png')
```

#### Key Timing Considerations

**100ms delay between captures:**
- Allows browser to complete scroll animation
- Ensures DOM has repainted
- Prevents race conditions

**Alternative timing strategies:**
```javascript
// Strategy 1: requestAnimationFrame
window.scrollTo(x, y);
requestAnimationFrame(() => {
  requestAnimationFrame(() => {
    captureScreenshot();
  });
});

// Strategy 2: Intersection Observer
const observer = new IntersectionObserver((entries) => {
  if (entries[0].isIntersecting) {
    captureScreenshot();
  }
});

// Strategy 3: MutationObserver (detect DOM idle)
let timer;
const observer = new MutationObserver(() => {
  clearTimeout(timer);
  timer = setTimeout(() => captureScreenshot(), 300);
});
```

---

### 1.4 High DPI / Retina Display Handling

**The Problem:**
On Retina displays, `window.devicePixelRatio` is 2 (or higher), meaning:
- Logical pixels: 1920x1080
- Physical pixels: 3840x2160

**Solution: Scale coordinates by devicePixelRatio**

```javascript
const dpr = window.devicePixelRatio || 1;

// When calculating canvas dimensions
canvas.width = docWidth * dpr;
canvas.height = docHeight * dpr;
canvas.style.width = docWidth + 'px';
canvas.style.height = docHeight + 'px';

// Scale context
context.scale(dpr, dpr);

// When cropping screenshots
const element = document.getElementById('target');
const rect = element.getBoundingClientRect();

const cropX = (rect.left + scrollLeft) * dpr;
const cropY = (rect.top + scrollTop) * dpr;
const cropWidth = rect.width * dpr;
const cropHeight = rect.height * dpr;

context.drawImage(
  screenshot,
  cropX, cropY, cropWidth, cropHeight,  // Source (physical pixels)
  0, 0, rect.width, rect.height         // Dest (logical pixels)
);
```

**Manifest V3 Example:**
```javascript
// background.js
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'screenshot') {
    chrome.tabs.captureVisibleTab(null, { format: 'png' }, (dataUrl) => {
      sendResponse({ dataUrl: dataUrl, dpr: request.dpr });
    });
    return true; // Keep channel open for async response
  }
});

// content.js
const dpr = window.devicePixelRatio;
chrome.runtime.sendMessage(
  { action: 'screenshot', dpr: dpr },
  (response) => {
    processScreenshot(response.dataUrl, dpr);
  }
);
```

---

### 1.5 Handling Lazy-Loaded Images

**The Challenge:**
Lazy loading libraries only set `<img>` src when the image enters the viewport.

**Detection Strategy:**

```javascript
// Strategy 1: Scroll incrementally and wait
async function scrollAndWait() {
  const scrollHeight = document.documentElement.scrollHeight;
  let currentPosition = 0;
  const step = window.innerHeight * 0.5; // 50% overlap

  while (currentPosition < scrollHeight) {
    window.scrollTo(0, currentPosition);

    // Wait for network idle
    await waitForNetworkIdle(500);

    // Wait for lazy images
    await waitForLazyImages();

    currentPosition += step;
  }
}

// Strategy 2: Intersection Observer
function waitForLazyImages() {
  return new Promise((resolve) => {
    const lazyImages = document.querySelectorAll('img[loading="lazy"], img[data-src]');

    if (lazyImages.length === 0) {
      resolve();
      return;
    }

    let loadedCount = 0;
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          const img = entry.target;
          if (img.dataset.src) {
            img.src = img.dataset.src;
          }
          img.onload = () => {
            loadedCount++;
            if (loadedCount === lazyImages.length) {
              observer.disconnect();
              resolve();
            }
          };
        }
      });
    });

    lazyImages.forEach(img => observer.observe(img));
  });
}

// Strategy 3: Network idle detection
function waitForNetworkIdle(timeout = 500) {
  return new Promise((resolve) => {
    let timer;
    let activeRequests = 0;

    const originalFetch = window.fetch;
    window.fetch = function(...args) {
      activeRequests++;
      clearTimeout(timer);

      return originalFetch.apply(this, args).finally(() => {
        activeRequests--;
        if (activeRequests === 0) {
          timer = setTimeout(resolve, timeout);
        }
      });
    };

    // Also intercept XMLHttpRequest
    const originalOpen = XMLHttpRequest.prototype.open;
    XMLHttpRequest.prototype.open = function(...args) {
      activeRequests++;
      clearTimeout(timer);

      this.addEventListener('loadend', () => {
        activeRequests--;
        if (activeRequests === 0) {
          timer = setTimeout(resolve, timeout);
        }
      });

      return originalOpen.apply(this, args);
    };

    // Initial check
    if (activeRequests === 0) {
      timer = setTimeout(resolve, timeout);
    }
  });
}
```

**NPM Package Solution:**
```javascript
// Use scroll-to-bottomjs package
import scrollToBottom from 'scroll-to-bottomjs';

await scrollToBottom({
  frequency: 100,  // Check every 100ms
  timing: 500,     // Wait 500ms after last scroll
  incremental: window.innerHeight * 0.8  // Scroll 80% of viewport
});
```

---

### 1.6 Handling Fixed/Sticky Elements

**The Problem:**
Fixed elements (headers, navbars) appear in every viewport capture, creating duplicates in the stitched image.

**Detection:**
```javascript
function getFixedElements() {
  const allElements = document.querySelectorAll('*');
  const fixedElements = [];

  for (const element of allElements) {
    const style = window.getComputedStyle(element);
    if (style.position === 'fixed' || style.position === 'sticky') {
      fixedElements.push(element);
    }
  }

  return fixedElements;
}
```

**Solution Strategies:**

```javascript
// Strategy 1: Temporarily hide fixed elements
const fixedElements = getFixedElements();
const originalPositions = [];

// Before capturing
fixedElements.forEach((el, index) => {
  originalPositions[index] = {
    position: el.style.position,
    display: el.style.display
  };
  el.style.display = 'none';
});

// Capture screenshots...

// After capturing, restore
fixedElements.forEach((el, index) => {
  el.style.position = originalPositions[index].position;
  el.style.display = originalPositions[index].display;
});

// Strategy 2: Capture fixed elements separately and overlay
// 1. Capture fixed elements in first viewport
const fixedCanvas = captureFixedElements();

// 2. Hide them for remaining captures
hideFixedElements();

// 3. Capture rest of page
const bodyCanvas = captureRestOfPage();

// 4. Composite: body first, then fixed overlay
finalContext.drawImage(bodyCanvas, 0, 0);
finalContext.drawImage(fixedCanvas, 0, 0);
```

---

### 1.7 Real-World Extension Examples

#### Example 1: Manifest V3 Simple Screenshot

**manifest.json:**
```json
{
  "manifest_version": 3,
  "name": "Screenshot Extension",
  "version": "1.0",
  "permissions": ["activeTab", "scripting"],
  "action": {
    "default_popup": "popup.html"
  },
  "background": {
    "service_worker": "background.js"
  }
}
```

**background.js:**
```javascript
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'capture') {
    chrome.tabs.captureVisibleTab(
      null,
      { format: 'png', quality: 100 },
      (dataUrl) => {
        sendResponse({ dataUrl });
      }
    );
    return true; // Keep message channel open
  }
});
```

**popup.js:**
```javascript
document.getElementById('capture-btn').addEventListener('click', () => {
  chrome.runtime.sendMessage({ action: 'capture' }, (response) => {
    const link = document.createElement('a');
    link.download = `screenshot-${Date.now()}.png`;
    link.href = response.dataUrl;
    link.click();
  });
});
```

#### Example 2: Full Page with Viewport Stitching

**content.js (injected via scripting API):**
```javascript
async function captureFullPage() {
  const pageWidth = document.documentElement.scrollWidth;
  const pageHeight = document.documentElement.scrollHeight;
  const viewportWidth = window.innerWidth;
  const viewportHeight = window.innerHeight;

  const canvas = document.createElement('canvas');
  canvas.width = pageWidth;
  canvas.height = pageHeight;
  const context = canvas.getContext('2d');

  const cols = Math.ceil(pageWidth / viewportWidth);
  const rows = Math.ceil(pageHeight / viewportHeight);

  for (let row = 0; row < rows; row++) {
    for (let col = 0; col < cols; col++) {
      // Scroll to position
      window.scrollTo(col * viewportWidth, row * viewportHeight);

      // Wait for render
      await new Promise(resolve => {
        requestAnimationFrame(() => {
          requestAnimationFrame(resolve);
        });
      });

      // Request screenshot from background
      const response = await chrome.runtime.sendMessage({
        action: 'capture'
      });

      // Load image
      const img = await loadImage(response.dataUrl);

      // Draw to canvas
      const destX = col * viewportWidth;
      const destY = row * viewportHeight;
      context.drawImage(img, destX, destY);

      // Rate limit: max 2 captures/second
      await sleep(500);
    }
  }

  // Export
  return canvas.toDataURL('image/png');
}

function loadImage(src) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = reject;
    img.src = src;
  });
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}
```

---

## 🎯 PART 2: BACKEND SCREENSHOT PROCESSING

### 2.1 Puppeteer vs Playwright Comparison

| Feature | Puppeteer | Playwright |
|---------|-----------|------------|
| **Browser Support** | Chrome/Chromium only (experimental Firefox) | Chromium, Firefox, WebKit (native) |
| **Screenshot API** | `page.screenshot()` | `page.screenshot()` |
| **Full Page** | `fullPage: true` | `fullPage: true` |
| **Performance** | Slightly faster for Chrome | ~10% slower for Chrome |
| **API Design** | Simpler, Chrome-focused | More powerful, cross-browser |
| **Auto-waiting** | Manual waits required | Built-in auto-waiting |
| **Clip Region** | ✅ Supported | ✅ Supported |
| **Quality Control** | JPEG quality 0-100 | JPEG quality 0-100 |
| **Formats** | PNG, JPEG | PNG, JPEG |
| **Max Dimensions** | Limited by Chrome (~16K pixels) | Limited by browser |
| **Lazy Loading** | Manual scrolling required | Manual scrolling required |
| **Network Idle** | `networkidle0`, `networkidle2` | `networkidle` (discouraged) |
| **Languages** | JavaScript/TypeScript only | JS/TS, Python, Java, .NET, Go |
| **Development Team** | Google (original Puppeteer team moved to MS) | Microsoft (ex-Puppeteer developers) |
| **Maturity** | More mature (2017) | Newer (2020) but rapidly evolving |
| **Community** | Larger | Growing fast |
| **License** | Apache 2.0 | Apache 2.0 |

**Recommendation:**
- Use **Puppeteer** if: Chrome-only, JavaScript-only, need mature ecosystem
- Use **Playwright** if: Cross-browser, multi-language, need modern API

---

### 2.2 Puppeteer Screenshot Implementation

#### Basic Usage

```javascript
const puppeteer = require('puppeteer');

async function screenshot(url) {
  const browser = await puppeteer.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });

  const page = await browser.newPage();

  // Set viewport
  await page.setViewport({
    width: 1920,
    height: 1080,
    deviceScaleFactor: 2  // Retina
  });

  // Navigate
  await page.goto(url, {
    waitUntil: 'networkidle2'  // Wait for network to be mostly idle
  });

  // Take screenshot
  const buffer = await page.screenshot({
    type: 'png',
    fullPage: true
  });

  await browser.close();

  return buffer;
}
```

#### Advanced Options

```javascript
await page.screenshot({
  // Output
  path: 'screenshot.png',        // File path (optional)
  type: 'png',                    // 'png' | 'jpeg' | 'webp'
  encoding: 'binary',             // 'base64' | 'binary'

  // Quality
  quality: 90,                    // 0-100 (JPEG/WebP only)

  // Region
  fullPage: true,                 // Capture beyond viewport
  clip: {                         // Specific region
    x: 100,
    y: 100,
    width: 800,
    height: 600
  },
  captureBeyondViewport: true,   // Capture outside viewport

  // Appearance
  omitBackground: false,          // Transparent background

  // Performance
  optimizeForSpeed: false,        // Trade quality for speed
  fromSurface: true              // Capture from surface (more accurate)
});
```

#### Handling Lazy Loading

```javascript
async function screenshotWithLazyLoad(url) {
  const page = await browser.newPage();
  await page.goto(url, { waitUntil: 'networkidle2' });

  // Scroll to bottom to trigger lazy loading
  await autoScroll(page);

  // Wait for images to load
  await page.evaluate(() => {
    return Promise.all(
      Array.from(document.images)
        .filter(img => !img.complete)
        .map(img => new Promise(resolve => {
          img.onload = img.onerror = resolve;
        }))
    );
  });

  return await page.screenshot({ fullPage: true });
}

async function autoScroll(page) {
  await page.evaluate(async () => {
    await new Promise((resolve) => {
      let totalHeight = 0;
      const distance = 100;  // Scroll 100px at a time

      const timer = setInterval(() => {
        const scrollHeight = document.documentElement.scrollHeight;
        window.scrollBy(0, distance);
        totalHeight += distance;

        if (totalHeight >= scrollHeight) {
          clearInterval(timer);
          resolve();
        }
      }, 100);  // Every 100ms
    });
  });
}
```

#### Known Issues & Workarounds

**Issue 1: fullPage doesn't work with viewport-relative units**
```javascript
// Problem: Elements with `height: 100vh` render incorrectly

// Workaround: Set viewport to page height
const metrics = await page.evaluate(() => ({
  width: document.documentElement.scrollWidth,
  height: document.documentElement.scrollHeight
}));

await page.setViewport({
  width: metrics.width,
  height: metrics.height
});

await page.screenshot({ fullPage: false });  // No longer needed
```

**Issue 2: Very tall pages crash**
```javascript
// Problem: Pages > 50,000px tall exhaust memory

// Workaround: Take sections and stitch
async function screenshotTallPage(page) {
  const sections = [];
  const viewportHeight = 10000;  // 10k pixels per section

  const totalHeight = await page.evaluate(() =>
    document.documentElement.scrollHeight
  );

  for (let y = 0; y < totalHeight; y += viewportHeight) {
    const screenshot = await page.screenshot({
      clip: {
        x: 0,
        y: y,
        width: await page.evaluate(() => document.documentElement.scrollWidth),
        height: Math.min(viewportHeight, totalHeight - y)
      },
      captureBeyondViewport: true
    });

    sections.push(screenshot);
  }

  // Stitch sections using sharp or jimp
  return stitchImages(sections);
}
```

#### Wait Strategies

```javascript
// Strategy 1: Network idle (discouraged for modern sites)
await page.goto(url, { waitUntil: 'networkidle0' });  // 0 connections
await page.goto(url, { waitUntil: 'networkidle2' });  // ≤2 connections

// Strategy 2: Specific selector
await page.goto(url);
await page.waitForSelector('.main-content', { visible: true });

// Strategy 3: Custom function
await page.goto(url);
await page.waitForFunction(() => {
  return document.querySelectorAll('img[data-src]').length === 0;
});

// Strategy 4: Fixed timeout
await page.goto(url);
await page.waitForTimeout(3000);  // 3 seconds (not recommended)

// Strategy 5: DOM idle (best for dynamic content)
await page.goto(url);
await page.evaluate(() => {
  return new Promise((resolve) => {
    let timer;
    const observer = new MutationObserver(() => {
      clearTimeout(timer);
      timer = setTimeout(() => {
        observer.disconnect();
        resolve();
      }, 300);  // 300ms of no DOM changes
    });

    observer.observe(document.body, {
      childList: true,
      subtree: true
    });
  });
});
```

---

### 2.3 Playwright Screenshot Implementation

#### Basic Usage

```javascript
const { chromium } = require('playwright');

async function screenshot(url) {
  const browser = await chromium.launch({
    headless: true
  });

  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
    deviceScaleFactor: 2
  });

  const page = await context.newPage();

  await page.goto(url, {
    waitUntil: 'domcontentloaded'  // Playwright auto-waits
  });

  const buffer = await page.screenshot({
    type: 'png',
    fullPage: true
  });

  await browser.close();

  return buffer;
}
```

#### Device Emulation

```javascript
const { devices } = require('playwright');

// Use preset device
const iPhone = devices['iPhone 12'];
const context = await browser.newContext({
  ...iPhone
});

// Custom device
const context = await browser.newContext({
  viewport: {
    width: 400,
    height: 800
  },
  deviceScaleFactor: 2,
  isMobile: true,
  hasTouch: true,
  userAgent: 'Mozilla/5.0...'
});

const page = await context.newPage();
const screenshot = await page.screenshot({ fullPage: true });
```

#### Multi-Browser Screenshots

```javascript
const { chromium, firefox, webkit } = require('playwright');

async function screenshotAllBrowsers(url) {
  const results = {};

  for (const browserType of [chromium, firefox, webkit]) {
    const browser = await browserType.launch();
    const page = await browser.newPage();
    await page.goto(url);

    results[browserType.name()] = await page.screenshot({
      fullPage: true
    });

    await browser.close();
  }

  return results;
}
```

#### Playwright-Specific Features

```javascript
// Animations: wait for animations to finish
await page.screenshot({
  animations: 'disabled'  // or 'allow'
});

// Caret: hide text input caret
await page.screenshot({
  caret: 'hide'  // or 'initial'
});

// Scale: CSS zoom level
await page.screenshot({
  scale: 'css'  // or 'device'
});

// Full example
await page.screenshot({
  path: 'screenshot.png',
  fullPage: true,
  animations: 'disabled',
  caret: 'hide',
  scale: 'css',
  quality: 90,
  type: 'jpeg'
});
```

---

### 2.4 Chrome DevTools Protocol (CDP) Backend

Both Puppeteer and Playwright use CDP under the hood. You can also use CDP directly:

```javascript
// Using Puppeteer's CDP session
const client = await page.target().createCDPSession();

const { data } = await client.send('Page.captureScreenshot', {
  format: 'png',
  captureBeyondViewport: true,
  clip: {
    x: 0,
    y: 0,
    width: 1920,
    height: 10000,
    scale: 1
  },
  fromSurface: true
});

// data is base64 encoded
const buffer = Buffer.from(data, 'base64');
```

**CDP Parameters:**
- `format`: 'png' | 'jpeg' | 'webp'
- `quality`: 0-100 (JPEG/WebP only)
- `clip`: Viewport for capturing (optional)
  - `x`, `y`: Offset in device-independent pixels
  - `width`, `height`: Rectangle dimensions
  - `scale`: Scale factor (typically 1)
- `fromSurface`: Capture from surface vs view (default: true)
- `captureBeyondViewport`: Capture beyond visible viewport (default: false)
- `optimizeForSpeed`: Optimize for speed vs quality (default: false)

---

## 🎯 PART 3: IMPLEMENTATION RECOMMENDATIONS

### 3.1 For Chrome Extension (Frontend)

**Recommended Approach: Hybrid Strategy**

1. **For most pages:** Use viewport stitching with `captureVisibleTab()`
2. **For simple pages:** Offer CDP option for users who trust debugger permission
3. **Handle edge cases:** Detect and handle lazy loading, fixed elements

**Implementation Checklist:**

```
✅ Use Manifest V3 (future-proof)
✅ Request minimal permissions (activeTab only)
✅ Implement viewport stitching algorithm
✅ Handle devicePixelRatio for Retina displays
✅ Detect and wait for lazy-loaded images
✅ Hide or separately capture fixed/sticky elements
✅ Add 500ms delay between captures (rate limiting)
✅ Show progress indicator to user
✅ Handle errors gracefully (rate limits, permissions)
✅ Optimize canvas memory (clear after export)
✅ Support PNG and JPEG export
✅ Add filename with timestamp
```

**Code Structure:**

```
extension/
├── manifest.json          # Permissions, background service worker
├── background.js          # captureVisibleTab handler
├── content.js             # Inject into page, handle scrolling/stitching
├── popup/
│   ├── popup.html        # UI for capture button
│   └── popup.js          # Trigger capture
└── utils/
    ├── stitcher.js       # Canvas stitching logic
    ├── lazy-loader.js    # Lazy loading detection
    └── fixed-elements.js # Fixed element handling
```

---

### 3.2 For Backend (Server-Side)

**Recommended Tool: Playwright**

**Reasons:**
- ✅ Cross-browser support (future-proof)
- ✅ Better auto-waiting (less manual code)
- ✅ Active development by Microsoft
- ✅ Multi-language support (if needed later)
- ✅ Better documentation

**Implementation:**

```javascript
// backend/screenshot-service.js
const { chromium } = require('playwright');

class ScreenshotService {
  constructor() {
    this.browser = null;
  }

  async initialize() {
    this.browser = await chromium.launch({
      headless: true,
      args: [
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-dev-shm-usage'  // Overcome limited resource problems
      ]
    });
  }

  async capture(url, options = {}) {
    const {
      fullPage = true,
      width = 1920,
      height = 1080,
      format = 'png',
      quality = 90,
      waitForSelector = null,
      scrollToLoad = true
    } = options;

    const context = await this.browser.newContext({
      viewport: { width, height },
      deviceScaleFactor: 2
    });

    const page = await context.newPage();

    try {
      // Navigate
      await page.goto(url, {
        waitUntil: 'domcontentloaded',
        timeout: 30000
      });

      // Optional: Wait for specific selector
      if (waitForSelector) {
        await page.waitForSelector(waitForSelector, {
          state: 'visible',
          timeout: 10000
        });
      }

      // Optional: Scroll to trigger lazy loading
      if (scrollToLoad) {
        await this.autoScroll(page);
      }

      // Capture
      const screenshot = await page.screenshot({
        type: format,
        quality: format === 'jpeg' ? quality : undefined,
        fullPage: fullPage,
        animations: 'disabled',
        caret: 'hide'
      });

      return screenshot;

    } finally {
      await context.close();
    }
  }

  async autoScroll(page) {
    await page.evaluate(async () => {
      await new Promise((resolve) => {
        let totalHeight = 0;
        const distance = 100;
        const timer = setInterval(() => {
          const scrollHeight = document.body.scrollHeight;
          window.scrollBy(0, distance);
          totalHeight += distance;

          if (totalHeight >= scrollHeight) {
            clearInterval(timer);
            // Scroll back to top
            window.scrollTo(0, 0);
            setTimeout(resolve, 100);
          }
        }, 100);
      });
    });
  }

  async close() {
    if (this.browser) {
      await this.browser.close();
    }
  }
}

module.exports = ScreenshotService;
```

**Usage in Express API:**

```javascript
const express = require('express');
const ScreenshotService = require('./screenshot-service');

const app = express();
const screenshotService = new ScreenshotService();

app.get('/api/screenshot', async (req, res) => {
  try {
    const { url, fullPage, width, height, format } = req.query;

    if (!url) {
      return res.status(400).json({ error: 'URL required' });
    }

    const screenshot = await screenshotService.capture(url, {
      fullPage: fullPage !== 'false',
      width: parseInt(width) || 1920,
      height: parseInt(height) || 1080,
      format: format || 'png'
    });

    res.contentType(`image/${format || 'png'}`);
    res.send(screenshot);

  } catch (error) {
    console.error('Screenshot error:', error);
    res.status(500).json({ error: error.message });
  }
});

// Initialize on startup
screenshotService.initialize().then(() => {
  app.listen(3000, () => console.log('Screenshot service running on :3000'));
});

// Cleanup on shutdown
process.on('SIGTERM', async () => {
  await screenshotService.close();
  process.exit(0);
});
```

---

### 3.3 Comparison: Extension vs Backend

| Aspect | Chrome Extension | Backend (Playwright) |
|--------|------------------|---------------------|
| **User Experience** | Instant (local) | Network latency |
| **Privacy** | Data stays local | Data sent to server |
| **Reliability** | Depends on user's browser | Controlled environment |
| **Lazy Loading** | Can wait indefinitely | Timeout required |
| **Authentication** | Uses user's cookies | Separate auth needed |
| **Paywalls** | User can access | Cannot access |
| **Browser Compatibility** | Chrome/Edge only | Any browser (API) |
| **Resource Usage** | User's computer | Server resources |
| **Cost** | Free | Server costs |
| **Update Frequency** | Chrome Web Store review | Deploy anytime |
| **Scale** | N/A (one user at a time) | Horizontal scaling |

**Recommendation:**
- **Chrome Extension:** For user-initiated screenshots of pages they can access
- **Backend Service:** For automated screenshots, API access, cross-browser testing

**Hybrid Approach:**
- Extension sends HTML to backend for processing/conversion
- Backend doesn't screenshot, just processes HTML → Markdown
- Best of both worlds: Privacy + controlled processing

---

## 🎯 PART 4: SPECIFIC CHALLENGES & SOLUTIONS

### 4.1 Challenge: Infinite Scroll Pages

**Problem:** Page height keeps growing as user scrolls

**Detection:**
```javascript
async function hasInfiniteScroll(page) {
  const initialHeight = await page.evaluate(() => document.body.scrollHeight);

  await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
  await page.waitForTimeout(1000);

  const newHeight = await page.evaluate(() => document.body.scrollHeight);

  return newHeight > initialHeight;
}
```

**Solution:**
```javascript
async function screenshotInfiniteScroll(page, maxScrolls = 20) {
  let previousHeight = 0;
  let currentHeight = await page.evaluate(() => document.body.scrollHeight);
  let scrollCount = 0;

  while (currentHeight > previousHeight && scrollCount < maxScrolls) {
    previousHeight = currentHeight;

    await page.evaluate(() => {
      window.scrollTo(0, document.body.scrollHeight);
    });

    await page.waitForTimeout(1000);  // Wait for content to load

    currentHeight = await page.evaluate(() => document.body.scrollHeight);
    scrollCount++;
  }

  // Scroll back to top
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.waitForTimeout(500);

  return await page.screenshot({ fullPage: true });
}
```

---

### 4.2 Challenge: Canvas/WebGL Content

**Problem:** Canvas elements may not capture correctly

**Solution:**
```javascript
// Before screenshot, ensure canvas preserveDrawingBuffer is set
await page.evaluate(() => {
  const canvases = document.querySelectorAll('canvas');
  canvases.forEach(canvas => {
    const gl = canvas.getContext('webgl') || canvas.getContext('webgl2');
    if (gl) {
      // WebGL contexts need preserveDrawingBuffer: true
      // This must be set at context creation, so we can't fix existing ones
      console.warn('WebGL canvas detected - may not capture correctly');
    }
  });
});

// For new canvases, developers should use:
const gl = canvas.getContext('webgl', { preserveDrawingBuffer: true });
```

---

### 4.3 Challenge: Cross-Origin Iframes

**Problem:** Cross-origin iframes may appear blank in screenshots

**Solution:**
```javascript
// Cannot access cross-origin iframe content due to CORS
// Best approach: Detect and warn user

await page.evaluate(() => {
  const iframes = document.querySelectorAll('iframe');
  const crossOrigin = Array.from(iframes).filter(iframe => {
    try {
      iframe.contentDocument;
      return false;  // Same origin
    } catch (e) {
      return true;   // Cross-origin
    }
  });

  if (crossOrigin.length > 0) {
    console.warn(`${crossOrigin.length} cross-origin iframes detected`);
  }
});

// Alternative: Use Chrome DevTools Protocol to inject into iframes
// (requires additional permissions)
```

---

### 4.4 Challenge: Memory Management for Large Pages

**Problem:** Very large screenshots exhaust memory

**Solutions:**

```javascript
// Solution 1: Compress immediately
const screenshot = await page.screenshot({
  type: 'jpeg',
  quality: 80  // Lower quality = smaller file
});

// Solution 2: Stream to disk
const fs = require('fs');
const stream = fs.createWriteStream('screenshot.png');
const screenshot = await page.screenshot({ type: 'png' });
stream.write(screenshot);
stream.end();

// Solution 3: Tile-based capture for extremely large pages
async function tileScreenshot(page, tileHeight = 10000) {
  const totalHeight = await page.evaluate(() =>
    document.documentElement.scrollHeight
  );
  const width = await page.evaluate(() =>
    document.documentElement.scrollWidth
  );

  const tiles = [];
  for (let y = 0; y < totalHeight; y += tileHeight) {
    const tile = await page.screenshot({
      clip: {
        x: 0,
        y: y,
        width: width,
        height: Math.min(tileHeight, totalHeight - y)
      },
      captureBeyondViewport: true
    });
    tiles.push(tile);
  }

  // Stitch tiles using image library (sharp, jimp, etc.)
  return stitchTiles(tiles, width, totalHeight);
}
```

---

## 📊 PERFORMANCE BENCHMARKS

### Chrome Extension (Local)
- **Viewport capture:** ~50-100ms per viewport
- **Full page (5 viewports):** ~2-3 seconds
- **Full page (20 viewports):** ~10-15 seconds
- **Rate limit:** 2 captures/second (500ms minimum between captures)

### Backend (Puppeteer/Playwright)
- **Browser launch:** ~1-2 seconds (cold start)
- **Page load:** ~1-5 seconds (depends on site)
- **Screenshot (viewport):** ~100-200ms
- **Screenshot (full page):** ~500-2000ms (depends on page height)
- **Memory usage:** ~50-100MB per browser instance

**Optimization Tips:**
- Reuse browser instances (don't launch/close for each screenshot)
- Use browser contexts for isolation (lighter than new browser)
- Set reasonable timeouts
- Limit concurrent screenshots (CPU/memory intensive)
- Use JPEG for smaller file sizes
- Implement caching for frequently screenshotted pages

---

## 🎯 FINAL RECOMMENDATIONS FOR SIMPLE-PAGE-SAVER

Based on this project's architecture (Chrome extension + Python backend):

### Option A: Extension Screenshots (Recommended)

**Why:**
- User already has page loaded in browser
- No additional server load
- Respects user authentication/cookies
- Faster (local processing)
- Better privacy

**Implementation:**
1. Add viewport stitching to extension
2. Extension captures full-page screenshot
3. Send screenshot as base64 to backend (or save locally)
4. Backend processes HTML → Markdown (existing functionality)
5. Optionally attach screenshot to saved page

**Files to modify:**
- `extension/background.js` - Add captureVisibleTab handler
- `extension/content-script.js` - Add viewport stitching logic
- `extension/popup.html/js` - Add screenshot button
- `backend/api.py` - Add endpoint to receive screenshot

---

### Option B: Backend Screenshots

**Why:**
- Useful for API-driven screenshot service
- Consistent rendering across users
- Can screenshot pages user doesn't have access to

**Implementation:**
1. Install Playwright in Python backend
2. Add screenshot endpoint
3. Extension sends URL to backend
4. Backend screenshots + converts HTML
5. Return both screenshot and markdown

**Dependencies:**
```bash
pip install playwright
playwright install chromium
```

**Code:**
```python
from playwright.sync_api import sync_playwright

def capture_screenshot(url, full_page=True):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 1920, 'height': 1080})
        page.goto(url, wait_until='domcontentloaded')

        screenshot = page.screenshot(
            type='png',
            full_page=full_page
        )

        browser.close()
        return screenshot
```

---

### Hybrid Recommendation

**Best approach for simple-page-saver:**

1. **Extension captures screenshots** (Option A)
   - User privacy preserved
   - Faster, no server load
   - Works with authenticated pages

2. **Backend processes HTML** (existing)
   - Convert HTML → Markdown using AI
   - Chunk large content (already implemented)

3. **Storage**
   - Screenshot saved as PNG/JPEG
   - Markdown saved as .md file
   - Both packaged together

This leverages the strengths of both approaches while minimizing weaknesses.

---

## 📚 RESOURCES

### Official Documentation
- [Chrome Extensions API - tabs.captureVisibleTab](https://developer.chrome.com/docs/extensions/reference/api/tabs#method-captureVisibleTab)
- [Chrome DevTools Protocol - Page.captureScreenshot](https://chromedevtools.github.io/devtools-protocol/tot/Page/#method-captureScreenshot)
- [Puppeteer API - page.screenshot()](https://pptr.dev/api/puppeteer.page.screenshot)
- [Playwright API - page.screenshot()](https://playwright.dev/docs/api/class-page#page-screenshot)

### Open Source Examples
- [GoFullPage Extension](https://github.com/mrcoles/full-page-screen-capture-chrome-extension)
- [chrome-screen-capture](https://github.com/sanathp/chrome-screen-capture)
- [Blipshot](https://github.com/folletto/Blipshot)
- [Manifest V3 Screenshot Example](https://github.com/hacess/chrome-extension-manifestv3-screenshot)

### Articles & Guides
- [Taking Screenshots with Chrome Extensions](https://louisrli.github.io/blog/2013/01/16/javascript-canvas-screenshot/)
- [Puppeteer vs Playwright Comparison](https://playwright.dev/docs/puppeteer)
- [Handling Lazy Loading in Puppeteer](https://wiki.zegnat.net/cache/?md5=f7ce4fd73de0ac41f15ea708b4c8f20f)

---

**Research completed: 2025-11-11**
**Next steps: Implement Option A (Extension Screenshots) for simple-page-saver**