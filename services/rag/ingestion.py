"""
Q&A Ingestion Service - Store Q&A pairs in Qdrant vector database
"""
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from langchain_openai import OpenAIEmbeddings
from typing import List, Dict
import uuid
import os


# Initialize Qdrant client (local Docker instance)
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
COLLECTION_NAME = "medusa_qna"

client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
embeddings = OpenAIEmbeddings()


def initialize_collection():
    """
    Initialize the Qdrant collection if it doesn't exist
    """
    try:
        # Check if collection exists
        collections = client.get_collections().collections
        collection_exists = any(col.name == COLLECTION_NAME for col in collections)

        if not collection_exists:
            # Create collection with vector configuration
            client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(size=1536, distance=Distance.COSINE)
            )
            print(f"✅ Collection '{COLLECTION_NAME}' created successfully")
        else:
            print(f"ℹ️  Collection '{COLLECTION_NAME}' already exists")

        return {"status": "success", "message": "Collection initialized"}
    except Exception as e:
        print(f"❌ Error initializing collection: {e}")
        return {"status": "error", "message": str(e)}


def ingest_qna_pairs(qna_pairs: List[Dict[str, str]]) -> Dict:
    """
    Ingest Q&A pairs into Qdrant

    Args:
        qna_pairs: List of dicts with 'question' and 'answer' keys
        Example: [
            {"question": "What is your return policy?", "answer": "30 days return..."},
            {"question": "Do you ship internationally?", "answer": "Yes, we ship..."}
        ]

    Returns:
        Dict with status and count of ingested pairs
    """
    try:
        # Initialize collection if needed
        initialize_collection()

        points = []

        for qna in qna_pairs:
            question = qna.get("question", "")
            answer = qna.get("answer", "")

            if not question or not answer:
                continue

            # Generate embedding for the question
            question_embedding = embeddings.embed_query(question)

            # Create point with metadata
            point = PointStruct(
                id=str(uuid.uuid4()),
                vector=question_embedding,
                payload={
                    "question": question,
                    "answer": answer,
                    "type": "qna"
                }
            )
            points.append(point)

        if points:
            # Upload to Qdrant
            client.upsert(
                collection_name=COLLECTION_NAME,
                points=points
            )

            return {
                "status": "success",
                "count": len(points),
                "message": f"Successfully ingested {len(points)} Q&A pairs"
            }
        else:
            return {
                "status": "error",
                "count": 0,
                "message": "No valid Q&A pairs provided"
            }

    except Exception as e:
        return {
            "status": "error",
            "count": 0,
            "message": f"Error during ingestion: {str(e)}"
        }


def delete_all_qna():
    """
    Delete all Q&A pairs from the collection (useful for testing)
    """
    try:
        client.delete_collection(collection_name=COLLECTION_NAME)
        initialize_collection()
        return {"status": "success", "message": "All Q&A pairs deleted"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def get_collection_info():
    """
    Get information about the collection
    """
    try:
        collection_info = client.get_collection(collection_name=COLLECTION_NAME)
        return {
            "status": "success",
            "collection_name": COLLECTION_NAME,
            "points_count": collection_info.points_count,
            "vectors_count": collection_info.vectors_count
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
