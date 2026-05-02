import os
import json
import subprocess
import re
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import PyPDF2
from bs4 import BeautifulSoup
import numpy as np
import faiss
import markdown
print("All Libaries Imported Successfully")

@dataclass
class Chunk:
    """Text chunk with metadata and embedding."""
    id: str
    text: str
    vector: Optional[np.ndarray]
    metadata: Dict

class DocumentLoader:
    """load PDF, Markdown and HTML documents."""
    @staticmethod
    def load_pdf(file_path: str) -> List[Dict]:
        """extract text from PDF, page by page for citations."""
        chunks = []
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page_num , page in enumerate(pdf_reader.pages):
                    text = page.extract_text()
                    if text.strip():
                        chunks.append({
                            'text': text,
                            'metadata': {
                                'source': os.path.basename(file_path),
                                'page': page_num+1,
                                'type': 'pdf'
                            }
                        })
        except Exception as e:
            print(f"Error loading PDF {file_path}: {e}")
        return chunks
    
    @staticmethod
    def load_markdown(file_path: str) -> List[Dict]:
        """convert markdown to text via HTML."""
        try:
            with open(file_path,'r',encoding='utf-8') as file:
                md_content = file.read()
                html = markdown.markdown(md_content)
                soup = BeautifulSoup(html,'html.parser')
                text = soup.get_text()
                return [{
                    'text': text,
                    'metadata': {
                        'source': os.path.basename(file_path),
                        'type': 'markdown',
                        'page': 1
                    }
                }]
        except Exception as e:
            print(f"Error loading Markdown {file_path}: {e}")
            return []
    
    @staticmethod
    def load_html(file_path: str) -> List[Dict]:
        """extract text from HTML, removing scripts and styles."""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                soup = BeautifulSoup(file.read(), 'html.parser')
                for script in soup(["script", "style"]):
                    script.decompose()
                text = soup.get_text()
                
                return [{
                    'text': text,
                    'metadata': {
                        'source': os.path.basename(file_path),
                        'page': 1,
                        'type': 'html'
                    }
                }]
        except Exception as e:
            print(f"error loading HTML {file_path}: {e}")
            return []
    
    @staticmethod
    def load_documents(directory: str) -> List[Dict]:
        """load supported documents from a directory."""
        documents = []
        doc_dir = Path(directory)
        if not doc_dir.exists():
            print(f"Creating {directory}...")
            doc_dir.mkdir(parents=True)
            print(f"Add documents to {directory} and run again.")
            return documents
        
        for file_path in doc_dir.rglob('*'):
            if file_path.is_file():
                ext = file_path.suffix.lower()
                if ext=='.pdf':
                    documents.extend(DocumentLoader.load_pdf(str(file_path)))
                elif ext in ['.md','.markdown']:
                    documents.extend(DocumentLoader.load_markdown(str(file_path)))
                elif ext in ['.html','.htm']:
                    documents.extend(DocumentLoader.load_html(str(file_path)))
        print(f"loaded {len(documents)} documents from {directory}")
        return documents

print("DocumentLoader ready")

class TextChunker:
    """text chunking with overlap and sentence boundaries."""
    @staticmethod
    def clean_text(text: str) -> str:
        """normalize whitespace and remove special characters."""
        text = re.sub(r'\s+',' ',text)
        text = re.sub(r'[^\w\s\.\,\!\?\-\:\;]','',text)
        return text.strip()
    
    @staticmethod
    def chunk_text(text: str, chunk_size: int = 750, overlap: int = 100, metadata: Dict = None) -> List[Chunk]:
        """split text into overlapping chunks at sentence boundaries"""
        text = TextChunker.clean_text(text)
        chunks = []
        if not text:
            return chunks
        start = 0
        chunk_index = 0
        while start < len(text):
            end = start + chunk_size
            if end < len(text):
                search_start = end - int(chunk_size*0.2)
                sentence_end = max(
                    text.rfind('.', search_start, end),
                    text.rfind('!', search_start, end),
                    text.rfind('?',search_start,end)
                )
                if sentence_end != -1 and sentence_end > start:
                    end = sentence_end + 1
            chunk_text = text[start:end].strip()

            if chunk_text:
                chunk_metadata = metadata.copy()
                chunk_metadata['chunk_index'] = chunk_index
                chunk_id = f"{chunk_metadata.get('source','unknown')}_{chunk_index}"
                chunks.append(Chunk(
                    id =chunk_id,
                    text=chunk_text,
                    vector=None,
                    metadata=chunk_metadata
                ))

                chunk_index += 1
            start = end - overlap
            if start >= len(text) - overlap:
                break
        return chunks

