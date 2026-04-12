from langchain_text_splitters import RecursiveCharacterTextSplitter


def chunk_text(text, chunk_size=512, chunk_overlap=50):
    """
    Chunk the input text into smaller pieces using RecursiveCharacterTextSplitter.

    Args:
        text (str): The input text to be chunked.
        chunk_size (int): The maximum size of each chunk.
        chunk_overlap (int): The number of characters to overlap between chunks.

    Returns:
        List[str]: A list of text chunks.
    """
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    chunks = text_splitter.split_text(text)
    return chunks