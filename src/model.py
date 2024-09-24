import logging

import ollama
import chromadb
import pdfplumber

import re

from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains.retrieval import create_retrieval_chain
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.embeddings import HuggingFaceBgeEmbeddings, OllamaEmbeddings
from langchain_community.utilities import SQLDatabase
from langchain.chains import create_sql_query_chain
from langchain_community.vectorstores import FAISS
from langchain_experimental.text_splitter import SemanticChunker
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from connect import ask_ollama_server
from templates.prompts import final_prompt_plan_lekcji_template, final_prompt_jezyk_polski_template, prompt_to_generate_sql_prompt_template

import os

class Model:
    def __init__(self, pdf_path: str, model_worked_on_server=True):
        logging.basicConfig(level=logging.INFO, filename="py_log.log", filemode="w")
        self.pdf_path = pdf_path
        self.model_embedding = "nomic-embed-text"
        self.model_name = "llama3.1"
        if model_worked_on_server:
            from copy_ollama_function_ChatOllama import ChatOllama
            self.function_model_ollama = ask_ollama_server
        else:
            from langchain_community.chat_models import ChatOllama
            self.function_model_ollama = ollama.generate
        self.llm_model_for_sql = ChatOllama(model='llama3.1')
        self.final_prompt_jezyk_polski_template = final_prompt_jezyk_polski_template
        self.client = chromadb.Client()
        self.collection = self.client.get_or_create_collection(name="docs")
        self.document = self._read_document()
        self.database_filename = os.path.abspath(os.path.join(os.path.dirname(__file__), '../content/plan_lekcji10.db'))
        self.db_path = os.path.join(os.getcwd(), self.database_filename)
        self.db = SQLDatabase.from_uri(f"sqlite:///{self.db_path}")
        print(self.db.get_context())
        self._embedding_document()
        self.chain = create_sql_query_chain(self.llm_model_for_sql, self.db)
        self.sql_prompt_extractor = lambda x: x[x.find('SELECT'):] + ";" if x[x.find('SELECT'):].count(';') == 0 else x[x.find('SELECT'):x.rfind(';') + 1]
        self.prompt_to_generate_sql_prompt_template = prompt_to_generate_sql_prompt_template
        self.final_prompt_plan_lekcji_template = final_prompt_plan_lekcji_template


    def _read_document(self):
        text = ""
        with pdfplumber.open(self.pdf_path) as pdf:
            # for page in pdf.pages:
            #     text += page.extract_text() + "\n"
        # document = text.split('---')
        # for i in text.split('___'):
        #     document.append(i)
        # return document
            splitter = SemanticChunker(
                OllamaEmbeddings(model="nomic-embed-text"), breakpoint_threshold_type="standard_deviation"
            )
            document = [document.page_content for document in splitter.split_documents(PyPDFLoader(self.pdf_path).load())]

            print(len(document))
            with open("output.txt", "w", encoding="utf-8") as file:
                for item in document:
                    # Записываем элемент и добавляем два переноса строки
                    file.write(item + "\n\n")
            return document


    def _embedding_document(self):
        for i, d in enumerate(self.document):
            if len(d) > 0:
                response = ollama.embeddings(model=self.model_embedding, prompt=d)
                embedding = response["embedding"]
                self.collection.add(
                    ids=[str(i)],
                    embeddings=[embedding],
                    documents=[d])


    def collection_is_empty(self):
        all_data = self.collection.peek(limit=1)
        return len(all_data['ids']) == 0


    def ask_pdf(self, question: str) -> str:
        response = ollama.embeddings(
            prompt=question,
            model=self.model_embedding)

        results = self.collection.query(
            query_embeddings=[response["embedding"]],
            n_results=8)
        print(results)
        data = "\n\n".join([doc for doc in results['documents'][0]])

        print(data)

        output = self.function_model_ollama(
            model=self.model_name,
            prompt=self.final_prompt_jezyk_polski_template.format(data, question))
        return output['response']

    def attempt_sql_query(self, question):
        max_attempts = 20

        for attempt in range(max_attempts):
            logging.info('Attempting to generate SQL query, attempt #%d', attempt + 1)
            try:
                response = self.chain.invoke({"question": self.prompt_to_generate_sql_prompt_template.format(question)})
                print(response)
                response = self.sql_prompt_extractor(response)
                self.db.run(response)
                logging.info('Response received on attempt #%d', attempt + 1)
                break
            except Exception as e:
                logging.error('Error occurred during SQL query generation attempt #%d: %s', attempt + 1, e)
        else:
            logging.warning('All attempts to generate SQL query failed.')
            return None
        return response


    def ask_sql(self, question):
        logging.info('Program just entered in ask_sql function')
        response = self.attempt_sql_query(question)
        if response is not None:
            db_context = self.sql_prompt_extractor(response)
            db_answer = self.db.run(db_context)
            human_final_prompt = self.final_prompt_plan_lekcji_template.format(question=question, result=db_answer, request_to_sql=db_context)

            logging.info('Final prompt to sql: ' + db_context)
            logging.info('Final answer of sql: ' + db_answer)

            output = self.function_model_ollama(prompt=human_final_prompt, model=self.model_name)
            return output['response']
        else:
            return 'Niestety nie udało się znaleść jakiejkolwiek informacji, sprobójcie przeformulować prompt lub zapytajcie o czymś innym'

    def ask_api(self, _json: dict):
        question = _json.get('question')
        selected_option = _json.get('file')
        print(selected_option)
        if selected_option == "polski":
            answer = self.ask_pdf(question)
        else:
            answer = self.ask_sql(question)
        json_answer = {'answer': answer}
        return json_answer