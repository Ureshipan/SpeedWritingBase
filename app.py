from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import random
import os
import yaml

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///speedwriting.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


# Модели базы данных
class GameResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(100), nullable=True)  # Для будущей системы регистрации
    score = db.Column(db.Integer, nullable=False)
    accuracy = db.Column(db.Float, nullable=False)
    words_typed = db.Column(db.Integer, nullable=False)
    mistakes = db.Column(db.Integer, nullable=False)
    time_spent = db.Column(db.Float, nullable=False)  # в секундах
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'score': self.score,
            'accuracy': self.accuracy,
            'words_typed': self.words_typed,
            'mistakes': self.mistakes,
            'time_spent': self.time_spent,
            'created_at': self.created_at.isoformat()
        }


# API Routes
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/street', methods=['GET'])
def get_street():
    """Получить случайную улицу заданной длины (и типа)"""
    length = request.args.get('length', type=int)
    street_type = request.args.get('street_type', type=str)

    if not length or length < 1:
        return jsonify({'error': 'Length parameter is required and must be positive'}), 400

    # Загружаем улицы из YAML (с кэшированием)
    all_streets = load_streets_from_yaml()

    if not all_streets:
        return jsonify({'error': 'No streets found'}), 404

    # Фильтрация по типу улицы (если передан параметр)
    if street_type:
        street_type = street_type.lower()
        all_streets = [
            s for s in all_streets
            if s['type'].lower() == street_type
        ]

        if not all_streets:
            return jsonify({
                'error': f'No streets found with type: {street_type}'
            }), 404

    # Сначала пытаемся найти улицы точно заданной длины (длина названия без типа)
    streets = [s for s in all_streets if s['length'] == length]

    # Если нет точно такой длины, ищем близкую (±2 символа)
    if not streets:
        streets = [
            s for s in all_streets
            if length - 2 <= s['length'] <= length + 2
        ]

    # Если всё ещё нет, берём любую доступную
    if not streets:
        streets = all_streets

    # Выбираем случайную улицу
    random_street = random.choice(streets)
    return jsonify(random_street)


@app.route('/api/result', methods=['POST'])
def save_result():
    """Сохранить результат игры"""
    data = request.json

    required_fields = ['score', 'accuracy', 'words_typed', 'mistakes', 'time_spent']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Missing required field: {field}'}), 400

    # Проверка типов данных
    try:
        score = int(data['score'])
        accuracy = float(data['accuracy'])
        words_typed = int(data['words_typed'])
        mistakes = int(data['mistakes'])
        time_spent = float(data['time_spent'])
    except (TypeError, ValueError):
        return jsonify({'error': 'Invalid data types'}), 400

    # Валидация значений
    if score < 0:
        return jsonify({'error': 'Score must be non-negative'}), 400
    if not 0 <= accuracy <= 100:
        return jsonify({'error': 'Accuracy must be between 0 and 100'}), 400
    if words_typed < 0:
        return jsonify({'error': 'Words typed must be non-negative'}), 400
    if mistakes < 0:
        return jsonify({'error': 'Mistakes must be non-negative'}), 400
    if time_spent <= 0:
        return jsonify({'error': 'Time spent must be greater than zero'}), 400

    result = GameResult(
        user_id=data.get('user_id'),  # Может быть None для анонимных игроков
        score=score,
        accuracy=accuracy,
        words_typed=words_typed,
        mistakes=mistakes,
        time_spent=time_spent
    )

    db.session.add(result)
    db.session.commit()

    return jsonify({'success': True, 'result_id': result.id}), 201


@app.route('/api/results', methods=['GET'])
def get_results():
    """Получить результаты (для будущего использования)"""
    user_id = request.args.get('user_id')
    limit = request.args.get('limit', 10, type=int)

    query = GameResult.query
    if user_id:
        query = query.filter_by(user_id=user_id)

    results = query.order_by(GameResult.created_at.desc()).limit(limit).all()
    return jsonify([r.to_dict() for r in results])


@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Получить общую статистику по всем играм"""
    total_games = GameResult.query.count()

    if total_games == 0:
        return jsonify({
            'total_games': 0,
            'average_accuracy': 0,
            'average_score': 0,
            'max_score': 0,
            'total_words_typed': 0
        })

    avg_accuracy = db.session.query(
        db.func.avg(GameResult.accuracy)
    ).scalar() or 0

    avg_score = db.session.query(
        db.func.avg(GameResult.score)
    ).scalar() or 0

    max_score = db.session.query(
        db.func.max(GameResult.score)
    ).scalar() or 0

    total_words = db.session.query(
        db.func.sum(GameResult.words_typed)
    ).scalar() or 0

    return jsonify({
        'total_games': total_games,
        'average_accuracy': round(avg_accuracy, 2),
        'average_score': round(avg_score, 2),
        'max_score': max_score,
        'total_words_typed': total_words
    })


# Кэш для улиц (загружается один раз при первом запросе)
_streets_cache = None


def parse_street_name(full_name):
    """Разделяет полное название улицы на название и тип"""
    full_name = full_name.lstrip('- ').strip()

    # Список типов улиц (от более длинных к более коротким)
    street_types = [
        'набережная', 'проспект', 'площадь', 'бульвар', 'шоссе',
        'переулок', 'проезд', 'аллея', 'улица', 'просека',
        'мост', 'линия', 'тупик', 'эстакада', 'тоннель'
    ]

    # Проверка, если тип указан в начале строки
    for street_type in street_types:
        if full_name.lower().startswith(street_type + ' '):
            name_part = full_name[len(street_type):].strip()
            return name_part, street_type

    # Проверка, если тип указан в конце строки
    for street_type in street_types:
        if full_name.lower().endswith(street_type):
            name_part = full_name[:-len(street_type)].strip()
            return name_part, street_type

    # Если тип не найден
    return full_name, 'улица'


def load_streets_from_yaml():
    """Загружает улицы из YAML файла и кэширует в памяти"""
    global _streets_cache

    if _streets_cache is not None:
        return _streets_cache

    yaml_path = os.path.join(os.path.dirname(__file__), 'data', 'moscow_streets.yaml')

    if not os.path.exists(yaml_path):
        print(f"Error: YAML file not found at {yaml_path}")
        _streets_cache = []
        return _streets_cache

    try:
        with open(yaml_path, 'r', encoding='utf-8') as f:
            streets_list = yaml.safe_load(f)

        if not streets_list:
            print("Error: YAML file is empty or invalid")
            _streets_cache = []
            return _streets_cache

        streets = []
        for full_name in streets_list:
            if not full_name or not isinstance(full_name, str):
                continue

            name, street_type = parse_street_name(full_name)
            streets.append({
                'name': name,
                'type': street_type,
                'full_name': full_name,
                'length': len(name)
            })

        _streets_cache = streets
        print(f"Loaded {len(streets)} streets from YAML")
        return _streets_cache

    except Exception as e:
        print(f"Error loading streets from YAML: {e}")
        _streets_cache = []
        return _streets_cache


def init_db():
    """Инициализация базы данных (только для GameResult)"""
    with app.app_context():
        db.create_all()
        print("Database initialized")


if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5100)