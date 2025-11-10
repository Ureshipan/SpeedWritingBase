from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import random
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///speedwriting.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


# Модели базы данных
class Street(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    length = db.Column(db.Integer, nullable=False)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'length': self.length
        }


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
    
    # Сначала пытаемся найти улицы точно заданной длины
    streets = Street.query.filter_by(length=length).all()
    
    # Если нет точно такой длины, ищем близкую (±2 символа)
    if not streets:
        streets = Street.query.filter(
            Street.length >= length - 2,
            Street.length <= length + 2
        ).all()
    
    # Если всё ещё нет, берём любую доступную
    if not streets:
        streets = Street.query.all()
    
    if not streets:
        return jsonify({'error': 'No streets found in database'}), 404
    
    # Выбираем случайную улицу
    random_street = random.choice(streets)
    return jsonify(random_street.to_dict())


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


def init_db():
    """Инициализация базы данных с московскими улицами"""
    with app.app_context():
        db.create_all()
        
        # Проверяем, есть ли уже улицы в базе
        if Street.query.count() > 0:
            print("Database already initialized")
            return
        
        # Список московских улиц с разной длиной
        moscow_streets = [
            # Короткие (5-10 символов)
            "Арбат", "Тверская", "Красная", "Лубянка", "Сретенка",
            "Пятницкая", "Остоженка", "Пречистенка", "Варварка", "Ильинка",
            "Петровка", "Мясницкая", "Никитская", "Знаменка", "Волхонка",
            "Поварская", "Спиридоньевка", "Гранатный", "Садовая",
            
            # Средние (11-20 символов)
            "Кутузовский проспект", "Ленинский проспект", "Проспект Мира",
            "Тверской бульвар", "Никитский бульвар", "Гоголевский бульвар",
            "Малая Бронная", "Большая Полянка", "Большая Ордынка",
            "Малая Ордынка", "Большая Дмитровка", "Малая Дмитровка",
            "Большая Лубянка", "Малая Лубянка", "Новослободская",
            "Садовая-Спасская", "Садовая-Сухаревская", "Садовая-Каретная",
            "Садовая-Триумфальная", "Садовая-Кудринская", "Садовая-Самотечная",
            "Садовая-Черногрязская", "Садовая-Спасская", "Садовая-Триумфальная",
            "Большая Никитская", "Малая Никитская", "Большая Пироговская",
            "Малая Пироговская", "Большая Якиманка", "Малая Якиманка",
            "Большая Серпуховская", "Малая Серпуховская", "Большая Грузинская",
            "Малая Грузинская", "Большая Дорогомиловская", "Малая Дорогомиловская",
            
            # Длинные (21-30 символов)
            "Новоарбатский проспект", "Краснопресненская набережная",
            "Берсеневская набережная", "Софийская набережная",
            "Пречистенская набережная", "Кремлевская набережная",
            "Красная площадь", "Театральная площадь", "Манежная площадь",
            "Пушкинская площадь", "Славянская площадь", "Боровицкая площадь",
            "Тверская площадь", "Лубянская площадь", "Смоленская площадь",
            "Арбатская площадь", "Суворовская площадь", "Комсомольская площадь",
            "Калужская площадь", "Серпуховская площадь", "Добрынинская площадь",
            "Павелецкая площадь", "Курская площадь", "Рижская площадь",
        ]
        
        for street_name in moscow_streets:
            street = Street(name=street_name, length=len(street_name))
            db.session.add(street)
        
        db.session.commit()
        print(f"Initialized database with {len(moscow_streets)} streets")


if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)

