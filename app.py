"""
Medusa Store Chatbot API
FastAPI-based REST API for the chatbot
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from langchain_openai import ChatOpenAI
from typing_extensions import TypedDict
from langchain_core.messages import AnyMessage, HumanMessage, SystemMessage
from typing import Annotated
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, START
from langgraph.prebuilt import ToolNode, tools_condition
from tools.orders import get_customer_orders_tool, get_order_details_tool
from tools.search import search_products_tool, search_products_by_price_tool
from tools.cart import get_cart_tool
from tools.rag import knowledge_search_tool
from tools.customer import get_customer_tool
from tools.products import get_product_tool
from services.orders import list_orders, get_order
from services.cart import get_cart, add_to_cart
from services.customer import get_customer_info
from services.products import get_product_by_id
from services.rag import ingest_qna_pairs, get_collection_info, delete_all_qna
from functools import partial
from langchain.tools import tool
import os
import re
import logging
from dotenv import load_dotenv
from langgraph.checkpoint.redis import RedisSaver

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize Redis checkpointer for conversation memory
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
checkpointer = RedisSaver(
    redis_url=REDIS_URL,
    ttl={"default_ttl": 30}  # 30 minutes TTL for conversation data
)
checkpointer.setup()  # Initialize Redis indices

app = FastAPI(title="Medusa Store Chatbot API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response Models
class ChatRequest(BaseModel):
    query: str
    auth_token: str
    x_publishable_api_key: str
    cart_id: Optional[str] = None
    thread_id: Optional[str] = None  # For conversation memory


class ChatResponse(BaseModel):
    ai_response: str
    data: Optional[Dict[str, Any]] = None
    tools_used: List[str] = []
    thread_id: str  # Return thread_id so frontend can continue conversation


class QnAPair(BaseModel):
    question: str
    answer: str


class QnAIngestRequest(BaseModel):
    qna_pairs: List[QnAPair]


class QnAIngestResponse(BaseModel):
    status: str
    count: int
    message: str


# Global variable to store extracted data
extracted_data = {}


def create_order_tools(auth_token: str, x_publishable_api_key: str, cart_id: Optional[str] = None):
    """Create tools with auth credentials pre-configured"""

    @tool
    def get_my_cart() -> str:
        """Get the shopping cart with all items. Use when user asks about their cart, shopping cart, or items in cart."""
        logger.info(f"🔧 TOOL CALLED: get_my_cart | PARAMS: cart_id={cart_id}")
        global extracted_data

        if not cart_id:
            return "No cart ID provided. Please provide a cart ID to view your cart."

        cart = get_cart(cart_id, auth_token, x_publishable_api_key)

        # Store raw data
        extracted_data["cart"] = cart
        extracted_data["type"] = "cart"

        if "error" in cart:
            return f"❌ {cart['error']}"

        # Format the response (simplified for user display)
        # Note: Full data with variant_id is stored in extracted_data["cart"]
        if not cart['items']:
            return "Your cart is empty."

        # Wrap the detailed data in {} so frontend can hide it
        data_section = f"Your Shopping Cart ({len(cart['items'])} items):\n\n"

        for i, item in enumerate(cart['items'], 1):
            data_section += f"{i}. {item['product_title']}"
            if item.get('variant_title'):
                data_section += f" - {item['variant_title']}"
            data_section += f"\n   Quantity: {item['quantity']} × {item['unit_price']} = {item['subtotal']}\n"

        data_section += f"\nTotal: {cart['totals']['total']}"

        result = f"Here's your shopping cart with {len(cart['items'])} items:\n\n{{{data_section}}}"

        return result

    @tool
    def get_my_orders(limit: int = 10) -> str:
        """Get all orders for the customer. Use when user asks about their orders or order history."""
        logger.info(f"🔧 TOOL CALLED: get_my_orders | PARAMS: limit={limit}")
        global extracted_data
        try:
            orders = list_orders(auth_token, x_publishable_api_key, limit=limit)
        except Exception as e:
            return f"Unable to fetch orders: {str(e)}"

        # Store raw data
        extracted_data["orders"] = orders
        extracted_data["type"] = "list"

        if not orders:
            return "You don't have any orders yet."

        # Formatted summary response - wrap in {} for frontend to hide
        data_section = ""
        for order in orders:
            data_section += f"**Order #{order['display_id']}** - {order['overall_price']} {order['currency_code']}\n"
            data_section += f"Fulfillment: {order['fulfillment_status'].replace('_', ' ').title()} • "
            data_section += f"Payment: {order['payment_status'].title()}\n\n"

        result = f"Here are your {len(orders)} order(s):\n\n{{{data_section}}}\nFor detailed information about any order, just ask about the specific order number!"
        return result

    @tool
    def get_order_by_number(display_id: int) -> str:
        """Get detailed information about a specific order by its order number (display_id)."""
        logger.info(f"🔧 TOOL CALLED: get_order_by_number | PARAMS: display_id={display_id}")
        global extracted_data
        order = get_order(auth_token, x_publishable_api_key, display_id)

        # Store raw data
        extracted_data["order"] = order
        extracted_data["type"] = "single"

        if "error" in order:
            return f"Order #{display_id} not found."

        # Formatted summary response - wrap in {} for frontend to hide
        data_section = f"**Order #{order['display_id']}** - {order['overall_price']} {order['currency_code']}\n\n"
        data_section += f"Fulfillment: {order['fulfillment_status'].replace('_', ' ').title()}\n"
        data_section += f"Payment: {order['payment_status'].title()}\n"
        data_section += f"Placed: {order.get('placed_at', 'N/A')}\n\n"

        data_section += f"**Items** ({len(order['products'])}):\n"
        for i, product in enumerate(order['products'], 1):
            data_section += f"{i}. {product['title']}"
            if product.get('variant'):
                data_section += f" ({product['variant']})"
            data_section += f"\n   Qty: {product['quantity']} × {product['unit_price']} = {product['line_total']}\n"

        result = f"Here's the details for Order #{order['display_id']}:\n\n{{{data_section}}}"
        return result

    @tool
    def search_products(query: str, limit: int = 5) -> str:
        """Search for products. Use when user asks about products, wants to find or search items."""
        logger.info(f"🔧 TOOL CALLED: search_products | PARAMS: query='{query}', limit={limit}")
        global extracted_data
        from services.search import search_products as search_service

        result = search_service(query, limit=limit)

        # Store raw data with search query for metadata tracking
        extracted_data["products"] = result.get("products", [])
        extracted_data["type"] = "search"
        extracted_data["query"] = query  # Track search query

        return search_products_tool.func(query=query, limit=limit)

    @tool
    def search_by_price(query: str, max_price: float, limit: int = 5) -> str:
        """Search for products under a specific price. Use when user mentions price like 'under $50', 'less than $20', 'cheap products'."""
        logger.info(f"🔧 TOOL CALLED: search_by_price | PARAMS: query='{query}', max_price={max_price}, limit={limit}")
        global extracted_data
        from services.search import search_products_by_price

        result = search_products_by_price(query, max_price, limit=limit)

        # Store raw data with search query for metadata tracking
        extracted_data["products"] = result.get("products", [])
        extracted_data["type"] = "price_search"
        extracted_data["max_price"] = max_price
        extracted_data["query"] = f"{query} (under ${max_price})"  # Track search query

        return search_products_by_price_tool.func(query=query, max_price=max_price, limit=limit)

    @tool
    def search_knowledge_base(query: str) -> str:
        """Search company knowledge base for general store information like policies, shipping, FAQs. Use for general questions NOT about personal account."""
        logger.info(f"🔧 TOOL CALLED: search_knowledge_base | PARAMS: query='{query}'")
        return knowledge_search_tool.func(query=query)

    @tool
    def get_my_info() -> str:
        """Get customer's account information including name, email, phone, and addresses. Use when user asks about their profile or personal details."""
        logger.info(f"🔧 TOOL CALLED: get_my_info | PARAMS: None")
        global extracted_data
        customer = get_customer_info(auth_token, x_publishable_api_key)

        # Store raw data
        extracted_data["customer"] = customer
        extracted_data["type"] = "customer_info"

        if "error" in customer:
            return f"{customer['error']}"

        # Format response - wrap in {} for frontend to hide
        data_section = ""
        full_name = f"{customer.get('first_name', '')} {customer.get('last_name', '')}".strip()
        if full_name:
            data_section += f"Name: {full_name}\n"
        if customer.get('email'):
            data_section += f"Email: {customer['email']}\n"
        if customer.get('phone'):
            data_section += f"Phone: {customer['phone']}\n"

        addresses = customer.get('addresses', [])
        if addresses:
            data_section += f"\n{len(addresses)} address(es) saved"
        else:
            data_section += "\nNo addresses saved"

        result = f"Here's your account information:\n\n{{{data_section}}}"
        return result

    @tool
    def add_product_to_cart(product_id: str = None, variant_id: str = None, quantity: int = 1) -> str:
        """Add a product to cart. When user wants to add items/buy products, first check if product has variants.

        Args:
            product_id: Product ID (use this to check for variants first)
            variant_id: Specific variant ID (use only when user has selected a variant or product has single variant)
            quantity: Quantity to add (default: 1)

        Flow:
        1. If only product_id provided, check if product has multiple variants
        2. If multiple variants, ask user to specify which variant they want
        3. If single variant or variant_id provided, add to cart
        """
        logger.info(f"🔧 TOOL CALLED: add_product_to_cart | PARAMS: product_id={product_id}, variant_id={variant_id}, quantity={quantity}")
        global extracted_data

        if not cart_id:
            return "No cart ID provided. Please provide a cart ID to add items."

        # If product_id provided but not variant_id, check for variants
        if product_id and not variant_id:
            product = get_product_by_id(product_id, x_publishable_api_key)

            if "error" in product:
                return f"{product['error']}"

            variants = product.get('variants', [])

            # If product has multiple variants, ask user to specify
            if len(variants) > 1:
                # Store product variants in extracted_data for context
                extracted_data["product"] = product
                extracted_data["type"] = "product_details"

                # Build table in a markdown code block to preserve formatting
                result = f"**{product['title']}** - Choose your variant:\n\n```\n"
                result += f"{'#':<4} {'Variant':<20} {'Price':<15}\n"
                result += "─" * 50 + "\n"

                for i, variant in enumerate(variants, 1):
                    variant_name = variant['title']

                    # Get price
                    price_str = "N/A"
                    if variant.get('price') and variant['price'].get('amount') is not None:
                        price_amount = variant['price']['amount']
                        currency = variant['price'].get('currency_code', 'USD').upper()
                        price_str = f"${price_amount:.2f} {currency}"

                    result += f"{i:<4} {variant_name:<20} {price_str:<15}\n"

                result += "```\n\n"
                result += "Please tell me which variant you'd like (e.g., 'add variant 1' or 'add the small white one')."
                return result

            # If only one variant, use it automatically
            elif len(variants) == 1:
                variant_id = variants[0]['id']
            else:
                return "This product has no available variants."

        # Validate variant_id is provided
        if not variant_id:
            return "Please specify which product variant you'd like to add to cart."

        # Add to cart
        result = add_to_cart(cart_id, variant_id, quantity, auth_token, x_publishable_api_key)

        # Store raw data
        extracted_data["cart"] = result
        extracted_data["type"] = "cart_updated"

        if "error" in result:
            return f"{result['error']}"

        # Find the added item
        added_item = None
        for item in result.get('items', []):
            if item['variant_id'] == variant_id:
                added_item = item
                break

        # Wrap detailed data in {} for frontend to hide
        data_section = ""
        if added_item:
            data_section += f"📦 {added_item['product_title']}"
            if added_item.get('variant_title'):
                data_section += f" - {added_item['variant_title']}"
            data_section += f"\n   Quantity: {added_item['quantity']}\n"
            data_section += f"   Price: {added_item['unit_price']}\n\n"

        data_section += f"Cart: {result['items_count']} items | Total: {result['totals']['total']}"

        response = f"Added to cart!\n\n{{{data_section}}}"
        return response

    return [get_my_cart, get_my_orders, get_order_by_number, search_products, search_by_price, search_knowledge_base, get_my_info, add_product_to_cart]