print("TextChunker ready")


class OllamaEmbedder:
    """Generate embeddings"""
    def __init__(self, model_name: str = "nomic-embed-text"):
        self.model_name = model_name
        self._verify_model()

    def _verify_model(self):
        """check if model is local"""
        try:
            result = subprocess.run(
                ['ollama','list'],
                capture_output=True,
                text=True,
                check=True
            )
            if self.model_name not in result.stdout:
                raise RuntimeError(
                    f"Model '{self.model_name}' not found locally.\n"
                    f"Please download it first using:\n"
                    f"  ollama pull {self.model_name}\n"
                    f"This is a one-time setup step that requires internet connection."
                )
            print(f"Found embedding model: {self.model_name}")
        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                f"Cannot connect to Ollama service.\n"
                f"Please ensure Ollama is installed and running.\n"
                f"Error: {e}"
            )
        except FileNotFoundError:
            raise RuntimeError(
                "Ollama not found on your system.\n"
                "Please install Ollama from: https://ollama.com/download\n"
                "This is a one-time setup step."
            )
    
    def embed_text(self, text: str) -> np.ndarray:
        """generate embeddong vector fpr text using HTTP API"""
        try:
            import http.client
            conn = http.client.HTTPConnection("localhost", 11434, timeout=30)
            headers = {'Content-Type':'application/json'}
            payload = json.dumps({
                "model": self.model_name,
                "prompt": text
            })
            conn.request("POST","/api/embeddings",payload,headers)
            res = conn.getresponse()
            data = json.loads(res.read().decode())
            return np.array(data['embedding'],dtype=np.float32)
        except Exception as e:
            print(f"Error generating embedding: {e}")
            return np.zeros((512,),dtype=np.float32)  # assuming 512-dim embeddings
        
    def embed_chunks(self, chunls: List[Chunk]) -> List[Chunk]:
        print(f"Generating embeddings for {len(chunls)} chunks...")
        for i,chunk in enumerate(chunls):
            if i%10 == 0 and i > 0:
                print(f" progress: {i}/{len(chunls)}")
            chunk.vector = self.embed_text(chunk.text)
        print("Embedding generation complete.")
        return chunls
    
