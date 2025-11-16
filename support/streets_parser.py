import json
import yaml
import re

# Загрузка данных из JSON-файла
with open('data/raw_streets.json', 'r', encoding='ansi') as f:
    data = json.load(f)

# Извлечение названий улиц
street_names = [item['UM_NAMEF'] for item in data]

# Функция для получения базового названия без порядкового номера
def get_base_name(street_name):
    # Убираем порядковые номера типа "1-й", "2-я", "3-е" и т.д.
    pattern = r'^\d+-[йяе]\s+'
    base_name = re.sub(pattern, '', street_name)
    return base_name

# Используем set для автоматического удаления дубликатов
unique_base_names = set()
for street in street_names:
    base = get_base_name(street)
    unique_base_names.add(base)

# Преобразуем в отсортированный список
result = sorted(unique_base_names)

# Сохранение в YAML
with open('data/moscow_streets.yaml', 'w', encoding='utf-8') as f:
    yaml.dump(result, f, allow_unicode=True, sort_keys=False, default_flow_style=False)

print(f"✓ Обработано {len(street_names)} улиц")
print(f"✓ Уникальных базовых названий: {len(unique_base_names)}")
print(f"✓ Данные сохранены в moscow_streets.yaml")