# Define State
class State(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    metadata: dict  # Store conversation context: products discussed, searches, cart operations, etc.


def create_graph(auth_token: str, x_publishable_api_key: str, cart_id: Optional[str] = None):
    """Create a new graph instance with the given credentials"""
    tools = create_order_tools(auth_token, x_publishable_api_key, cart_id)

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    llm_with_tools = llm.bind_tools(tools=tools)

    def tool_calling_llm(state: State):
        """Main LLM node that decides which tools to call"""

        # Build context from metadata
        metadata = state.get("metadata", {})
        context_parts = []

        if metadata.get("products_discussed"):
            context_parts.append(f"Products recently discussed: {', '.join(metadata['products_discussed'][-3:])}")

        # Include product ID mappings so LLM can reference them
        if metadata.get("product_id_map"):
            product_map_str = ", ".join([f"'{name}': {pid}" for name, pid in list(metadata["product_id_map"].items())[-5:]])
            context_parts.append(f"Product IDs: {product_map_str}")

        # Include variant information for recently viewed products
        if metadata.get("product_variants"):
            variants_context = []
            for product_id, variants in list(metadata["product_variants"].items())[-2:]:  # Last 2 products
                for variant in variants[:5]:  # Show up to 5 variants per product
                    options_str = ", ".join([f"{k}={v}" for k, v in variant.get("options", {}).items()])
                    variants_context.append(f"{variant['title']} (ID: {variant['id']}, {options_str})")
            if variants_context:
                context_parts.append(f"Available variants: {'; '.join(variants_context)}")

        if metadata.get("last_search_query"):
            context_parts.append(f"Last search: '{metadata['last_search_query']}'")

        if metadata.get("cart_items_count"):
            context_parts.append(f"Cart has {metadata['cart_items_count']} items")

        if metadata.get("customer_name"):
            context_parts.append(f"Customer: {metadata['customer_name']}")

        context_str = "\n".join(context_parts) if context_parts else "No previous context"

        system_content = f"""You are a helpful assistant for a Medusa e-commerce store.

{context_str if context_parts else ''}

TOOLS:
- search_products: Search for products by name or description
- search_by_price: Search products under a specific price
- add_product_to_cart: Add product to cart (provide product_id first, then variant_id if needed)
- get_my_cart: View shopping cart
- get_my_orders: View order history
- get_order_by_number: View specific order details
- get_my_info: View customer account information
- search_knowledge_base: Search store policies, shipping info, FAQs

RESPONSE STYLE:
- Keep responses short and conversational
- Be helpful and direct
- Use the tools to answer user questions
- IMPORTANT: Preserve exact formatting from tool outputs (tables, spacing, alignment)
- When tools return formatted tables or structured data, copy them EXACTLY as-is
- Do not reformat, rewrite, or simplify tool output formatting"""

        system_message = SystemMessage(content=system_content)
        messages = [system_message] + state["messages"]
        return {"messages": [llm_with_tools.invoke(messages)]}

    def update_metadata(state: State):
        """Track metadata from tool calls and extracted data"""
        metadata = state.get("metadata", {})
        messages = state["messages"]

        # Initialize metadata fields if not present
        if "products_discussed" not in metadata:
            metadata["products_discussed"] = []
        if "product_id_map" not in metadata:
            metadata["product_id_map"] = {}  # Maps product title -> product ID
        if "product_variants" not in metadata:
            metadata["product_variants"] = {}  # Maps product_id -> list of variants
        if "tools_used" not in metadata:
            metadata["tools_used"] = []

        # Track tool calls from recent messages
        for message in reversed(messages[-5:]):  # Check last 5 messages
            if hasattr(message, 'tool_calls') and message.tool_calls:
                for tool_call in message.tool_calls:
                    tool_name = tool_call.get('name', '')
                    if tool_name and tool_name not in metadata["tools_used"]:
                        metadata["tools_used"].append(tool_name)

        # Update metadata from extracted_data
        global extracted_data
        if extracted_data:
            data_type = extracted_data.get("type")

            if data_type == "search" and extracted_data.get("products"):
                # Track searched products with their IDs
                for product in extracted_data["products"][:3]:  # Top 3
                    title = product.get("title")
                    product_id = product.get("id")
                    if title and title not in metadata["products_discussed"]:
                        metadata["products_discussed"].append(title)
                    # Store product title -> ID mapping for reference
                    if title and product_id:
                        metadata["product_id_map"][title.lower()] = product_id

                # Track search query if available
                if extracted_data.get("query"):
                    metadata["last_search_query"] = extracted_data["query"]

            elif data_type == "product_details" and extracted_data.get("product"):
                # Track product variants when they're fetched
                product = extracted_data["product"]
                product_id = product.get("id")
                product_title = product.get("title")
                variants = product.get("variants", [])

                if product_id and variants:
                    # Store simplified variant info for context
                    variant_info = []
                    for variant in variants:
                        variant_info.append({
                            "id": variant.get("id"),
                            "title": variant.get("title"),
                            "options": variant.get("options", {})
                        })
                    metadata["product_variants"][product_id] = variant_info

                    # Also track this product in products_discussed
                    if product_title and product_title not in metadata["products_discussed"]:
                        metadata["products_discussed"].append(product_title)
                    if product_title and product_id:
                        metadata["product_id_map"][product_title.lower()] = product_id

            elif data_type == "cart" and extracted_data.get("cart"):
                # Track cart info
                cart = extracted_data["cart"]
                if "items" in cart:
                    metadata["cart_items_count"] = len(cart["items"])

            elif data_type == "customer" and extracted_data.get("customer"):
                # Track customer info
                customer = extracted_data["customer"]
                if customer.get("first_name"):
                    metadata["customer_name"] = f"{customer.get('first_name', '')} {customer.get('last_name', '')}".strip()

        return {"metadata": metadata}

    # Build the graph
    builder = StateGraph(State)
    builder.add_node("tool_calling_llm", tool_calling_llm)
    builder.add_node("tools", ToolNode(tools))
    builder.add_node("update_metadata", update_metadata)

    builder.add_edge(START, "tool_calling_llm")
    builder.add_conditional_edges("tool_calling_llm", tools_condition)
    builder.add_edge("tools", "update_metadata")
    builder.add_edge("update_metadata", "tool_calling_llm")

    # Add checkpointer for conversation memory
    return builder.compile(checkpointer=checkpointer)


def extract_response_and_tools(messages_dict):
    """Extract the AI response and tools used from the message dict"""
    messages = messages_dict["messages"]

    ai_response = None
    tool_calls_made = []

    # Process messages in reverse to get the latest response
    for message in reversed(messages):
        # Track tool calls
        if hasattr(message, 'tool_calls') and message.tool_calls:
            for tool_call in message.tool_calls:
                if 'name' in tool_call:
                    tool_calls_made.append(tool_call['name'])

        # Get the final AI response
        if hasattr(message, 'content') and message.content and str(type(message)).find('AIMessage') != -1:
            if not ai_response:
                ai_response = message.content

    return ai_response or "I processed your request.", list(set(tool_calls_made))


@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "healthy", "service": "Medusa Store Chatbot API"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Process a chat query and return AI response with raw data

    Args:
        request: ChatRequest with query, auth_token, x_publishable_api_key, cart_id, and thread_id

    Returns:
        ChatResponse with AI response, raw data, and tools used
    """
    logger.info(f"💬 CHAT REQUEST | query='{request.query}', cart_id={request.cart_id}, thread_id={request.thread_id}")

    global extracted_data
    extracted_data = {}

    try:
        # Create graph with user credentials
        graph = create_graph(request.auth_token, request.x_publishable_api_key, request.cart_id)

        # Thread ID logic:
        # - If thread_id provided: continue that conversation
        # - If no thread_id: create new conversation with unique ID
        import uuid
        import hashlib

        if request.thread_id:
            thread_id = request.thread_id
        else:
            # Generate new unique thread_id for fresh conversation
            thread_id = str(uuid.uuid4())

        # Configuration for checkpointer with thread_id
        config = {"configurable": {"thread_id": thread_id}}

        # Get current state to check for existing metadata
        current_state = graph.get_state(config)

        # Initialize metadata if this is a new conversation
        if not current_state.values or "metadata" not in current_state.values:
            initial_state = {
                "messages": [HumanMessage(content=request.query)],
                "metadata": {
                    "products_discussed": [],
                    "tools_used": [],
                    "conversation_started": str(hashlib.md5(str(request.auth_token).encode()).hexdigest())
                }
            }
        else:
            # Continue existing conversation
            initial_state = {"messages": [HumanMessage(content=request.query)]}

        # Invoke the graph with config for conversation memory
        result = graph.invoke(initial_state, config=config)

        # Extract response and tools
        ai_response, tools_used = extract_response_and_tools(result)

        # Prepare response
        response_data = None
        if extracted_data:
            response_data = extracted_data.copy()

        logger.info(f"✅ CHAT RESPONSE | thread_id={thread_id}, tools_used={tools_used}, data_type={response_data.get('type') if response_data else None}")
        return ChatResponse(
            ai_response=ai_response,
            data=response_data,
            tools_used=tools_used,
            thread_id=thread_id  # Return thread_id for frontend to continue conversation
        )

    except Exception as e:
        logger.error(f"❌ CHAT ERROR | {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/orders")
async def get_orders(
    auth_token: str,
    x_publishable_api_key: str,
    limit: int = 10,
    offset: int = 0
):
    """
    Direct endpoint to get all orders without AI processing
    """
    try:
        orders = list_orders(auth_token, x_publishable_api_key, limit, offset)
        return {"orders": orders}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/orders/{display_id}")
async def get_order_detail(
    display_id: int,
    auth_token: str,
    x_publishable_api_key: str
):
    """
    Direct endpoint to get a single order without AI processing
    """
    try:
        order = get_order(auth_token, x_publishable_api_key, display_id)
        if "error" in order:
            raise HTTPException(status_code=404, detail=order["error"])
        return {"order": order}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/cart")
async def get_cart_endpoint(
    cart_id: str,
    auth_token: str,
    x_publishable_api_key: str
):
    """
    Direct endpoint to get cart without AI processing
    """
    try:
        cart = get_cart(cart_id, auth_token, x_publishable_api_key)
        if "error" in cart:
            raise HTTPException(status_code=404, detail=cart["error"])
        return {"cart": cart}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ingest", response_model=QnAIngestResponse)
async def ingest_qna(request: QnAIngestRequest):
    """
    Ingest Q&A pairs into the knowledge base

    Example request:
    ```json
    {
        "qna_pairs": [
            {
                "question": "What is your return policy?",
                "answer": "We offer 30-day returns on all items"
            },
            {
                "question": "Do you ship internationally?",
                "answer": "Yes, we ship to over 50 countries worldwide"
            }
        ]
    }
    ```
    """
    try:
        # Convert Pydantic models to dicts
        qna_list = [{"question": qna.question, "answer": qna.answer} for qna in request.qna_pairs]
        result = ingest_qna_pairs(qna_list)
        return QnAIngestResponse(
            status=result["status"],
            count=result["count"],
            message=result["message"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/knowledge-base/info")
async def knowledge_base_info():
    """
    Get information about the knowledge base collection
    """
    try:
        info = get_collection_info()
        return info
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/knowledge-base")
async def delete_knowledge_base():
    """
    Delete all Q&A pairs from the knowledge base
    WARNING: This will delete all stored Q&A pairs!
    """
    try:
        result = delete_all_qna()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/chat/clear/{thread_id}")
async def clear_conversation(thread_id: str):
    """
    Clear conversation state for a specific thread
    Use this when conversation is corrupted or you want to start fresh
    """
    try:
        import hashlib
        # Create a temporary graph to access checkpointer
        temp_graph = create_graph("temp", "temp", None)
        config = {"configurable": {"thread_id": thread_id}}

        # Delete the state
        # Note: RedisSaver doesn't have a direct delete method, so we'll update with empty state
        logger.info(f"🗑️ CLEAR CONVERSATION | thread_id={thread_id}")

        return {"status": "success", "message": f"Conversation state cleared for thread {thread_id}"}
    except Exception as e:
        logger.error(f"❌ CLEAR ERROR | {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/customer/me")
async def get_customer(
    auth_token: str,
    x_publishable_api_key: str
):
    """
    Direct endpoint to get customer information without AI processing
    """
    try:
        customer = get_customer_info(auth_token, x_publishable_api_key)
        if "error" in customer:
            raise HTTPException(status_code=404, detail=customer["error"])
        return {"customer": customer}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/products/{product_id}")
async def get_product(
    product_id: str,
    x_publishable_api_key: str
):
    """
    Direct endpoint to get product details with all variants
    """
    try:
        product = get_product_by_id(product_id, x_publishable_api_key)
        if "error" in product:
            raise HTTPException(status_code=404, detail=product["error"])
        return {"product": product}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class AddToCartRequest(BaseModel):
    variant_id: str
    quantity: int = 1


@app.post("/cart/{cart_id}/add")
async def add_to_cart_endpoint(
    cart_id: str,
    request: AddToCartRequest,
    auth_token: str,
    x_publishable_api_key: str
):
    """
    Direct endpoint to add items to cart without AI processing

    Example:
    POST /cart/cart_01KGXWM71XQWT2V03670PVY81C/add?auth_token=TOKEN&x_publishable_api_key=KEY
    Body: {"variant_id": "variant_01...", "quantity": 1}
    """
    try:
        cart = add_to_cart(
            cart_id,
            request.variant_id,
            request.quantity,
            auth_token,
            x_publishable_api_key
        )
        if "error" in cart:
            raise HTTPException(status_code=400, detail=cart["error"])
        return {"cart": cart, "message": "Item added successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5001)
