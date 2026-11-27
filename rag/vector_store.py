import uuid

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams
from langchain_qdrant import QdrantVectorStore


def create_vectorstores(
    splits,
    vectors,
    embedding,
    qdrant_path,
    domains
):



    # Prepare data
    texts = [doc.page_content for doc in splits]
    metadatas = [doc.metadata for doc in splits]

    # Validate data (Production-ready checks)
    if not (len(texts) == len(vectors) == len(metadatas)):
        raise ValueError(
            f"Data length mismatch: texts={len(texts)}, "
            f"vectors={len(vectors)}, metadatas={len(metadatas)}"
        )

    if len(vectors) == 0:
        raise ValueError("Cannot create vectorstores: 'vectors' list is empty.")

    vector_size = len(vectors[0])

    if vector_size == 0 or not all(len(vec) == vector_size for vec in vectors):
        raise ValueError(
            f"Vector dimension mismatch: expected all vectors to have size {vector_size}."
        )

    # Qdrant configuration
    client = QdrantClient(path=qdrant_path)

    vectorstores = {}

    for domain in domains:

        collection_name = f"{domain}_collection"

        # Delete collection if it already exists
        if client.collection_exists(collection_name):
            client.delete_collection(collection_name)

        # Create new collection
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=vector_size,
                distance=Distance.COSINE
            )
        )

        # Filter chunks by domain
        domain_texts = []
        domain_vectors = []
        domain_metadatas = []

        for text, vec, meta in zip(texts, vectors, metadatas):

            if meta.get("domain") == domain:

                domain_texts.append(text)
                domain_vectors.append(vec)
                domain_metadatas.append(meta)

        # Prepare points
        # points = [
        #     PointStruct(
        #         id=str(uuid.uuid4()),
        #         vector=vec,
        #         payload={
        #             "page_content": text,
        #             "metadata": meta
        #         }
        #     )
        #     for text, vec, meta in zip(
        #         domain_texts,
        #         domain_vectors,
        #         domain_metadatas
        #     )
        # ]

# Prepare points
        points = [
            PointStruct(
                id=str(uuid.uuid5(
                    uuid.NAMESPACE_DNS,
                    f"{domain}_{meta.get('source')}_{meta.get('chunk_id')}"
                )),
                vector=vec,
                payload={
                    "page_content": text,
                    "metadata": meta
                }
            )
            for text, vec, meta in zip(
                domain_texts,
                domain_vectors,
                domain_metadatas
            )
        ]

        # Store vectors
        if points:

            client.upsert(
                collection_name=collection_name,
                points=points
            )

        # Connect with LangChain
        vectorstores[domain] = QdrantVectorStore(
            client=client,
            collection_name=collection_name,
            embedding=embedding,
            content_payload_key="page_content",
            metadata_payload_key="metadata"
        )



    return vectorstores