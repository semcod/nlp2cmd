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
    # FAISS
    'faiss_create': "python3 -c \"import faiss; import numpy as np; idx = faiss.IndexFlatL2({dim}); print('FAISS index created, dim={dim}')\"",
    'faiss_search': "python3 -c \"import faiss, numpy as np; idx = faiss.read_index('{index_file}'); D, I = idx.search(np.random.rand(1,{dim}).astype('float32'), {k}); print('Results:', I)\"",
    'faiss_save': "python3 -c \"import faiss; idx = faiss.read_index('{index_file}'); faiss.write_index(idx, '{output_file}'); print('Saved')\"",
    # Weaviate
    'weaviate_query': "curl -s '{url}/v1/graphql' -H 'Content-Type: application/json' -d '{{\"query\": \"{{Get{{{class_name}(nearText:{{concepts:[\\\"{query}\\\"]}}limit:{limit}){{_additional{{distance}}}}}}}}\"}}'",
    'weaviate_schema': "curl -s '{url}/v1/schema'",
    # pgvector
    'pgvector_search': "psql -c \"SELECT id, content, embedding <-> '{vector}' AS distance FROM {table} ORDER BY distance LIMIT {limit};\" {database}",
    'pgvector_create': "psql -c \"CREATE EXTENSION IF NOT EXISTS vector; CREATE TABLE {table} (id serial PRIMARY KEY, content text, embedding vector({dim}));\" {database}",
    # Pinecone
    'pinecone_upsert': "python3 -c \"import pinecone; pinecone.init(api_key='{api_key}'); idx = pinecone.Index('{index}'); idx.upsert(vectors={vectors}); print('Upserted')\"",
    'pinecone_query': "python3 -c \"import pinecone; pinecone.init(api_key='{api_key}'); idx = pinecone.Index('{index}'); r = idx.query(vector={vector}, top_k={k}); print(r)\"",
    # Document loaders
    'unstructured_load': "python3 -c \"from unstructured.partition.auto import partition; elements = partition(filename='{file}'); print(len(elements), 'elements')\"",
    'csv_to_docs': "python3 -c \"from langchain.document_loaders.csv_loader import CSVLoader; docs = CSVLoader('{file}').load(); print(len(docs), 'documents')\"",
    'web_scrape_docs': "python3 -c \"from langchain.document_loaders import WebBaseLoader; docs = WebBaseLoader('{url}').load(); print(len(docs), 'pages loaded')\"",
    'text_splitter': "python3 -c \"from langchain.text_splitter import CharacterTextSplitter; s = CharacterTextSplitter(chunk_size={size}, chunk_overlap={overlap}); chunks = s.split_text(open('{file}').read()); print(len(chunks), 'chunks')\"",
    # Ollama embeddings (v2 API)
    'ollama_embed_v2': "curl -s {ollama_url}/api/embed -d '{{\"model\": \"{model}\", \"input\": \"{text}\"}}'",
    'ollama_embed_batch': "curl -s {ollama_url}/api/embed -d '{{\"model\": \"{model}\", \"input\": {texts}}}'",
    # RAG pipeline helpers
    'similarity_search': "python3 -c \"from langchain.vectorstores import Chroma; from langchain.embeddings import OllamaEmbeddings; db = Chroma(persist_directory='{db_path}', embedding_function=OllamaEmbeddings(model='{model}')); print(db.similarity_search('{query}', k={k}))\"",
    'rag_chain': "python3 -c \"from langchain.chains import RetrievalQA; from langchain.llms import Ollama; from langchain.vectorstores import Chroma; from langchain.embeddings import OllamaEmbeddings; db = Chroma(persist_directory='{db_path}', embedding_function=OllamaEmbeddings()); qa = RetrievalQA.from_chain_type(Ollama(model='{model}'), retriever=db.as_retriever()); print(qa.run('{query}'))\"",
    'index_directory': "python3 -c \"from langchain.document_loaders import DirectoryLoader; from langchain.text_splitter import RecursiveCharacterTextSplitter; docs = DirectoryLoader('{directory}', glob='**/*.{ext}').load(); chunks = RecursiveCharacterTextSplitter(chunk_size=1000).split_documents(docs); print(len(chunks), 'chunks indexed')\"",
}