class VectorDatabase:
    """FAISS-based vector storage and retrieval with Cosine Similarity."""
    def __init__(self, dimension: int = 768):
        self.dimension = dimension
        self.index = faiss.IndexFlatIP(dimension)
        self.chunks: List[Chunk] = []

    def add_chunks(self, chunks: List[Chunk]):
        """add chunk embeddings to the index."""
        vectors = np.array([chunk.vector for chunk in chunks], dtype = np.float32)
        faiss.normalize_L2(vectors)
        self.index.add(vectors)
        self.chunks.extend(chunks)
        print(f"Added {len(chunks)} chunks to the vector database (total: {len(self.chunks)}).")
    
    def search(self, query_vector: np.ndarray, top_k: int = 5) -> List[Tuple[Chunk, float]]:
        """find top-k most similar chunks"""
        query_vector = query_vector.reshape(1,-1).astype(np.float32)
        faiss.normaliz3e_L2(query_vector)
        similarities, indices = self.index.search(query_vector, top_k)

        results = []
        for idx, similarity in zip(indices[0], similarities[0]):
            if idx < len(self.chunks):
                distance = 1-similarity
                results.append((self.chunks[idx], float(distance)))
        return results
    
    def save(self, directory: str):
        """save index and metadata to disk."""
        os.makedirs(directory, exist_ok=True)
        faiss.write_index(self.index, os.path.join(directory,'faiss.index'))
        chunks_data = [{'id': chunk.id, 'text': chunk.text,'metadata': chunk.metadata} for chunk in self.chunks]
        with open(os.path.join(directory,'chunks.json'),'w',encoding='utf-8') as f:
            json.dump(chunks_data, f, indent=2)
        print(f"Vector database saved to {directory}")
    
    def load(self, directory: str, embedder) -> bool:
        """load database from disk"""
        index_path = os.path.join(directory,'faiss.index')
        chunks_path = os.path.join(directory,'chunks.json')

        if not os.path.exists(index_path) or not os.path.exists(chunks_path):
            print(f"No database found in {directory}")
            return False
        
        self.index = faiss.read_index(index_path)
        with open(chunks_path, 'r', encoding='utf-8') as f:
            chunks_data = json.load(f)
        
        print("Reconstructing chunk vectors from metadata...")
        self.chunks = []
        for data in chunks_data:
            chunk = Chunk(
                id=data['id'],
                text=data['text'],
                vector=embedder.embed_text(data['text']),
                metadata=data['metadata']
            )
            self.chunks.append(chunk)
        print(f"Loaded vector database with {len(self.chunks)} chunks from {directory}")
        return True
    

class OllamaLLM:
    """LLM interafce using Ollama CLI."""
    def __init__(self, model_name: str = "llama3.2"):
        self.model_name = model_name
        self._verify_model()
    
    def _verify_model(self):
        try:
            result = subprocess.run(
                ['ollama','list'],
                capture_output=True,
                text=True,
                check=True
            )
            if self.model_name not in result.stdout:
                raise RuntimeError(
                    f"Model '{self.model_name}' not found locally.\n"
                    f"Please download it first using:\n"
                    f"  ollama pull {self.model_name}\n"
                    f"This is a one-time setup step that requires internet connection."
                )
            print(f"Found LLM model: {self.model_name}")
        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                f"Cannot connect to Ollama service.\n"
                f"Please ensure Ollama is installed and running.\n"
                f"Error: {e}"
            )
        except FileNotFoundError:
            raise RuntimeError(
                "Ollama not found on your system.\n"
                "Please install Ollama from: https://ollama.com/download\n"
                "This is a one-time setup step."
            )
    
    def generate(self, prompt: str, temperatur: float = 0.3) -> str:
        """generate response from LLM using CLI"""
        try:
            result = subprocess.run(
                ['ollama','run',self.model_name],
                input=prompt,
                capture_output=True,
                text=True,
                timeout=300,
                encoding='utf-8'
            )
            if result.returncode != 0:
                error_msg = result.stderr or "Unknown error"
                print(f" Ollama error: {error_msg}")
                return f"Error: {error_msg}"
            answer = result.stdout.strip()

            if not answer:
                print(f"Empty response")
                return "Error: Empty response from LLM."
            
            print(f"Generated {len(answer)} characters")
            return answer
        except subprocess.TimeoutExpired:
            print(f"  Timeout after 5 minutes")
            return "Error: Generation timed out. Try a simpler question or smaller context."
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            print(f"  {error_msg}")
            return error_msg
    
print("OllamaLLM ready")

