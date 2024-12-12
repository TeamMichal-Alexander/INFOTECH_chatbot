from model import Communication, Models, Files
import os
from flask import Flask, request, jsonify
import os
from dotenv import load_dotenv
from huggingface_hub import login


app = Flask(__name__)
my_class_instance=None
def create_model_instance():
    global my_class_instance
    # login(token=os.getenv('HUGGING_FACE_TOKEN'))
    if my_class_instance is None:
        dotenv_path = os.path.join(os.path.dirname(__file__), '../.env')
        if os.path.exists(dotenv_path):
            load_dotenv(dotenv_path)
        os.environ["OPENAI_API_KEY"] = os.environ.get('OPENAI_API_KEY')
        os.environ["UNSTRUCTURED_API_KEY"] = os.environ.get('UNSTRUCTURED_API_KEY')

        working_with_ollama_server = True

        files = Files(['historia2', 'jezyk-polski', 'fizyka2', 'polski2_1', 'matematyka2'], working_with_ollama_server)
        my_class_instance = Communication(pdf_path=os.path.abspath(os.path.join(os.path.dirname(__file__), '../content/historia2.pdf')), working_with_ollama_server=working_with_ollama_server, files=files)

@app.route('/api/model/ask', methods=['POST'])
async def action():
    data = request.json
    print(data)
    result = await my_class_instance.ask_api(data)
    return jsonify(result)

if __name__ == '__main__':
    create_model_instance()
    app.run(debug=True, use_reloader=False)