import ollama
import chromadb
import pdfplumber


class Model:
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.model_embedding = "mxbai-embed-large"
        self.model = "llama3.1"
        self.prompt = ("""Jesteś botem Q&A, ode mnie otrzymasz fragmenty tekstu z planu nauki języka polskiego w szkole ponadpodstawowej, ten plan jest dokładny. Otrzymasz również pytanie, na które musisz odpowiedzieć, opierając się na fragmentach tekstu. Twoja odpowiedź powinna być dokładna, bez zbędnych informacji, ale informatywna i rozszerzona. Jeśli nie znasz odpowiedzi, poproś o przekształcenie pytania. 
Oto fragmenty tekstu: [{}] 
Pytanie: [{}]""")
        self.client = chromadb.Client()
        self.collection = self.client.create_collection(name="docs")
        self.document = self._read_document()
        self._embedding_document()

    def _read_document(self):
        text = ""
        with pdfplumber.open(self.pdf_path) as pdf:
            for page in pdf.pages:
                text += page.extract_text() + "\n"
        print(text)
        document = text.split('|')
        for i in text.split('{}'):
            document.append(i)
        print(len(document))
        return document


    def _embedding_document(self):
        for i, d in enumerate(self.document):
            response = ollama.embeddings(model=self.model_embedding, prompt=d)
            embedding = response["embedding"]
            self.collection.add(
                ids=[str(i)],
                embeddings=[embedding],
                documents=[d])


    def ask(self, question: str) -> str:
        response = ollama.embeddings(
            prompt=question,
            model=self.model_embedding)

        results = self.collection.query(
            query_embeddings=[response["embedding"]],
            n_results=3)

        print(results['documents'])
        data = "\n".join([doc[0] for doc in results['documents']])

        output = ollama.generate(
            model=self.model,
            prompt=self.prompt.format(data, question))

        return output['response']