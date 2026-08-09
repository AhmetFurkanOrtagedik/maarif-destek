from flask import Flask, render_template, request, jsonify
from data import get_themes_by_grade
from pdf_analyzer import analyze_curriculum

app = Flask(__name__)

@app.route('/')
def index():
    # Başlangıçta 9. sınıf temalarını yükleyelim (varsayılan)
    default_grade = "9"
    themes = get_themes_by_grade(default_grade)
    return render_template('index.html', default_themes=themes)

@app.route('/api/themes', methods=['GET'])
def get_themes():
    grade = request.args.get('grade')
    themes = get_themes_by_grade(grade)
    return jsonify({"themes": themes})

@app.route('/api/analyze', methods=['POST'])
def analyze():
    data = request.json
    grade = data.get('grade')
    theme = data.get('theme')
    
    # data.py yerine doğrudan PDF'leri tarayan yapay zekayı çağırıyoruz
    content = analyze_curriculum(grade, theme)
    return jsonify(content)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
