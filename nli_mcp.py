"""
National Library of Israel MCP Server
Machine Consumable Provider (MCP) for searching the Israeli National Library (NLI).
Provides search, image, manifest, and streaming endpoints.
"""

import asyncio
import json
import os
from typing import Any, Dict, List

import httpx
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import (
    Resource,
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
    LoggingLevel
)
from pydantic import BaseModel

# Configurations
NLI_API_KEY = os.getenv("NLI_API_KEY", "OHOwpHbdR3Kt6p4S7qjBHddpUam0jHBMsvF5gXPz")
BASE_SEARCH_URL = "https://api.nli.org.il/openlibrary/search"
BASE_IIIF_IMAGE = "https://iiif.nli.org.il/IIIFv21"
BASE_IIIF_MANIFEST = f"{BASE_IIIF_IMAGE}/{{recordId}}/manifest"

class SearchResponse(BaseModel):
    total_results: int
    items: list

# Create server instance
server = Server("nli_mcp")

# System instructions from plugin.json
QUERY_PROCESSING_INSTRUCTIONS = """You are an expert system for converting natural language user queries into multiple structured JSON parameters for an API search endpoint.
Your ONLY output MUST be a valid JSON array of objects, where each object represents a separate query. Do NOT include any introductory or concluding text, explanations, or markdown formatting (like ```json). Just the raw JSON array.

**Process the user's query step-by-step to accurately extract multiple parameters for the API call:**
1. **Understand User Intent:** Determine the primary goal (e.g., searching books by multiple Israeli authors with a specific theme).
2. **Identify Relevant API Parameters:** Map the intent to the most appropriate API parameters.
3. **Parameter Extraction Guidelines:**
    * Extract ALL relevant parameters: 'creator', 'subject', 'materialType', etc., in addition to 'q'.
    * **'q' (Main Query):** Use format: **'field,operator,value'**. Fields: 'any', 'title', 'desc', 'creator', 'subject', 'dr_s', 'dr_e'. Operators: 'contains', 'exact'.
    * **Names & Entities:** Infer full names (e.g., 'Bialik' -> 'חיים נחמן ביאליק').
    * **'materialType':** Use ONLY: 'books', 'articles', 'images', 'audio', 'videos', 'maps', 'journals', 'manuscripts', 'rareBooks'.
4. **Deep Query Analysis for Complex Requests:**
    * For queries like 'ספרים לילדים בסגנון כיפה אדומה אבל של סופרים ישראלים':
        * Theme: From 'כיפה אדומה', infer 'מעשיות', 'ספרות ילדים קלאסית', 'סיפורי עם' for 'q' or 'subject'.
        * Authors: Identify well‑known Israeli children's authors (e.g., לאה גולדברג, גלילה רון פדר) based on common knowledge (no external lookups). Create a separate query for each.
        * Material: 'ספרים לילדים' implies `materialType: books`.
    * Generate multiple JSON objects, one per author, combining theme and material type.
5. **Construct Final JSON Array:** Each object MUST have 'q' correctly formatted. All values as strings.

**Limit Parameter Guidelines:**
    * Use the 'limit' parameter ONLY to restrict the number of search results returned by the API, not to specify a desired number of final items.
    * Valid usage: When the user explicitly requests a limited number of search results, e.g., 'Give me only the first 10 search results for books by Bialik' → include 'limit': '10'.
    * Invalid usage:
        - Requests for 'the last N results' (e.g., 'Give me the last 10 books') are NOT valid.
        - Requests for a specific number of final items (e.g., 'Give me 20 books by Bialik') are NOT valid.
    * If the user's request for 'limit' is invalid, omit the 'limit' parameter in the JSON output."""

