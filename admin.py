from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from . import db
from .models import Question, Law, Article
import csv
import openai
import json

admin_bp = Blueprint('admin', __name__)

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('Acesso negado.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated

@admin_bp.route('/', methods=['GET'])
@admin_required
def admin_index():
    return render_template('admin_index.html')

@admin_bp.route('/import', methods=['GET','POST'])
@admin_required
def import_csv():
    if request.method=='POST':
        file = request.files['csv_file']
        stream = file.stream.read().decode('utf-8').splitlines()
        reader = csv.DictReader(stream)
        count=0
        for row in reader:
            law = Law.query.filter_by(name=row['law']).first() or Law(name=row['law'])
            db.session.add(law); db.session.flush()
            article = Article.query.filter_by(number=row['article'], law=law).first() or Article(number=row['article'], law=law)
            db.session.add(article); db.session.flush()
            q = Question(
                text=row['text'],
                type=row['type'],
                difficulty=row['difficulty'],
                law=law,
                article=article
            )
            db.session.add(q)
            count+=1
        db.session.commit()
        flash(f'{count} questões importadas.', 'success')
    return render_template('admin_import.html')

@admin_bp.route('/generate', methods=['GET','POST'])
@admin_required
def generate_questions():
    if request.method == 'POST':
        prompt = request.form.get('prompt')
        openai.api_key = current_app.config.get('OPENAI_API_KEY')
        full_prompt = (
            "Forneça um JSON array de objetos com chaves "
            "'text', 'type', 'difficulty', 'law', 'article' baseadas no seguinte prompt: " + prompt
        )
        try:
            response = openai.Completion.create(
                model='text-davinci-003',
                prompt=full_prompt,
                max_tokens=800,
                temperature=0.7
            )
            data_text = response.choices[0].text.strip()
            data = json.loads(data_text)
            count = 0
            for item in data:
                law = Law.query.filter_by(name=item.get('law')).first() or Law(name=item.get('law'))
                db.session.add(law); db.session.flush()
                article = Article.query.filter_by(number=item.get('article'), law=law).first() or Article(number=item.get('article'), law=law)
                db.session.add(article); db.session.flush()
                q = Question(
                    text=item.get('text'),
                    type=item.get('type'),
                    difficulty=item.get('difficulty'),
                    law=law,
                    article=article
                )
                db.session.add(q)
                count += 1
            db.session.commit()
            flash(f'Geradas e importadas {count} questões com IA.', 'success')
        except Exception as e:
            flash('Erro ao gerar questões via IA: ' + str(e), 'danger')
    return render_template('admin_generate.html')
