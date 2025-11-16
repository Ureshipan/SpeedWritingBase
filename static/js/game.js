class SpeedTypingGame {
    constructor() {
        this.isPlaying = false;
        this.isPaused = false;
        this.currentStreet = null;
        this.score = 0;
        this.lives = 3;
        this.wordsTyped = 0;
        this.mistakes = 0;
        this.totalChars = 0;
        this.correctChars = 0;
        this.startTime = null;
        this.carPosition = 0;
        this.targetPosition = 0;
        this.lastInputLength = 0;
        this.mistakeHandled = false;
        
        this.initializeElements();
        this.attachEventListeners();
    }
    
    initializeElements() {
        this.startBtn = document.getElementById('start-btn');
        this.pauseBtn = document.getElementById('pause-btn');
        this.resetBtn = document.getElementById('reset-btn');
        this.restartBtn = document.getElementById('restart-btn');
        this.typingInput = document.getElementById('typing-input');
        this.streetDisplay = document.getElementById('street-display');
        this.car = document.getElementById('car');
        this.finishLine = document.getElementById('finish-line');
        this.progressFill = document.getElementById('progress-fill');
        this.gameOver = document.getElementById('game-over');
        
        // Stats elements
        this.scoreElement = document.getElementById('score');
        this.livesElement = document.getElementById('lives');
        this.accuracyElement = document.getElementById('accuracy');
    }
    
    attachEventListeners() {
        this.startBtn.addEventListener('click', () => this.startGame());
        this.pauseBtn.addEventListener('click', () => this.togglePause());
        this.resetBtn.addEventListener('click', () => this.resetGame());
        this.restartBtn.addEventListener('click', () => {
            this.gameOver.style.display = 'none';
            this.resetGame();
        });
        
        this.typingInput.addEventListener('input', (e) => this.handleInput(e));
        this.typingInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !this.isPlaying) {
                this.startGame();
            }
        });
    }
    
    async startGame() {
        if (this.isPlaying && !this.isPaused) return;
        
        if (this.isPaused) {
            this.isPaused = false;
            this.pauseBtn.textContent = 'Пауза';
            this.typingInput.disabled = false;
            this.typingInput.focus();
            return;
        }
        
        this.isPlaying = true;
        this.isPaused = false;
        this.score = 0;
        this.lives = 3;
        this.wordsTyped = 0;
        this.mistakes = 0;
        this.totalChars = 0;
        this.correctChars = 0;
        this.startTime = Date.now();
        this.carPosition = 0;
        
        this.updateStats();
        this.startBtn.disabled = true;
        this.pauseBtn.disabled = false;
        this.resetBtn.disabled = false;
        this.typingInput.disabled = false;
        this.typingInput.focus();
        
        // Сброс позиции машинки
        this.car.style.transform = 'translateX(0)';
        
        await this.loadNextStreet();
    }
    
    togglePause() {
        if (!this.isPlaying) return;
        
        this.isPaused = !this.isPaused;
        this.typingInput.disabled = this.isPaused;
        this.pauseBtn.textContent = this.isPaused ? 'Продолжить' : 'Пауза';
        
        if (!this.isPaused) {
            this.typingInput.focus();
        }
    }
    
    resetGame() {
        this.isPlaying = false;
        this.isPaused = false;
        this.currentStreet = null;
        this.carPosition = 0;
        this.lastInputLength = 0;
        this.mistakeHandled = false;
        
        this.startBtn.disabled = false;
        this.pauseBtn.disabled = true;
        this.resetBtn.disabled = false;
        this.typingInput.disabled = true;
        this.typingInput.value = '';
        this.typingInput.className = 'typing-input';
        
        this.streetDisplay.innerHTML = '<p class="instruction">Нажмите "Начать заезд" чтобы начать</p>';
        this.progressFill.style.width = '0%';
        this.car.style.transform = 'translateX(0)';
        this.car.classList.remove('crashed');
        
        this.updateStats();
    }
    
    async loadNextStreet() {
        if (!this.isPlaying || this.isPaused) return;
        
        // Определяем длину улицы (начинаем с коротких, постепенно увеличиваем)
        const baseLength = 10;
        const lengthVariation = Math.floor(this.wordsTyped / 3);
        const targetLength = Math.min(baseLength + lengthVariation * 2, 40);
        
        try {
            const response = await fetch(`/api/street?length=${targetLength}`);
            if (!response.ok) {
                throw new Error('Failed to fetch street');
            }
            
            const data = await response.json();
            this.currentStreet = data;
            this.displayStreet(data.name, data.type);
            this.typingInput.value = '';
            this.typingInput.className = 'typing-input';
            this.progressFill.style.width = '0%';
            this.lastInputLength = 0;
            this.mistakeHandled = false;
            this.typingInput.focus();
        } catch (error) {
            console.error('Error loading street:', error);
            this.streetDisplay.innerHTML = '<p class="instruction" style="color: red;">Ошибка загрузки улицы</p>';
        }
    }
    
    displayStreet(name, type) {
        // Отображаем название обычным цветом, а тип - серым
        this.streetDisplay.innerHTML = `
            <p class="street-name">
                <span class="street-name-text">${name}</span>
                <span class="street-type-text"> ${type}</span>
            </p>
        `;
    }
    
    handleInput(e) {
        if (!this.isPlaying || this.isPaused || !this.currentStreet) return;
        
        const input = e.target.value;
        // Проверяем только название, без типа
        const target = this.currentStreet.name;
        
        // Проверяем, увеличилась ли длина ввода (новый символ)
        const isNewChar = input.length > this.lastInputLength;
        this.lastInputLength = input.length;
        
        // Обновляем статистику символов
        if (isNewChar) {
            this.totalChars++;
            if (input.length <= target.length && input === target.substring(0, input.length)) {
                this.correctChars++;
                this.typingInput.classList.remove('incorrect');
                this.typingInput.classList.add('correct');
                this.mistakeHandled = false; // Сброс флага ошибки при правильном вводе
            } else {
                this.typingInput.classList.remove('correct');
                this.typingInput.classList.add('incorrect');
                
                // Ошибка засчитывается только один раз за неправильный ввод
                if (!this.mistakeHandled) {
                    this.handleMistake();
                    this.mistakeHandled = true;
                }
            }
        }
        
        // Обновляем прогресс (только если ввод правильный)
        if (input.length <= target.length && input === target.substring(0, input.length)) {
            const progress = (input.length / target.length) * 100;
            this.progressFill.style.width = `${Math.min(progress, 100)}%`;
            this.updateCarPosition(progress);
        }
        
        // Проверка на завершение слова
        if (input === target) {
            this.handleCorrectWord();
        }
    }
    
    updateCarPosition(progress) {
        const roadWidth = document.querySelector('.road-container').offsetWidth;
        const maxPosition = roadWidth - 150; // Оставляем место для финиша
        this.carPosition = (progress / 100) * maxPosition;
        this.car.style.transform = `translateX(${this.carPosition}px)`;
    }
    
    handleCorrectWord() {
        this.wordsTyped++;
        this.score += Math.floor(100 * (1 + this.wordsTyped / 10));
        this.updateStats();
        
        // Анимация успеха
        this.typingInput.classList.add('correct');
        
        setTimeout(() => {
            if (this.isPlaying && !this.isPaused) {
                this.loadNextStreet();
            }
        }, 300);
    }
    
    handleMistake() {
        this.mistakes++;
        this.lives--;
        this.updateStats();
        
        // Анимация аварии
        this.car.classList.add('crashed');
        setTimeout(() => {
            this.car.classList.remove('crashed');
        }, 500);
        
        // Откат машинки назад (на 20% от текущей позиции)
        const roadWidth = document.querySelector('.road-container').offsetWidth;
        const maxPosition = roadWidth - 150;
        this.carPosition = Math.max(0, this.carPosition * 0.8);
        this.car.style.transform = `translateX(${this.carPosition}px)`;
        
        // Откат прогресс-бара и очистка неправильного ввода
        if (this.currentStreet) {
            // Проверяем только название, без типа
            const target = this.currentStreet.name;
            const input = this.typingInput.value;
            
            // Находим правильную часть ввода
            let correctPart = '';
            for (let i = 0; i < Math.min(input.length, target.length); i++) {
                if (input[i] === target[i]) {
                    correctPart += input[i];
                } else {
                    break;
                }
            }
            
            // Оставляем только правильную часть
            this.typingInput.value = correctPart;
            this.lastInputLength = correctPart.length;
            
            // Обновляем прогресс-бар
            const currentProgress = (correctPart.length / target.length) * 100;
            this.progressFill.style.width = `${currentProgress}%`;
            
            // Обновляем позицию машинки
            this.updateCarPosition(currentProgress);
        }
        
        // Проверка на окончание игры
        if (this.lives <= 0) {
            this.endGame();
        }
    }
    
    updateStats() {
        this.scoreElement.textContent = this.score;
        this.livesElement.textContent = this.lives;
        
        const accuracy = this.totalChars > 0 
            ? Math.round((this.correctChars / this.totalChars) * 100) 
            : 100;
        this.accuracyElement.textContent = `${accuracy}%`;
    }
    
    async endGame() {
        this.isPlaying = false;
        this.isPaused = false;
        this.typingInput.disabled = true;
        this.startBtn.disabled = false;
        this.pauseBtn.disabled = true;
        
        const timeSpent = (Date.now() - this.startTime) / 1000;
        const accuracy = this.totalChars > 0 
            ? (this.correctChars / this.totalChars) * 100 
            : 100;
        
        // Сохраняем результат на сервере
        try {
            await fetch('/api/result', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    score: this.score,
                    accuracy: accuracy,
                    words_typed: this.wordsTyped,
                    mistakes: this.mistakes,
                    time_spent: timeSpent
                })
            });
        } catch (error) {
            console.error('Error saving result:', error);
        }
        
        // Показываем экран окончания игры
        document.getElementById('final-score').textContent = this.score;
        document.getElementById('final-accuracy').textContent = `${Math.round(accuracy)}%`;
        document.getElementById('final-words').textContent = this.wordsTyped;
        this.gameOver.style.display = 'flex';
    }
}

// Инициализация игры при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    new SpeedTypingGame();
});