RESPONSE_GENERATION_INSTRUCTIONS = """After retrieving search results, the AI must extract images and then generate a user-facing response:
1. From each item in 'context.results', check the 'thumbnail' field. If it's a valid URL, add {recordId, title, thumbnailUrl} to 'items_images'.
2. For items without a valid thumbnail, call GET /api/v1/manifest/{recordId}, parse sequences→canvases→images, and select the first URL ending in .jpg or .png (excluding 'logo'). Add that to 'items_images'.
3. Ensure 'items_images' is a list of objects: {recordId, title, thumbnailUrl}.
4. Do not add an item to 'items_images' if no valid image exists."""

SYSTEM_INSTRUCTIONS = """These instructions apply AFTER the search results have been retrieved and AFTER the items_images list has been created from the context and manifest data.

You are an advanced AI assistant for the National Library of Israel. Your goal is to take a user's natural-language question and a set of JSON-formatted search results (context), along with the list of all the items that have image URLs (items_images list). This list contains dictionaries that include recordId and their image link.

You must deliver a precise, well-structured answer in Hebrew, or in English if the user's question is in English. The context contains multiple search results under 'results'. Analyze each relevant result, extract pertinent items, and combine them into a cohesive response directly addressing the user's question. Format answers in complete sentences, using clear and user-friendly language in the appropriate language (Hebrew or English), keeping the answer relevant to the user's question and simple to understand.

If no matching data is available, explicitly state that no results were found.

Include photos of the items in the answer, but only if they are relevant to the question and only if they are available in the items_images (meaning the relevant chosen item from the context has the same recordId that exists in the items_images list).

Use the image URL from the items_images list that you created before. If there is no image URL for the item in the items_images list, you may use the image URL from the context, but only if it is relevant to the question.

If the item has no image, do not include it in the response.

If the item has an image, include it in the response itself - show the photo from the image URL from the items_images list. If there is no image URL in the items_images list, you can use the image URL from the context, but only if it is relevant to the question.

Place the image in a logical way in the text that does not break the text flow or the UI view.

Ensure that when multiple images are included in an answer, they are arranged in a logical and visually appealing way that maintains the flow of the text. Avoid overwhelming the user by placing too many images in the middle of the content or disrupting the reading experience. For example, put all of them at the end of the answer if it is logical.

Always include links to item pages whenever possible, using the 'id' field from the context to form URLs in the format 'https://www.nli.org.il/en/articles/NNL_ALEPH990020376560205171'.

Do not put the link separate from the text like this: 'https://www.nli.org.il/en/articles/NNL_ALEPH990020376560205171'. Instead, make the item's name a clickable link, for example: if the answer mentions the book 'around the world', the link should be on the book title.

If the user asks specifically for the number of search results, calculate them and answer.
"""

searchSchema =  {
                    "type": "object",
                    "properties": {
                        "q": {
                            "type": "string",
                            "description": "Main search query in 'field,operator,value' format, e.g. 'creator,contains,דוד בן גוריון'."
                        },
                        "output_format": {
                            "type": "string",
                            "description": "Response format: json or xml.",
                            "default": "json"
                        },
                        "count_only": {
                            "type": "boolean",
                            "description": "If true, return only the total result count.",
                            "default": False
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum search results per page (for the query, not the final user results).",
                            "minimum": 1,
                            "maximum": 500,
                            "default": 100
                        },
                        "offset": {
                            "type": "integer",
                            "description": "Pagination offset.",
                            "minimum": 0,
                            "default": 0
                        },
                        "materialType": {
                            "type": "string",
                            "description": "Filter by material type (books, articles, images, etc.)."
                        },
                        "availabilityType": {
                            "type": "string",
                            "description": "Filter by availability type."
                        },
                        "sortField": {
                            "type": "string",
                            "description": "Sort results by this field."
                        },
                        "sortOrder": {
                            "type": "string",
                            "description": "asc or desc."
                        },
                        "facet_field": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Facet fields to include."
                        },
                        "facet_limit": {
                            "type": "integer",
                            "description": "Limit number of facet results."
                        },
                        "facet_offset": {
                            "type": "integer",
                            "description": "Offset for facets."
                        },
                        "facet_sort": {
                            "type": "string",
                            "description": "Facet sort order."
                        },
                        "fields": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Which fields to return in the result."
                        },
                        "lang": {
                            "type": "string",
                            "description": "Limit by item language."
                        },
                        "creator": {
                            "type": "string",
                            "description": "Filter by creator name."
                        },
                        "subject": {
                            "type": "string",
                            "description": "Filter by subject."
                        },
                        "publisher": {
                            "type": "string",
                            "description": "Filter by publisher."
                        },
                        "publicationYearFrom": {
                            "type": "integer",
                            "description": "Filter by publication start year."
                        },
                        "publicationYearTo": {
                            "type": "integer",
                            "description": "Filter by publication end year."
                        },
                        "collection": {
                            "type": "string",
                            "description": "Filter by collection."
                        },
                        "contributor": {
                            "type": "string",
                            "description": "Filter by contributor."
                        },
                        "isbn": {
                            "type": "string",
                            "description": "Filter by ISBN."
                        },
                        "issn": {
                            "type": "string",
                            "description": "Filter by ISSN."
                        },
                        "dateFrom": {
                            "type": "string",
                            "description": "Filter by start date."
                        },
                        "dateTo": {
                            "type": "string",
                            "description": "Filter by end date."
                        }
                    },
                    "required": ["q"]
                }
