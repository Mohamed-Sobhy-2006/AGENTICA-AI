from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter
)

from langchain_core.documents import Document


def split_documents(docs, chunk_size, chunk_overlap):

    # Step 1: Split by Markdown headers
    headers_to_split_on = [
        ("#", "header_1"),
        ("##", "header_2"),
        ("###", "header_3"),
    ]

    markdown_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=headers_to_split_on,
        strip_headers=True
    )

    # Step 2: Split large sections into chunks
    recursive_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )

    # Step 3: Extract sections and preserve metadata
    section_docs = []

    for doc in docs:

        header_sections = markdown_splitter.split_text(doc.page_content)

        for section in header_sections:

            section_docs.append(
                Document(
                    page_content=section.page_content,
                    metadata={
                        **doc.metadata,
                        **section.metadata
                    }
                )
            )

    # Step 4: Split all sections
    splits = recursive_splitter.split_documents(section_docs)

    # Step 5: Merge headers into content + assign chunk_id
    for chunk_id, doc in enumerate(splits):

        headers = [
            doc.metadata.get(key)
            for key in ["header_1", "header_2", "header_3"]
            if doc.metadata.get(key)
        ]

        header_context = " > ".join(headers)

        if header_context:
            doc.page_content = f"{header_context}\n\n{doc.page_content}"

        doc.metadata["chunk_id"] = chunk_id

    

    return splits