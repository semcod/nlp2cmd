"""
RAG (Retrieval-Augmented Generation) domain templates for NLP2CMD.

Contains vector DB, embeddings, document processing, search pipeline templates.
"""

RAG_TEMPLATES = {
    # ChromaDB
    'chroma_create': "python3 -c \"import chromadb; c = chromadb.Client(); c.create_collection('{collection}'); print('Created:', '{collection}')\"",
    'chroma_add': "python3 -c \"import chromadb; c = chromadb.PersistentClient(path='{db_path}'); col = c.get_or_create_collection('{collection}'); col.add(documents={documents}, ids={ids}); print('Added', len({ids}), 'documents')\"",
    'chroma_query': "python3 -c \"import chromadb; c = chromadb.PersistentClient(path='{db_path}'); col = c.get_collection('{collection}'); r = col.query(query_texts=['{query}'], n_results={n}); print(r)\"",
    'chroma_list': "python3 -c \"import chromadb; c = chromadb.PersistentClient(path='{db_path}'); print([col.name for col in c.list_collections()])\"",
    'chroma_count': "python3 -c \"import chromadb; c = chromadb.PersistentClient(path='{db_path}'); col = c.get_collection('{collection}'); print(col.count())\"",
    'chroma_delete': "python3 -c \"import chromadb; c = chromadb.PersistentClient(path='{db_path}'); c.delete_collection('{collection}'); print('Deleted:', '{collection}')\"",
    # Qdrant
    'qdrant_create': "curl -X PUT '{url}/collections/{collection}' -H 'Content-Type: application/json' -d '{{\"vectors\": {{\"size\": {dim}, \"distance\": \"{distance}\"}}}}'",
    'qdrant_search': "curl -X POST '{url}/collections/{collection}/points/search' -H 'Content-Type: application/json' -d '{{\"vector\": {vector}, \"limit\": {limit}}}'",
    'qdrant_info': "curl -s '{url}/collections/{collection}'",
    'qdrant_list': "curl -s '{url}/collections'",
    # Milvus
    'milvus_list': "python3 -c \"from pymilvus import connections, utility; connections.connect(); print(utility.list_collections())\"",
    # Embeddings
    'embed_openai': "curl -s https://api.openai.com/v1/embeddings -H 'Authorization: Bearer {api_key}' -H 'Content-Type: application/json' -d '{{\"input\": \"{text}\", \"model\": \"{model}\"}}'",
    'embed_ollama': "curl -s {ollama_url}/api/embeddings -d '{{\"model\": \"{model}\", \"prompt\": \"{text}\"}}'",
    'embed_sentence_transformers': "python3 -c \"from sentence_transformers import SentenceTransformer; m = SentenceTransformer('{model}'); print(m.encode('{text}').tolist()[:5], '...')\"",
    # Document processing
    'pdf_extract': "python3 -c \"import PyPDF2; r = PyPDF2.PdfReader('{file}'); [print(p.extract_text()) for p in r.pages]\"",
    'pdf_chunk': "python3 -c \"from langchain.text_splitter import RecursiveCharacterTextSplitter; s = RecursiveCharacterTextSplitter(chunk_size={chunk_size}, chunk_overlap={overlap}); print(len(s.split_text(open('{file}').read())), 'chunks')\"",
    'docx_extract': "python3 -c \"from docx import Document; d = Document('{file}'); print('\\n'.join(p.text for p in d.paragraphs))\"",
    'html_extract': "python3 -c \"from bs4 import BeautifulSoup; soup = BeautifulSoup(open('{file}'), 'html.parser'); print(soup.get_text())\"",
    # LLM calls
    'ollama_generate': "curl -s {ollama_url}/api/generate -d '{{\"model\": \"{model}\", \"prompt\": \"{prompt}\", \"stream\": false}}' | jq -r '.response'",
    'ollama_chat': "curl -s {ollama_url}/api/chat -d '{{\"model\": \"{model}\", \"messages\": [{{\"role\": \"user\", \"content\": \"{message}\"}}], \"stream\": false}}' | jq -r '.message.content'",
    'ollama_list': "ollama list",
    'ollama_pull': "ollama pull {model}",
    'ollama_run': "ollama run {model} '{prompt}'",
    'openai_chat': "curl -s https://api.openai.com/v1/chat/completions -H 'Authorization: Bearer {api_key}' -H 'Content-Type: application/json' -d '{{\"model\": \"{model}\", \"messages\": [{{\"role\": \"user\", \"content\": \"{message}\"}}]}}'",
    # Search
    'whoosh_search': "python3 -c \"from whoosh.index import open_dir; ix = open_dir('{index_dir}'); s = ix.searcher(); r = s.search(ix.schema.parse('{query}')); [print(h) for h in r]\"",
    'elasticsearch_search': "curl -s '{url}/{index}/_search?q={query}'",
    'elasticsearch_index': "curl -s -X PUT '{url}/{index}' -H 'Content-Type: application/json' -d '{mapping}'",
    # Pipeline
    'langchain_qa': "python3 -c \"from langchain.chains import RetrievalQA; from langchain.llms import Ollama; print('LangChain QA pipeline ready')\"",
    'llamaindex_query': "python3 -c \"from llama_index import VectorStoreIndex, SimpleDirectoryReader; docs = SimpleDirectoryReader('{directory}').load_data(); index = VectorStoreIndex.from_documents(docs); print(index.as_query_engine().query('{query}'))\"",
}
