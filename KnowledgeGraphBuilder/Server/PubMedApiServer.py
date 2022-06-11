from flask import Flask, json

PubMedApi = Flask(__name__)

f = open('articles_bulk.json')
data = json.load(f)
i = -1

@PubMedApi.route("/getData")
def getData():
    global i
    global data

    i += 1
    if i == len(data):
        i = 0
        
    article = data.pop(i)
    text_full_text = article['full_text']['text']
    for item in article['full_text']['sections']:
        text_full_text += item['text']
    resp = {
        "text": text_full_text,
    }
    return json.dumps(resp)


if __name__ == "__main__":
    PubMedApi.run(debug=True,
            host='0.0.0.0',
            port=9000)