@server.list_tools()
async def handle_list_tools() -> List[Tool]:
    """List available tools for the NLI MCP server."""
    return [
        Tool(
            name="process_natural_query",
            description="First to use: Process natural language queries and convert them to structured search parameters according to NLI MCP instructions.",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_query": {
                        "type": "string",
                        "description": "Natural language query from the user that needs to be processed into structured search parameters."
                    }
                },
                "required": ["user_query"]
            }
        ),
        Tool(
            name="generate_response",
            description="Second to use: Generate a user-facing response from search results with images extraction and formatting.",
            inputSchema={
                "type": "object",
                "properties": {
                    **searchSchema["properties"],  # unpack all the searchSchema fields
                    "user_query": {
                        "type": "string",
                        "description": "Original user query to provide context for the response."
                    }
                },
                "required": ["user_query", "q"]
            }
        ),
        Tool(
            name="stream_batches",
            description="Third to use: Process large result sets in streaming batches for comprehensive analysis. Use when you need to analyze many results systematically.",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_query": {
                        "type": "string",
                        "description": "Original user query to provide context for the response."
                    },
                    "search_data": {
                        "type": "object",
                        "description": "Complete search results data containing items array and metadata."
                    },
                    "items_images": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "recordId": {"type": "string"},
                                "title": {"type": "string"},
                                "thumbnailUrl": {"type": "string"}
                            }
                        },
                        "description": "Array of items with their image URLs."
                    },
                    "offset": {
                        "type": "integer",
                        "description": "Starting offset for batch processing.",
                        "default": 0
                    },
                    "batch_size": {
                        "type": "integer",
                        "description": "Number of items to process in each batch.",
                        "default": 10
                    }
                },
                "required": ["user_query", "search_data", "items_images"]
            }
        ),
        Tool(
            name="get_image",
            description="Retrieve an image by IIIF identifier.",
            inputSchema={
                "type": "object",
                "properties": {
                    "identifier": {
                        "type": "string",
                        "description": "Unique identifier of the IIIF image."
                    },
                    "region": {
                        "type": "string",
                        "description": "IIIF region (default: full).",
                        "default": "full"
                    },
                    "size": {
                        "type": "string",
                        "description": "IIIF size (default: max).",
                        "default": "max"
                    },
                    "rotation": {
                        "type": "number",
                        "description": "Image rotation.",
                        "default": 0.0
                    },
                    "quality": {
                        "type": "string",
                        "description": "Image quality (default: default).",
                        "default": "default"
                    },
                    "format": {
                        "type": "string",
                        "description": "Image format (default: jpg).",
                        "default": "jpg"
                    }
                },
                "required": ["identifier"]
            }
        ),
        Tool(
            name="get_manifest",
            description="Retrieve the IIIF manifest for a given recordId.",
            inputSchema={
                "type": "object",
                "properties": {
                    "recordId": {
                        "type": "string",
                        "description": "Unique record ID from the library."
                    }
                },
                "required": ["recordId"]
            }
        ),
        Tool(
            name="get_stream",
            description="Retrieve media streams (mp4, hls, audio) for an item.",
            inputSchema={
                "type": "object",
                "properties": {
                    "itemId": {
                        "type": "string",
                        "description": "Unique item ID from the library."
                    },
                    "format": {
                        "type": "string",
                        "description": "Stream type to return: mp4, hls, audio, or all.",
                        "default": "all"
                    }
                },
                "required": ["itemId"]
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle tool calls for the NLI MCP server."""
    
    if name == "process_natural_query":
        return await handle_process_natural_query(arguments)
    elif name == "generate_response":
        return await handle_generate_response(arguments)
    elif name == "stream_batches":
        return await stream_batches(arguments)
    elif name == "get_image":
        return await handle_get_image(arguments)
    elif name == "get_manifest":
        return await handle_get_manifest(arguments)
    elif name == "get_stream":
        return await handle_get_stream(arguments)
    else:
        raise ValueError(f"Unknown tool: {name}")

async def handle_search_nli(arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle search requests to the NLI API."""
    
    q = arguments["q"]
    output_format = arguments.get("output_format", "json")
    count_only = arguments.get("count_only", False)
    limit = arguments.get("limit")
    offset = arguments.get("offset", 0)
    materialType = arguments.get("materialType")
    availabilityType = arguments.get("availabilityType")
    sortField = arguments.get("sortField")
    sortOrder = arguments.get("sortOrder")
    facet_field = arguments.get("facet_field", [])
    facet_limit = arguments.get("facet_limit")
    facet_offset = arguments.get("facet_offset")
    facet_sort = arguments.get("facet_sort")
    fields = arguments.get("fields", [])
    lang = arguments.get("lang")
    creator = arguments.get("creator")
    subject = arguments.get("subject")
    publisher = arguments.get("publisher")
    publicationYearFrom = arguments.get("publicationYearFrom")
    publicationYearTo = arguments.get("publicationYearTo")
    collection = arguments.get("collection")
    contributor = arguments.get("contributor")
    isbn = arguments.get("isbn")
    issn = arguments.get("issn")
    dateFrom = arguments.get("dateFrom")
    dateTo = arguments.get("dateTo")

    params = {
        "api_key": NLI_API_KEY,
        "query": q,
        "output_format": output_format,
        "rows": limit,
        "start": offset
    }

    optional = {
        "material_type": materialType,
        "availability_type": availabilityType,
        "sortField": sortField,
        "sort_order": sortOrder,
        "language": lang,
        "creator": creator,
        "subject": subject,
        "publisher": publisher,
        "publication_year_from": publicationYearFrom,
        "publication_year_to": publicationYearTo,
        "collection": collection,
        "contributor": contributor,
        "isbn": isbn,
        "issn": issn,
        "start_date": dateFrom,
        "end_date": dateTo
    }

    for key, val in optional.items():
        if val is not None:
            params[key] = val

    if facet_field:
        params["facet.field"] = facet_field
    if facet_limit is not None:
        params["facet.limit"] = facet_limit
    if facet_offset is not None:
        params["facet.offset"] = facet_offset
    if facet_sort:
        params["facet.sort"] = facet_sort
    if fields:
        params["fields"] = ",".join(fields)

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(BASE_SEARCH_URL, params=params)
            response.raise_for_status()

        data = response.json()
      
        if isinstance(data, list):
            total = len(data)
            items = data
            if count_only:
                pass 
            result = {"total_results": total, "items": items[offset:offset+limit]}
        else:
            total = data.get("total_results", 0)
            if count_only:
                pass
            items = data.get("items", [])
            result = {"total_results": total, "items": items[offset:offset + limit]}

        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]
    
    except Exception as e:
        return [TextContent(type="text", text=f"Error searching NLI: {str(e)}")]

async def handle_process_natural_query(arguments: Dict[str, Any]) -> List[TextContent]:
    """Process natural language queries into structured search parameters."""
    
    user_query = arguments.get("user_query")
    # This function processes the natural language query according to the instructions
    # In a real implementation, this would use NLP/AI to convert the query
    # For now, we'll return the instructions for how to process it
    
    instructions = f"""{QUERY_PROCESSING_INSTRUCTIONS}

                    User query: '{user_query}'

                    Based on the instructions above, this query should be processed to extract:
                    - Main search parameters (q, materialType, creator, subject, etc.)
                    - Multiple query objects if needed (e.g., for multiple authors)
                    - Proper formatting for the NLI API

                    Please process this query according to the detailed instructions provided."""

    return [TextContent(type="text", text=instructions)]

async def handle_generate_response(arguments: Dict[str, Any]) -> List[TextContent]:
    """
    Generate user-facing response from natural language query with streaming batches.
    Returns exact search numbers and provides option to continue getting more results.
    """
    # Validate arguments first
    if not arguments:
        return [TextContent(type="text", text="No arguments provided", is_error=True)]
    
    user_query = arguments.get("user_query")
    if not user_query:
        return [TextContent(type="text", text="Missing user_query parameter", is_error=True)]
            
    
    try:
        # Extract search parameters from arguments
        search_params = {key: value for key, value in arguments.items() 
                        if key != "user_query" and key !="limit" and value is not None}
        search_params["limit"] = 3
        # Perform the search
        search_result = await handle_search_nli(search_params)
        try:
            search_data = json.loads(search_result[0].text)
        except json.JSONDecodeError as json_err:
            return [TextContent(type="text", text=f"Failed to parse search results: {json_err}")]
        except Exception as e:
            return [TextContent(type="text", text=f"Unexpected error processing search results: {str(e)}")]        
        # Extract total results and current batch info
        total_results = search_data.get("total_results", 0)
        current_items = search_data.get("items", [])
        current_offset = search_data.get("offset", 0)
        current_limit = search_data.get("limit", 3)
        
        # Calculate result range
        results_start = current_offset + 1
        results_end = min(total_results - current_offset, current_offset + 3)
        
        # Process items to extract thumbnails or prepare manifest fetching
        items_images = []
        items_for_manifest = []
        manifest_tasks = []

        for item in current_items:
            record_id = get_simple_field(item, "http://purl.org/dc/elements/1.1/recordid")  # Use 'recordId' for manifest
            title = get_simple_field(item, "http://purl.org/dc/elements/1.1/title")
            thumbnail = get_simple_field(
                item, "http://purl.org/dc/elements/1.1/thumbnail")

            if ((not thumbnail or thumbnail and not thumbnail.startswith(("http://", "https://"))) and record_id != None):
                items_for_manifest.append((record_id, title))
                manifest_tasks.append(handle_get_manifest({"recordId": record_id}))
            else:
                if thumbnail and thumbnail.startswith(("http://", "https://")):
                    # If thumbnail is a valid URL, add to items_images
                    items_images.append({
                        "recordId": record_id,
                        "title": title,
                        "thumbnailUrl": thumbnail
                    })
 
        # Parallel manifest fetching and processing
        if manifest_tasks:
            manifest_results = await asyncio.gather(*manifest_tasks, return_exceptions=True)

            for (record_id, title), result in zip(items_for_manifest, manifest_results):
                if isinstance(result, Exception):
                    continue
                try:
                    manifest_data = json.loads(result[0].text)
                    sequences = manifest_data.get("sequences", [])
                    if sequences:
                        canvases = sequences[0].get("canvases", [])
                        image_url = next(
                            (
                                img.get("resource", {}).get("@id", "")
                                for canvas in canvases
                                for img in canvas.get("images", [])
                                if img.get("resource", {}).get("@id", "").lower().endswith((".jpg", ".png"))
                                and "logo" not in img.get("resource", {}).get("@id", "").lower()
                            ),
                            None
                        )
                        if image_url:
                            items_images.append({
                                "recordId": record_id,
                                "title": title,
                                "thumbnailUrl": image_url
                            })
                except Exception:
                    continue

        # Build comprehensive response with exact numbers
        has_more_results = results_end < total_results
        next_offset = current_offset + current_limit if has_more_results else None
        
        # Create the main response with result statistics
        response_instructions = f"""{SYSTEM_INSTRUCTIONS}

                                === SEARCH RESULTS SUMMARY ===
                                Total results found: {total_results}
                                Showing results: {results_start}-{results_end} of {total_results}
                                Current batch size: {len(current_items)}
                                {'More results available' if has_more_results else 'All results shown'}

                                === CONTINUATION OPTIONS ===
                                {f"To get next batch, use offset={next_offset}" if has_more_results else "No more results available"}

                                Context (search results): {json.dumps(search_data, ensure_ascii=False, indent=2)}

                                Items with images: {json.dumps(items_images, ensure_ascii=False, indent=2)}

                                User query: '{user_query}'

                                Based on the context and items_images above, generate a comprehensive response following all the instructions provided.

                                IMPORTANT: Include the exact search statistics in your response:
                                - Total results: {total_results}
                                - Currently showing: {results_start}-{results_end}
                                - {f"To see more results, the user can ask for the next {current_limit} results" if has_more_results else "This shows all available results"}
                                """

        responses = [TextContent(type="text", text=response_instructions)]
        
        # If there are more results, add a continuation prompt
        if has_more_results:
            continuation_prompt = f"""
                                === CONTINUATION AVAILABLE ===
                                There are {total_results - results_end} more results available.
                                To continue viewing more results, you can:
                                1. Ask for "next {current_limit} results" 
                                2. Specify a different offset (next batch starts at offset {next_offset})
                                3. Request a specific range of results

                                The search query can be continued with the same parameters plus offset={next_offset}
                                """
            responses.append(TextContent(type="text", text=continuation_prompt))

        return responses

    except Exception as e:
        return [TextContent(type="text", text=f"Error processing query: {str(e)}")]

# --- Helper function to extract simple values ---
def extract_value_from_json(value: str) -> str:
    try:
        parsed = json.loads(value.replace("'", '"'))
        if isinstance(parsed, dict) and '@value' in parsed:
            return str(parsed['@value']).strip()
    except json.JSONDecodeError:
        pass
    if isinstance(value, list):
        return str(value[0]).strip() if value else None
    else:
        return value.strip() if not None else None

def get_simple_field(item: dict, key_name: str) -> str:
    value = item.get(key_name)
    
    if isinstance(value, str):
        if "@value" in value:
            return extract_value_from_json(str(value))
    
    if isinstance(value, list):
        if "@value" in value[0]:
            return extract_value_from_json(str(value[0]))
    return str(value).strip() if value is not None else None

async def stream_batches(
    user_query: str,
    search_data: Dict[str, Any],
    items_images: List[Dict[str, str]],
    offset: int,
    batch_size: int
) -> List[TextContent]:
    """
    Stream results in batches, calling itself recursively to process all items.
    Provides exact count information and continuation options.
    """
    items = search_data.get("items", [])
    total_results = search_data.get("total_results", 0)
    
    # If no more items to display, return completion message
    if offset >= len(items):
        final_prompt = f"""{SYSTEM_INSTRUCTIONS}

                    === BATCH PROCESSING COMPLETE ===
                    Finished processing all {len(items)} items from the current search batch.
                    Total results in database: {total_results}

                    All recordIds and images have been processed for query: '{user_query}'

                    You can now build the final comprehensive response from all the accumulated data.
                    """
        return [TextContent(type="text", text=final_prompt)]
    
    # Create partial context for current batch
    context_part = dict(search_data)  # shallow copy
    context_part["items"] = items[offset:offset+batch_size]
    next_offset = offset + batch_size
    
    # Calculate current batch info
    batch_start = offset + 1
    batch_end = min(offset + batch_size, len(items))
    
    prompt = f"""{SYSTEM_INSTRUCTIONS}

            === BATCH PROCESSING ===
            Processing batch: items {batch_start}-{batch_end} of {len(items)} (from total {total_results} in database)

            Context (current batch):  
            {json.dumps(context_part['items'], ensure_ascii=False, indent=2)}

            Items with images:  
            {json.dumps(items_images, ensure_ascii=False, indent=2)}

            User query: "{user_query}"

            === INSTRUCTION ===
            - If you have sufficient information to answer the question, provide the answer now
            - If you need more context, respond exactly with (no additional words):  
            NEED_MORE_CONTEXT: next_offset={next_offset}

            === BATCH STATUS ===
            Current batch: {batch_start}-{batch_end} of {len(items)} items
            Remaining items: {max(0, len(items) - batch_end)}
            """
    
    # Collect current response
    responses = [TextContent(type="text", text=prompt)]
    
    # Recursively call for next batch
    more_responses = await stream_batches(
        user_query=user_query,
        search_data=search_data,
        items_images=items_images,
        offset=next_offset,
        batch_size=batch_size
    )
    responses.extend(more_responses)
    
    return responses

async def handle_get_image(arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle image retrieval requests."""
    
    identifier = arguments["identifier"]
    region = arguments.get("region", "full")
    size = arguments.get("size", "max")
    rotation = arguments.get("rotation", 0.0)
    quality = arguments.get("quality", "default")
    fmt = arguments.get("format", "jpg")

    url = f"{BASE_IIIF_IMAGE}/{identifier}/{region}/{size}/{rotation}/{quality}.{fmt}"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()
        
        return [TextContent(type="text", text=f"Image retrieved successfully from: {url}")]
    
    except Exception as e:
        return [TextContent(type="text", text=f"Error retrieving image: {str(e)}")]

async def handle_get_manifest(arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle manifest retrieval requests."""
    
    recordId = arguments["recordId"]
    url = BASE_IIIF_MANIFEST.format(recordId=recordId)
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()
        
        data = response.json()
        return [TextContent(type="text", text=json.dumps(data, ensure_ascii=False, indent=2))]
    
    except Exception as e:
        return [TextContent(type="text", text=f"Error retrieving manifest: {str(e)}")]

async def handle_get_stream(arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle stream retrieval requests."""
    
    itemId = arguments["itemId"]
    fmt = arguments.get("format", "all")

    params = {"api_key": NLI_API_KEY, "query": f"RecordId,exact,{itemId}", "format": "json", "rows": 1, "start": 0}
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(BASE_SEARCH_URL, params=params)
            response.raise_for_status()

        data = response.json()
        items = data.get("items", [])
        if not items:
            return [TextContent(type="text", text="Item not found")]

        doc = items[0]
        streams = {}
        if fmt in ("mp4", "all") and doc.get("stream_url_mp4"):
            streams["mp4"] = doc["stream_url_mp4"]
        if fmt in ("hls", "all") and doc.get("stream_url_hls"):
            streams["hls"] = doc["stream_url_hls"]
        if fmt in ("audio", "all") and doc.get("audio_url"):
            streams["audio"] = doc["audio_url"]

        return [TextContent(type="text", text=json.dumps(streams, ensure_ascii=False, indent=2))]
    
    except Exception as e:
        return [TextContent(type="text", text=f"Error retrieving streams: {str(e)}")]

async def main():
    """Main function to run the MCP server."""
    notification_options = None
    class NotificationOptions:
        tools_changed = None

    notification_options = NotificationOptions()

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="nli_mcp",
                server_version="1.0.0",
                capabilities = server.get_capabilities(
                    notification_options=notification_options,
                    experimental_capabilities=None,
                ),
            ),
        )

if __name__ == "__main__":
    asyncio.run(main())