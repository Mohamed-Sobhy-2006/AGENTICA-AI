from .document_loader import load_documents
from .chunking import split_documents
from .embeddings import create_embeddings, create_embedding_model
from .vector_store import create_vectorstores
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DATA_DIR = str(PROJECT_ROOT / "data" / "knowledge_bases")
DEFAULT_QDRANT_PATH = str(PROJECT_ROOT / "data" / "vector_store")

def ingest_documents(
    data_dir=DEFAULT_DATA_DIR,
    qdrant_path=DEFAULT_QDRANT_PATH,
    domains=None ,
    chunk_size=400,
    chunk_overlap=100,
    model_name="BAAI/bge-m3"
):

    if domains is None:
        domains = ["finance", "hr", "company"]

    # 1. Load documents
    docs = load_documents(data_dir=data_dir)

    # 2. Chunk documents
    splits = split_documents(
        docs,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )

    # 3. Create embeddings
    embedding = create_embedding_model(model_name=model_name)

    vectors = create_embeddings(
        splits,
        embedding=embedding
    )

    # 4. Store vectors in Qdrant
    vectorstores = create_vectorstores(
        splits=splits,
        vectors=vectors,
        embedding=embedding,
        qdrant_path=qdrant_path,
        domains=domains
    )

    return vectorstores