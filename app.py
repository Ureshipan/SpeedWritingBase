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
    """Получить случайную улицу заданной длины (или близкой)"""
    length = request.args.get('length', type=int)
    
    if not length or length < 1:
        return jsonify({'error': 'Length parameter is required and must be positive'}), 400
    
    # Загружаем улицы из YAML (с кэшированием)
    all_streets = load_streets_from_yaml()
    
    if not all_streets:
        return jsonify({'error': 'No streets found'}), 404
    
    # Сначала пытаемся найти улицы точно заданной длины (длина названия без типа)
    streets = [s for s in all_streets if s['length'] == length]
    
    # Если нет точно такой длины, ищем близкую (±2 символа)
    if not streets:
        streets = [s for s in all_streets if length - 2 <= s['length'] <= length + 2]
    
    # Если всё ещё нет, берём любую доступную
    if not streets:
        streets = all_streets
    
    if not streets:
        return jsonify({'error': 'No streets found'}), 404
    
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
    
    result = GameResult(
        user_id=data.get('user_id'),  # Может быть None для анонимных игроков
        score=data['score'],
        accuracy=data['accuracy'],
        words_typed=data['words_typed'],
        mistakes=data['mistakes'],
        time_spent=data['time_spent']
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


# Кэш для улиц (загружается один раз при первом запросе)
_streets_cache = None


def parse_street_name(full_name):
    """Разделяет полное название улицы на название и тип"""
    # Убираем дефис в начале, если есть
    full_name = full_name.lstrip('- ').strip()
    
    # Список типов улиц (от более длинных к более коротким для правильного распознавания)
    street_types = [
        'набережная', 'проспект', 'площадь', 'бульвар', 'шоссе', 
        'переулок', 'проезд', 'аллея', 'улица', 'просека', 
        'мост', 'линия', 'тупик', 'эстакада', 'тоннель'
    ]
    
    # Сначала проверяем, не начинается ли строка с типа (например, "проспект Мира")
    for street_type in street_types:
        if full_name.lower().startswith(street_type.lower() + ' '):
            # Тип в начале, название после
            name_part = full_name[len(street_type):].strip()
            return name_part, street_type
    
    # Если тип не в начале, ищем в конце строки
    for street_type in street_types:
        if full_name.lower().endswith(' ' + street_type.lower()) or full_name.lower().endswith(street_type.lower()):
            # Находим позицию начала типа
            name_part = full_name[:len(full_name) - len(street_type)].strip()
            return name_part, street_type
    
    # Если тип не найден, считаем что это просто название
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
        
        # Обрабатываем каждую улицу
        streets = []
        for full_name in streets_list:
            if not full_name or not isinstance(full_name, str):
                continue
            
            # Разделяем название и тип
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
    app.run(debug=True, host='0.0.0.0', port=5000)

