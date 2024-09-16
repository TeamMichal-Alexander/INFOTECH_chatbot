from flask import Flask, request, jsonify
from model import Model
import os
import json

app = Flask(__name__)
my_class_instance = Model(pdf_path=os.path.abspath(os.path.join(os.path.dirname(__file__), '../content/język_polski_new.pdf')))

@app.route('/api/model/ask', methods=['POST'])
def action():
    data = request.json
    print(data)
    result = my_class_instance.ask_api(data)
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True)