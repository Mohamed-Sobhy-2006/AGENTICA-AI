from langchain_huggingface import HuggingFaceEmbeddings


def create_embedding_model(model_name):

    embedding = HuggingFaceEmbeddings(
        model_name=model_name
    )

    return embedding




def create_embeddings(splits, embedding):

    # if embedding is None:
    #     embedding = create_embedding_model()

    # Extract texts and metadata
    texts = [doc.page_content for doc in splits]
    metadatas = [doc.metadata for doc in splits]

    # Generate vectors
    vectors = embedding.embed_documents(texts)


    ### assert len(splits) == len(texts) == len(metadatas) == len(vectors)

    # Validation check suitable for production
    if not (len(splits) == len(texts) == len(metadatas) == len(vectors)):
        raise ValueError(
            f"Embedding mismatch: splits={len(splits)}, texts={len(texts)}, "
            f"metadatas={len(metadatas)}, vectors={len(vectors)}"
        )

    return vectors