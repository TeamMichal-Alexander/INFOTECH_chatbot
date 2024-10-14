from model import Model
import os
from flask import Flask, request, jsonify


app = Flask(__name__)
my_class_instance=None
def create_model_instance():
    global my_class_instance
    if my_class_instance is None:
        my_class_instance = Model(pdf_path=os.path.abspath(os.path.join(os.path.dirname(__file__), '../content/język_polski_new.pdf')), working_with_ollama_server=False)

@app.route('/api/model/ask', methods=['POST'])
def action():
    create_model_instance()
    data = request.json
    print(data)
    result = my_class_instance.ask_api(data)
    return jsonify(result)

if __name__ == '__main__':
    create_model_instance()
    app.run(debug=True, use_reloader=False)