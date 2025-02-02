import requests
import json

# URL сервиса
# url = "http://127.0.0.1:8005/generate-pdf"
url = "http://172.27.239.23:31005/generate-pdf"

# JSON данные
data = {
    "operation": "CREATE",
    "id": "39-24",
    "email": "LKaracheva@rfgf.ru",
    "phone": "89",
    "applicantType": "ORGANIZATION",
    "organizationInfo": {
        "name": "ФЕДЕРАЛЬНОЕ ГОСУДАРСТВЕННОЕ БЮДЖЕТНОЕ УЧРЕЖДЕНИЕ \"РОССИЙСКИЙ ФЕДЕРАЛЬНЫЙ ГЕОЛОГИЧЕСКИЙ ФОНД\"",
        "agent": "Карачева Лидия Сергеевна",
        "address": "Г.Москва, УЛ. 3-Я МАГИСТРАЛЬНАЯ"
    },
    "registryItems": [
        {
            "id": "54539931",
            "invNumber": "2505",
            "name": "Скважина №: 2505, 1959 (актуализирована: 01.01.1974), от центр села Зюзя, около конторы, Зюзинский маслозавод",
            "informationDate": None,
            "note": None
        },
        {
            "id": "54668748",
            "note": "Документ недоступен"
        },
        {
            "id": "54000000",
            "note": "Документ недоступен"
        },
        {
            "id": "54668749",
            "note": "Документ недоступен"
        },
        {
            "id": "54000005",
            "note": "Документ недоступен"
        },
        {
            "id": "54668748",
            "note": "Документ недоступен"
        },
        {
            "id": "54000000",
            "note": "Документ недоступен"
        },
        {
            "id": "54668749",
            "note": "Документ недоступен"
        },
        {
            "id": "54000005",
            "note": "Документ недоступен"
        },
        {
            "id": "54668748",
            "note": "Документ недоступен"
        },
        {
            "id": "54000000",
            "note": "Документ недоступен"
        },
        {
            "id": "54668749",
            "note": "Документ недоступен"
        },
        {
            "id": "54000005",
            "note": "Документ недоступен"
        },
        {
            "id": "54668748",
            "note": "Документ недоступен"
        },
        {
            "id": "54000000",
            "note": "Документ недоступен"
        },
        {
            "id": "54668749",
            "note": "Документ недоступен"
        },
        {
            "id": "54001111",
            "note": "Документ недоступен"
        }
    ],
    "creationDate": "2024-12-17T08:33:04.715969591Z",
    "geoInfoStorageOrganization": {
        "code": "21315",
        "value": "Ямало-Ненецкий филиал ФБУ \"ТФГИ по УрФО\"",
        "links": []
    },
    "purposeOfGeoInfoAccessDictionary": {
        "code": "1",
        "value": "Пользование недрами",
        "links": []
    },
    "numpages": 2
}

try:
    # Отправляем запрос
    print(f"Отправляем запрос на {url}")
    print(f"Данные для отправки: {json.dumps(data, indent=2, ensure_ascii=False)}")
    
    # Изменяем формат отправки данных
    response = requests.post(
        url,
        params={'data': json.dumps(data)}  # Используем params вместо data
    )

    # Проверяем статус ответа
    print(f"Получен ответ со статусом: {response.status_code}")
    print(f"Заголовки ответа: {dict(response.headers)}")
    
    if response.status_code == 200:
        # Сохраняем PDF
        with open('result.pdf', 'wb') as f:
            f.write(response.content)
        print("PDF успешно создан и сохранен как 'result.pdf'")
    else:
        print(f"Ошибка: {response.status_code}")
        print(f"Текст ошибки: {response.text}")
        try:
            error_json = response.json()
            print(f"Детали ошибки: {json.dumps(error_json, indent=2, ensure_ascii=False)}")
        except:
            print(f"Тело ответа: {response.content}")

except Exception as e:
    print(f"Произошла ошибка: {str(e)}")
    import traceback
    print("Traceback:")
    print(traceback.format_exc())
