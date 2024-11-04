import logging
from fileinput import filename
from os.path import exists

import ollama
from importlib_metadata import metadata
from ollama import embeddings

import chromadb
import chromadb.utils.embedding_functions as embedding_functions
import pdfplumber
from openai import OpenAI


from langchain_community.utilities import SQLDatabase
from langchain.chains import create_sql_query_chain

from connect import ask_ollama_server
from templates.prompts import *
from langchain_community.embeddings import OllamaEmbeddings
import pickle
from llama_index.core.node_parser import SemanticSplitterNodeParser
from langchain_openai import OpenAIEmbeddings
from llama_index.core import SimpleDirectoryReader



import os

class Model:
    def __init__(self, pdf_path: str, working_with_ollama_server):
        self.logger = logging.getLogger(__name__)
        self.working_with_ollama_server = working_with_ollama_server
        logging.basicConfig(filename='py_log.log', encoding='utf-8', level=logging.DEBUG)
        self.pdf_path = pdf_path
        self.dict_of_chunks = {}
        self.client_openai = OpenAI()
        self.model_embedding = "text-embedding-3-large"
        self.model = "llama3.1"
        self.pkl_file = 'jezyk-polski.pkl'
        self.faiss_path = 'content/faiss'
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
            api_key="",
            model_name="text-embedding-3-large"
        )
        # Tworzymy kolekcję dokumentów w ChromaDB, jeśli jeszcze nie istnieje
        self.collection = self.client.get_or_create_collection(name="docs_openai", embedding_function=self.ollama_embedding_for_chromadb, metadata={"hnsw:space": "cosine"})
        # Wczytujemy dokument PDF
        self.document = self._read_document()
        # Ścieżka do pliku bazy danych SQL
        self.database_filename = os.path.abspath(os.path.join(os.path.dirname(__file__), '../content/plan_lekcji10.db'))
        self.db_path = os.path.join(os.getcwd(), self.database_filename)
        # Inicjalizacja połączenia z bazą SQL
        self.db = SQLDatabase.from_uri(f"sqlite:///{self.db_path}")
        # Lista osadzonych dokumentów (embeddingów)
        self.list_of_embeded_document = []
        # Generowanie embeddingów dla dokumentu
        self._embedding_document()
        # Tworzenie łańcucha zapytań SQL
        self.chain = create_sql_query_chain(self.llm_model_for_sql, self.db)
        # Funkcja ekstrakcji zapytań SQL
        self.sql_prompt_extractor = lambda x: x[x.find('SELECT'):] + ";" if x[x.find('SELECT'):].count(';') == 0 else x[x.find('SELECT'):x.rfind(';') + 1]

    def embedding_function(self, text, model=None):
        model = model or self.model_embedding
        data = self.client_openai.embeddings.create(input=text, model=model)
        return data.data[0].embedding


    def generation_function(self, text, model=None):
        model = model or self.model
        if self.working_with_ollama_server:
            return ask_ollama_server(prompt=text, model=model)['response']
        else:
            return ollama.generate(prompt=text, model=model)['response']

    def make_chunking(self) -> list:
        # Ładowanie danych z pliku PDF
        documents = SimpleDirectoryReader(input_files=[self.pdf_path]).load_data()
        # Dzielimy dokument na fragmenty za pomocą algorytmu segmentacji semantycznej
        splitter = SemanticSplitterNodeParser(
            buffer_size=3, breakpoint_percentile_threshold=95,
            embed_model=OpenAIEmbeddings(),
        )
        # Generowanie nodów (fragmentów tekstu)
        docs = splitter.get_nodes_from_documents(documents)
        # Zapisujemy pocięte dokumenty do pliku pickle
        with open(self.pkl_file, 'wb') as f:
            pickle.dump([i.get_content() for i in docs], f)
        # Zwracamy treść fragmentów dokumentu
        return [i.get_content() for i in docs]


    def _read_document(self):
        # Sprawdzamy, czy plik z osadzonymi fragmentami istnieje
        if not exists(self.pkl_file):
            self.make_chunking()
        # Ładujemy dane z pliku pickle
        with open(self.pkl_file, 'rb') as f:
            loaded_list = pickle.load(f)
            answer = []
            # Dodajemy niepusty tekst do listy "answer"
            _ = [answer.append(i) if len(i) > 0 else None for i in loaded_list]
            # # Generujemy opisy dla embeddingu
            # descriptions = self.generate_description_for_embedding(answer)
            # Dla każdego opisu generujemy embedding i aktualizujemy kolekcję w ChromaDB
            # for i, descr in enumerate(answer):
            #     embedding = self.embedding_function(descr)
            #     self.collection.update(documents=descr, ids=[f'{i}_id'], embeddings=[embedding], metadatas=[{"full_document": descr}])
            #     print(i)
            return answer


    def generate_description_for_embedding(self, data):
        # Generujemy krótkie opisy dla każdego fragmentu tekstu
        dictionary_of_chunks = {}
        print(len(data))
        for i, text in enumerate(data):
            key = self.generation_function(prompt_to_generate_shorter_text_for_embedding_template.format(text))
            key = key[key.find('"')+1:key.rfind('"')]
            dictionary_of_chunks[key] = text
            print(i)
        return dictionary_of_chunks


    def _embedding_document(self):
        try:
            # Pobieramy dane z kolekcji w ChromaDB
            data = self.collection.get()
            print(data)
            keys, values = data['documents'], list([i['full_document'] for i in data['metadatas']])
            print(len(keys), len(values))
            # Sprawdzamy, czy liczba kluczy (opisów) i wartości (dokumentów) się zgadza
            if len(keys) != len(values):
                raise 'len of description not equal len of document'
            # Tworzymy słownik fragmentów
            for key, value in zip(keys, values):
                self.dict_of_chunks[key] = value
            print('all')
        except Exception as e:
            print(e)
            # Jeśli wystąpi błąd, ponownie wczytujemy dane i aktualizujemy kolekcję
            with open(self.pkl_file, 'rb') as f:
                loaded_list = pickle.load(f)
                answer = []
                _ = [answer.append(i) if len(i) > 0 else None for i in loaded_list]
                descriptions = self.generate_description_for_embedding(answer)
                for i, descr in enumerate(descriptions):
                    # embedding = ollama.embeddings(model=self.model_embedding, prompt=descriptions[descr])["embedding"]
                    embedding = self.embedding_function(descriptions[descr])
                    self.collection.update(documents=descr, ids=[f'{i}_id'], embeddings=[embedding],
                                           metadatas=[{"full_document": descriptions[descr]}])
                data = self.collection.get()
                print(data)
                keys, values = data['documents'], list([i['full_document'] for i in data['metadatas']])
                print(len(keys), len(values))
                if len(keys) != len(values):
                    raise 'len of description not equal len of document'
                for key, value in zip(keys, values):
                    self.dict_of_chunks[key] = value
                print('all')

    def collection_is_empty(self):
        # Sprawdzamy, czy kolekcja w ChromaDB jest pusta
        all_data = self.collection.peek(limit=1)
        return len(all_data['ids']) == 0


    def ask_pdf(self, question: str) -> str:
        # Tworzymy embedding pytania
        # embedding_of_question = ollama.embeddings(model=self.model_embedding, prompt=question)["embedding"]
        embedding_of_question = self.embedding_function(question)
        # Wyszukujemy najbardziej pasujące dokumenty
        matched_docs = self.collection.query(query_embeddings=[embedding_of_question], n_results=5)
        print(matched_docs)
        print(matched_docs['documents'])
        # Zwracamy dopasowane dokumenty
        matched_docs = [i['full_document'] for i in matched_docs['metadatas'][0]]
        matched_docs = [f'{i+1} fragment tekstu: ' + text for i, text in enumerate(matched_docs)]
        matched_docs = "\n\n".join(matched_docs)
        print(matched_docs)
        # Generujemy odpowiedź na pytanie na podstawie fragmentów dokumentu
        output = self.generation_function(final_prompt_with_pdf_template.format(matched_docs, question))
        return output


    def _generate_prompt_to_sql(self, question):
        for i in range(20):
            try:
                # Wysyłamy zapytanie do łańcucha SQL
                response = self.chain.invoke({"question": prompt_to_sql_database_template.format(question)})
                # Jeśli zapytanie SQL zwróci dane, generujemy odpowiedź
                answer = self.db.run(self.sql_prompt_extractor(response))
                if len(answer) > 0:
                    return response
                else:
                    continue
            except Exception:
                self.logger.info(f'{i} trying was unsuccessfully')
        return None


    def ask_sql(self, question):
        # Tworzymy zapytanie do bazy SQL
        response = self._generate_prompt_to_sql(question)
        if response:
            # Tworzymy odpowiedź na podstawie zapytania SQL
            db_context = self.sql_prompt_extractor(response)
            db_answer = self.db.run(db_context)
            self.logger.info(db_context)
            self.logger.info(db_answer)
            # Generujemy odpowiedź w zależności od serwera Ollama
            return self.generation_function(final_prompt_sql_template.format(question=question, result=db_answer, request_to_sql=db_context))
        else:
            # Jeśli zapytanie SQL się nie powiedzie, zwracamy odpowiedź błędną
            return 'Niestety nie udało się znaleść jakiejkolwiek informacji, sprobójcie przeformulować prompt lub zapytajcie o czymś innym'


    def ask_api(self, _json: dict):
        # Wybieramy odpowiednią metodę odpowiedzi na podstawie typu pliku
        question = _json.get('question')
        selected_option = _json.get('file')
        if selected_option == "polski":
            answer = self.ask_pdf(question)
        else:
            answer = self.ask_sql(question)
        json_answer = {'answer': answer}
        return json_answer
