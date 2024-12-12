import asyncio
import logging
from os.path import exists
from typing import List, Any

import ollama
from ollama import embeddings

import chromadb
import chromadb.utils.embedding_functions as embedding_functions
from openai import OpenAI


from langchain_community.utilities import SQLDatabase
from langchain.chains import create_sql_query_chain
from langchain_unstructured import UnstructuredLoader
from langchain_core.documents import Document


from connect import ask_ollama_server
from templates.prompts import *
from langchain_experimental.text_splitter import SemanticChunker
from langchain.embeddings import OpenAIEmbeddings
from langchain_community.embeddings import OllamaEmbeddings
import pickle
from langchain_openai import OpenAIEmbeddings

import os

class Files:
    def __init__(self, list_of_collections: List[str] = [], working_with_ollama_server=False):
        self.pkl_file = lambda x: os.path.abspath(os.path.join(os.path.dirname(__file__), f'../content/pkls/{x}.pkl'))
        self.pdf_file = lambda x: os.path.abspath(os.path.join(os.path.dirname(__file__), f'../content/pdfs/{x}.pdf'))
        self.path_to_save_chromadb = os.path.abspath(os.path.join(os.path.dirname(__file__), 'chromadb'))
        self.client = chromadb.HttpClient(host='localhost', port=8001)
        self.ollama_embedding_for_chromadb = embedding_functions.OpenAIEmbeddingFunction(
            api_key=os.environ.get('OPENAI_API_KEY'),
            model_name="text-embedding-3-large"
        )
        self.Models = Models(working_with_ollama_server)
        self.list_of_collections = list_of_collections


    async def add_new_file(self, file_name: str) -> bool:
        print(1)
        _ = await self._read_file(file_name)
        self.list_of_collections.append(file_name)
        return True


    async def _make_chunking(self, file_name):
        loader = UnstructuredLoader(
            file_path=self.pdf_file(file_name),
            api_key=os.getenv("UNSTRUCTURED_API_KEY"),
            partition_via_api=True,
        )
        print('Starting chunkin via unstructured')
        docs = loader.load()
        print('Ending chunkin via unstructured')
        text = ''
        tables = []
        for element in docs:
            if element.metadata['category'] == "Title":
                text += f'.\n\n{element.page_content}'
            elif element.metadata['category'] == "Table":
                temp_text = element.metadata["text_as_html"].replace('<', ' <').replace('>', '> ')
                tables.append(temp_text)
            else:
                text += f'. {element.page_content}'

        text_splitter = SemanticChunker(
            OpenAIEmbeddings(model="text-embedding-3-large"),
            buffer_size=5,
            sentence_split_regex=r"(?<=[.?!;])\s+",
            breakpoint_threshold_type="gradient"
        )
        docs_splited = [i.page_content for i in text_splitter.create_documents([text])]
        docs_splited += tables
        with open(self.pkl_file(file_name), 'wb') as f:
            pickle.dump(docs_splited, f)
        return docs_splited


    async def _read_file(self, file_name: str) -> list[Any]:
        pkl_file_path = self.pkl_file(file_name)
        collection = await asyncio.to_thread(self.client.get_or_create_collection, name=file_name,
                                                            embedding_function=self.ollama_embedding_for_chromadb,
                                                            metadata={"hnsw:space": "cosine"}
                                                            )
        if not exists(pkl_file_path):
            await self._make_chunking(file_name=file_name)
        # Ładujemy dane z pliku pickle
        with open(pkl_file_path, 'rb') as f:
            loaded_list = await asyncio.to_thread(pickle.load, f)
            answer = []
            # Dodajemy niepusty tekst do listy "answer"
            _ = [answer.append(i) if len(i) > 0 else None for i in loaded_list]
            # Dla każdego opisu generujemy embedding i aktualizujemy kolekcję w ChromaDB
            if len((await asyncio.to_thread(collection.get))['documents']) == 0:
                print(len(answer))
                for i, descr in enumerate(answer):
                    embedding = await self.Models.embedding_function(descr)
                    await asyncio.to_thread(collection.add, documents=descr, ids=[f'{i}_id'], embeddings=[embedding])
                    print(i)
            return answer


    async def search_most_relevant_pieces_of_text(self, question: str, n=3) -> List[Any]:
        embedded_question = await self.Models.embedding_function(question)
        results = []
        for name_of_collection in self.list_of_collections:
            collection = await asyncio.to_thread(self.client.get_or_create_collection, name=name_of_collection, metadata={"hnsw:space": "cosine"})
            results.append(await asyncio.to_thread(collection.query, query_embeddings=[embedded_question], n_results=n))
        all_documents = []
        all_distances = []
        for item in results:
            all_documents.extend(item['documents'][0])
            all_distances.extend(item['distances'][0])
        sorted_documents = [(document, all_distances) for document, all_distances in sorted(zip(all_documents, all_distances), key=lambda x: x[1])][:n]
        print([i[0] for i in sorted_documents])
        return [i[0] for i in sorted_documents]


