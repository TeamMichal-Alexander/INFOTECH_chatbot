import logging

import ollama
import chromadb
import pdfplumber

from langchain_community.utilities import SQLDatabase
from langchain.chains import create_sql_query_chain



from connect import ask_ollama_server
from templates.prompts import final_prompt_plan_lekcji_template, final_prompt_jezyk_polski_template, prompt_to_generate_sql_prompt_template

import os

class Model:
    def __init__(self, pdf_path: str, model_worked_on_server=True):
        logging.basicConfig(level=logging.INFO, filename="py_log.log", filemode="w")
        self.pdf_path = pdf_path
        self.model_embedding = "mxbai-embed-large"
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
        self.database_filename = './content/plan_lekcji10.db'
        self.db_path = os.path.join(os.getcwd(), self.database_filename)
        self.db = SQLDatabase.from_uri(f"sqlite:///{self.db_path}")
        self._embedding_document()
        self.chain = create_sql_query_chain(self.llm_model_for_sql, self.db)
        self.sql_prompt_extractor = lambda x: x[x.find('SELECT'):] + ";" if x[x.find('SELECT'):].count(';') == 0 else x[x.find('SELECT'):x.rfind(';') + 1]
        self.prompt_to_generate_sql_prompt_template = prompt_to_generate_sql_prompt_template
        self.final_prompt_plan_lekcji_template = final_prompt_plan_lekcji_template


    def _read_document(self):
        text = ""
        with pdfplumber.open(self.pdf_path) as pdf:
            for page in pdf.pages:
                text += page.extract_text() + "\n"
        document = text.split('---')
        for i in text.split('___'):
            document.append(i)
        return document


    def _embedding_document(self):
        for i, d in enumerate(self.document):
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
            n_results=2)

        data = "\n".join([doc[0] for doc in results['documents']])

        output = self.function_model_ollama(
            model=self.model_name,
            prompt=self.final_prompt_jezyk_polski_template.format(data, question))

        return output['response']

    def attempt_sql_query(self, question):
        max_attempts = 10

        for attempt in range(max_attempts):
            logging.info('Attempting to generate SQL query, attempt #%d', attempt + 1)
            try:
                response = self.chain.invoke({"question": self.prompt_to_generate_sql_prompt_template.format(question)})
                logging.info('Response received on attempt #%d', attempt + 1)
                break
            except Exception as e:
                logging.error('Error occurred during SQL query generation attempt #%d: %s', attempt + 1, e)
        else:
            logging.error('All attempts to generate SQL query failed.')
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
        if selected_option == "polski":
            answer = self.ask_pdf(question)
        else:
            answer = self.ask_sql(question)
        json_answer = {'answer': answer}
        return json_answer