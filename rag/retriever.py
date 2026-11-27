def retrieve(query, vectorstores, domain=None, k=10):

    # Normalize domain (لو مبعوت كنص)
    if isinstance(domain, str):
        domain = domain.strip().lower()


    # 1. Select collections (Fallback to all if domain is not found)
    if domain in vectorstores:
        selected_vectorstores = {
            domain: vectorstores[domain]
        }
    else:
        selected_vectorstores = vectorstores


    # 2. Retrieve from selected collections
    retrieved_chunks = []

    for domain_name, vs in selected_vectorstores.items():

        results = vs.similarity_search_with_score(
            query=query,
            k=k
        )

        # 3. Prepare results
        for doc, score in results:

            retrieved_chunks.append({
                "score": float(score),
                "text": doc.page_content,
                "domain": doc.metadata.get("domain", domain_name),
                "source": doc.metadata.get("source"),
                "chunk_id": doc.metadata.get("chunk_id"),
                "classification_level": doc.metadata.get("classification_level"),
                "document_type": doc.metadata.get("document_type"),
                "effective_date": doc.metadata.get("effective_date")
            })

    # 4. Sort results by similarity score
    retrieved_chunks.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    # 5. Return top-k results globally
    return retrieved_chunks[:k]