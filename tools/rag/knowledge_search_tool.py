"""
Knowledge Search Tool - Retrieve general company information from knowledge base
"""
from langchain.tools import tool
from services.rag import retrieve_relevant_qna


@tool
def knowledge_search_tool(query: str) -> str:
    """
    Search the company knowledge base for general information like policies, shipping info, FAQs, etc.
    Use this when user asks general questions about the store that are NOT about their personal account, orders, or cart.

    Examples of when to use:
    - "What is your return policy?"
    - "Do you ship internationally?"
    - "What payment methods do you accept?"
    - "What are your business hours?"
    - "How long does shipping take?"

    Do NOT use for:
    - Personal account questions (use get_my_orders, get_my_cart instead)
    - Product searches (use search_products instead)

    Args:
        query: The user's question about general store information

    Returns:
        Relevant information from the knowledge base
    """
    try:
        # Retrieve relevant Q&A pairs
        results = retrieve_relevant_qna(query, limit=3, score_threshold=0.7)

        if not results:
            return "I don't have specific information about that in my knowledge base. Let me help you in another way or you can contact our support team."

        # Format the response
        response = "Based on our store information:\n\n"

        for i, qna in enumerate(results, 1):
            # Only show the most relevant answer if score is high enough
            if i == 1 and qna['score'] > 0.85:
                # High confidence - give direct answer
                return qna['answer']
            else:
                # Medium confidence - show Q&A format
                response += f"**Q: {qna['question']}**\n{qna['answer']}\n\n"

        return response.strip()

    except Exception as e:
        print(f"Knowledge search error: {e}")
        return "I'm having trouble accessing the knowledge base right now. Please try again or contact support."
