"""
Q&A Retrieval Service - Retrieve relevant Q&A pairs from Qdrant
"""
from qdrant_client import QdrantClient
from qdrant_client.models import SearchRequest, Filter
from langchain_openai import OpenAIEmbeddings
from typing import List, Dict
import os


# Initialize Qdrant client (local Docker instance)
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
COLLECTION_NAME = "medusa_qna"

client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
embeddings = OpenAIEmbeddings()


def retrieve_relevant_qna(query: str, limit: int = 3, score_threshold: float = 0.7) -> List[Dict]:
    """
    Retrieve relevant Q&A pairs based on the user query

    Args:
        query: User's question
        limit: Maximum number of Q&A pairs to retrieve
        score_threshold: Minimum similarity score (0-1)

    Returns:
        List of relevant Q&A pairs with scores
    """
    try:
        # Generate embedding for the query
        query_embedding = embeddings.embed_query(query)

        # Search in Qdrant using the correct method
        search_results = client.query_points(
            collection_name=COLLECTION_NAME,
            query=query_embedding,
            limit=limit,
            score_threshold=score_threshold
        )

        # Format results
        results = []
        for result in search_results.points:
            results.append({
                "question": result.payload.get("question"),
                "answer": result.payload.get("answer"),
                "score": result.score,
                "id": result.id
            })

        return results

    except Exception as e:
        print(f"❌ Error retrieving Q&A: {e}")
        import traceback
        traceback.print_exc()
        return []


def format_context_for_llm(qna_results: List[Dict]) -> str:
    """
    Format retrieved Q&A pairs as context for the LLM

    Args:
        qna_results: List of Q&A pairs from retrieval

    Returns:
        Formatted string to be used as context
    """
    if not qna_results:
        return ""

    context = "Here is some relevant information from the store's knowledge base:\n\n"

    for i, qna in enumerate(qna_results, 1):
        context += f"Q{i}: {qna['question']}\n"
        context += f"A{i}: {qna['answer']}\n\n"

    return context