class RAGSystem:
    def __init__(self, documents_dir: str = "documents", db_dir: str = "vector_db", llm_model: str = "llama3.2",embedding_model: str = "nomic-embed-text"):
        self.documents_dir = documents_dir
        self.db_dir = db_dir
        self.embedder = OllamaEmbedder(model_name=embedding_model)
        self.vector_db = VectorDatabase()  
        self.llm = OllamaLLM(model_name=llm_model)
        print("RAGSystem initialized")
    
    def ingest_documents(self, chunk_size: int = 750, overlap: int = 100, force_rebuild: bool = False):
        """Build or load vector database."""
        if not force_rebuild and os.path.exists(self.db_dir):
            print("loading existing vector database...")
            if self.vector_db.load(self.db_dir, self.embedder):
                return
        print("Building new database...")

        documents = DocumentLoader.load_documents(self.documents_dir)
        if not documents:
            print("No documents found!")
            return
        
        all_chunks = []
        for doc in documents:
            chunks = TextChunker.chunk_text(
                doc['text'],
                chunk_size = chunk_size,
                overlap=overlap,
                metadata=doc['metadata']
            )
            all_chunks.extend(chunks)
        print(f"Total chunks created: {len(all_chunks)}")
        all_chunks = self.embedder.embed_chunks(all_chunks)
        self.vector_db.add_chunks(all_chunks)
        self.vector_db.save(self.db_dir)

    def query(self, question: str, top_k: int = 5, distance_threshold: float = 1.5):
        """Answer question using RAG.
       Returns:
            {
                'answer': Generated answer,
                'sources': List of source chunks,
                'confidence': 'high'|'medium'|'low'
            }
        """
        print(f"\n Question: {question}")
        
        #embed query
        query_vector = self.embedder.embed_text(question)
        
        #search vector DB
        results = self.vector_db.search(query_vector, top_k=top_k)
        #filter by threshold
        filtered_results = [
            (chunk, dist) for chunk, dist in results
            if dist < distance_threshold
        ]
        if not filtered_results:
            return {
                'answer': "Insufficient context to answer this question.",
                'sources': [],
                'confidence': 'low'
            }
        
        #build context from chunks
        context_parts = []
        sources = []
        for i, (chunk, distance) in enumerate(filtered_results):
            context_parts.append(
                f"[Source {i+1}: {chunk.metadata['source']}, "
                f"Page {chunk.metadata.get('page', 'N/A')}]\n{chunk.text}\n"
            )
            sources.append({
                'id': chunk.id,
                'source': chunk.metadata['source'],
                'page': chunk.metadata.get('page', 'N/A'),
                'distance': distance
            })
        
        context = "\n".join(context_parts)
        
        #build prompt
        prompt = f"""You are a helpful AI assistant. Answer the question based ONLY on the provided context.

CONTEXT:
{context}

QUESTION: {question}

INSTRUCTIONS:
1. Answer based only on the context above
2. Cite source numbers (e.g., "According to Source 1...")
3. If context is insufficient, state that clearly
4. Be concise but thorough

ANSWER:"""       
        #generate answer
        print("Generating answer...")
        answer = self.llm.generate(prompt, temperature=0.3)
        
        return {
            'answer': answer,
            'sources': sources,
            'confidence': 'high' if len(filtered_results) >= 3 else 'medium'
        }

print("RAG System class ready!")



# Initialize RAG system
rag = RAGSystem(
    documents_dir="documents",
    db_dir="vector_db",
    llm_model="llama3.2",
    embedding_model="nomic-embed-text"
)

# Build/load database
rag.ingest_documents(
    chunk_size=750,
    overlap=100,
    force_rebuild=True  
)

#example: Ask a question
question = "What problem does FLoRA aim to address in the context of parameter-efficient fine-tuning (PEFT) for large language models?"

result = rag.query(
    question=question,
    top_k=5,
    distance_threshold=0.6
)

# Display results
print("\n" + "="*60)
print("ANSWER:")
print("="*60)
print(result['answer'])
print("\n" + "="*60)
print(f"CONFIDENCE: {result['confidence'].upper()}")
print("="*60)
print("\nSOURCES:")
for i, source in enumerate(result['sources'], 1):
    print(f"  {i}. {source['source']} (Page {source['page']}) - Distance: {source['distance']:.4f}")
print("="*60)