# Шаблоны документов

В этой директории должны находиться шаблоны DOCX для генерации PDF документов.

## Требования к шаблонам

1. Имя файла: `template.docx`
2. Формат: Microsoft Word Document (*.docx)
3. Кодировка: UTF-8
4. Максимальный размер: 10MB

## Переменные шаблона

Шаблон должен содержать следующие переменные:

### Основные данные
- `applicant_info` - информация о заявителе
- `applicant_name` - имя заявителя
- `applicant_agent` - представитель заявителя
- `is_organization` - флаг организации
- `creationDate` - дата создания
- `registry_pages` - количество страниц реестра

### Данные таблицы
- `table_rows` - массив строк таблицы со следующими полями:
  - `index` - номер строки
  - `invNumber` - инвентарный номер
  - `name` - название документа
  - `informationDate` - дата информации
  - `id` - идентификатор
  - `note` - примечание

## Безопасность

⚠️ ВНИМАНИЕ: Не включайте в репозиторий реальные шаблоны с конфиденциальной информацией!

## Пример структуры шаблона

```
Заявитель: {applicant_info}
Дата: {creationDate}

Таблица документов:
№ п/п | Инв. номер | Название | Дата | ID | Примечание
-------|------------|----------|------|----|-----------
{%- for row in table_rows %}
{{row.index}} | {{row.invNumber}} | {{row.name}} | {{row.informationDate}} | {{row.id}} | {{row.note}}
{%- endfor %}

Количество страниц реестра: {registry_pages}
``` 