class Models:
    def __init__(self, working_with_ollama_server):
        self.client_openai = OpenAI()
        self.model_embedding = "text-embedding-3-large"
        self.model = "llama3.1"
        self.working_with_ollama_server = working_with_ollama_server


    async def embedding_function(self, text, model=None):
        model = model or self.model_embedding
        data = await asyncio.to_thread(self.client_openai.embeddings.create, input=text, model=model)
        return data.data[0].embedding

        # return ollama.embeddings(model='nomic-embed-text', prompt=text)['embedding']

        # from transformers import AutoModel
        # model = AutoModel.from_pretrained("jinaai/jina-embeddings-v3", trust_remote_code=True)
        # embeddings = model.encode(text, task="text-matching", truncate_dim=2048)
        # return embeddings.astype(float).tolist()

        # from sentence_transformers import SentenceTransformer
        #
        # auto_model = SentenceTransformer("Alibaba-NLP/gte-Qwen1.5-7B-instruct", trust_remote_code=True)
        # query_embeddings = model.encode([text], prompt_name="query")
        # print(query_embeddings)
        # print(len(query_embeddings))
        # return query_embeddings.tolist()[0]


    async def generation_function(self, text, model=None):
        # model = model or self.model
        # if self.working_with_ollama_server:
        #     return ask_ollama_server(prompt=text, model=model)['response']
        # else:
        #     return ollama.generate(prompt=text, model=model)['response']

        client = self.client_openai

        completion = await asyncio.to_thread(client.chat.completions.create,
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {
                    "role": "user",
                    "content": text
                }
            ]
        )
        return completion.choices[0].message.content


class Communication:
    def __init__(self, pdf_path: str, working_with_ollama_server, files):
        self.logger = logging.getLogger(__name__)
        self.working_with_ollama_server = working_with_ollama_server
        logging.basicConfig(filename='py_log.log', encoding='utf-8', level=logging.DEBUG)
        self.pdf_path = pdf_path
        self.dict_of_chunks = {}
        self.client_openai = OpenAI()
        self.model_embedding = "text-embedding-3-large"
        self.model = "llama3.1"
        self.faiss_path = 'content/faiss'
        self.Models = Models(working_with_ollama_server)
        self.Files = files
        if self.working_with_ollama_server:
            # Jeśli pracujemy z serwerem Ollama, importujemy specyficzną funkcję "ChatOllama"
            from copy_ollama_function_ChatOllama import ChatOllama
        else:
            # W przeciwnym wypadku korzystamy z funkcji wbudowanej w LangChain
            from langchain_community.chat_models import ChatOllama
        # Tworzymy instancję modelu dla zapytań SQL
        self.llm_model_for_sql = ChatOllama(model='llama3.1')
        # Ścieżka do zapisu danych ChromaDB
        self.path_to_save_chromadb = os.path.abspath(os.path.join(os.path.dirname(__file__), 'chromadb'))
        # Inicjalizacja klienta ChromaDB
        self.client = chromadb.HttpClient(host='localhost', port=8001)
        # Ustawiamy funkcję embeddingu, która korzysta z modelu Ollama
        # self.ollama_embedding_for_chromadb = embedding_functions.OllamaEmbeddingFunction(
        #     url="http://localhost:11434/api/embeddings",
        #     model_name=self.model_embedding,
        # )
        self.ollama_embedding_for_chromadb = embedding_functions.OpenAIEmbeddingFunction(
            api_key=os.environ.get('OPENAI_API_KEY'),
            model_name="text-embedding-3-large"
        )
        # Tworzymy kolekcję dokumentów w ChromaDB, jeśli jeszcze nie istnieje
        self.collection = self.client.get_or_create_collection(name="jezyk-polski-final", embedding_function=self.ollama_embedding_for_chromadb, metadata={"hnsw:space": "cosine"})
        # self.document = asyncio.run(self.Files.add_new_file('polski2_1'))
        # Ścieżka do pliku bazy danych SQL
        self.database_filename = os.path.abspath(os.path.join(os.path.dirname(__file__), '../content/plan_lekcji10.db'))
        self.db_path = os.path.join(os.getcwd(), self.database_filename)
        # Inicjalizacja połączenia z bazą SQL
        self.db = SQLDatabase.from_uri(f"sqlite:///{self.db_path}")
        # Lista osadzonych dokumentów (embeddingów)
        self.list_of_embeded_document = []
        # Tworzenie łańcucha zapytań SQL
        self.chain = create_sql_query_chain(self.llm_model_for_sql, self.db)
        # Funkcja ekstrakcji zapytań SQL
        self.sql_prompt_extractor = lambda x: x[x.find('SELECT'):] + ";" if x[x.find('SELECT'):].count(';') == 0 else x[x.find('SELECT'):x.rfind(';') + 1]


    async def ask_pdf(self, question: str) -> str:
        # Wyszukujemy najbardziej pasujące dokumenty
        matched_docs = await self.Files.search_most_relevant_pieces_of_text(question, 30)
        # Zwracamy dopasowane dokumenty
        matched_docs = "\n\n".join([f'{i+1} fragment tekstu: ' + str(text) for i, text in enumerate(matched_docs)])
        print(matched_docs)
        # Generujemy odpowiedź na pytanie na podstawie fragmentów dokumentu
        output = await self.Models.generation_function(final_prompt_with_pdf_template.format(matched_docs, question))
        return output


    async def ask_pdf_with_quotation(self, question: str, quotation_text: str, quotation_div: str) -> str:
        # Wyszukujemy najbardziej pasujące dokumenty
        matched_docs = await self.Files.search_most_relevant_pieces_of_text(quotation_text, 30)
        # Zwracamy dopasowane dokumenty
        matched_docs = "\n\n".join([f'{i+1} fragment tekstu: ' + str(text) for i, text in enumerate(matched_docs)])
        # print(matched_docs)
        # Generujemy odpowiedź na pytanie na podstawie fragmentów dokumentu
        answer = final_prompt_with_pdf_and_quotation_template.format(matched_docs, quotation_div, quotation_text, question)
        print(answer)
        output = await self.Models.generation_function(answer)
        return output


    async def _generate_prompt_to_sql(self, question):
        for i in range(20):
            try:
                # Wysyłamy zapytanie do łańcucha SQL
                response = await asyncio.to_thread(self.chain.invoke({"question": prompt_to_sql_database_template.format(question)}))
                # Jeśli zapytanie SQL zwróci dane, generujemy odpowiedź
                answer = await asyncio.to_thread(self.db.run(self.sql_prompt_extractor(response)))
                if len(answer) > 0:
                    return response
                else:
                    continue
            except Exception:
                self.logger.info(f'{i} trying was unsuccessfully')
        return None


    async def ask_sql(self, question):
        # Tworzymy zapytanie do bazy SQL
        response = await self._generate_prompt_to_sql(question)
        if response:
            # Tworzymy odpowiedź na podstawie zapytania SQL
            db_context = await self.sql_prompt_extractor(response)
            db_answer = await asyncio.to_thread(self.db.run(db_context))
            self.logger.info(db_context)
            self.logger.info(db_answer)
            # Generujemy odpowiedź w zależności od serwera Ollama
            return await self.Models.generation_function(final_prompt_sql_template.format(question=question, result=db_answer, request_to_sql=db_context))
        else:
            # Jeśli zapytanie SQL się nie powiedzie, zwracamy odpowiedź błędną
            return 'Niestety nie udało się znaleść jakiejkolwiek informacji, sprobójcie przeformulować prompt lub zapytajcie o czymś innym'


    async def ask_api(self, _json: dict):
        # Wybieramy odpowiednią metodę odpowiedzi na podstawie typu pliku
        question = _json.get('question')
        selected_option = _json.get('file')
        quotation_text = _json.get('quotation_text')
        quotation_div = _json.get('quotation_div')
        if quotation_text:
            if selected_option == "pdfs":
                answer = await self.ask_pdf_with_quotation(question, quotation_text, quotation_div)
            elif selected_option == "lekcji":
                answer = await self.ask_sql(question)
            else:
                answer = 'Wystąpił błąd, spróbuj ponownie'
            json_answer = {'answer': answer}
            return json_answer
        else:
            if selected_option == "pdfs":
                answer = await self.ask_pdf(question)
            elif selected_option == "lekcji":
                answer = await self.ask_sql(question)
            else:
                answer = 'Wystąpił błąd, spróbuj ponownie'
            json_answer = {'answer': answer}
            return json_answer
