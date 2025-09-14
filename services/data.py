SERVICES = [
    {
        "id": 1,
        "name": "Июнь",
        "main_value": "Дней в месяце: 31 дней\nСолнечная радиация: 550 МДж/м²",
        "image_key": "June_Apple.jpeg",
        "description": "Тёплый месяц с высокой солнечной активностью. Подходит для активного роста плодовых культур.",
        "stats": {
            "temperature": "+5...+7°C (днём), 0...+3°C (ночью)",
            "precipitation": "50-60 мм",
        },
    },
    {
        "id": 2,
        "name": "Июль",
        "main_value": "Дней в месяце: 31 дней\nСолнечная радиация: 630 МДж/м²",
        "image_key": "Jule_Apple.jpeg",
        "description": "Самый тёплый период сезона. Требуется контроль за поливом и состоянием почвы.",
        "stats": {
            "temperature": "+5...+7°C (днём), 0...+3°C (ночью)",
            "precipitation": "50-60 мм",
        },
    },
    {
        "id": 3,
        "name": "Август",
        "main_value": "Дней в месяце: 31 дней\nСолнечная радиация: 550 МДж/м²",
        "image_key": "August_Apple.jpeg",
        "description": "Период созревания. Важно отслеживать погодные риски и поддерживать агротехнику.",
        "stats": {
            "temperature": "+5...+7°C (днём), 0...+3°C (ночью)",
            "precipitation": "50-60 мм",
        },
    },
    {
        "id": 4,
        "name": "Сентябрь",
        "main_value": "Дней в месяце: 30 дней\nСолнечная радиация: 430 МДж/м²",
        "image_key": "September_Apple.jpeg",
        "description": "Начало сбора урожая. Температуры ниже, осадки участятся.",
        "stats": {
            "temperature": "+5...+7°C (днём), 0...+3°C (ночью)",
            "precipitation": "50-60 мм",
        },
    },
    {
        "id": 5,
        "name": "Октябрь",
        "main_value": "Дней в месяце: 31 дней\nСолнечная радиация: 300 МДж/м²",
        "image_key": "October_Apple.jpeg",
        "description": "Похолодание и снижение солнечной активности. Подготовка садов к зиме.",
        "stats": {
            "temperature": "+5...+7°C (днём), 0...+3°C (ночью)",
            "precipitation": "50-60 мм",
        },
    },
    {
        "id": 6,
        "name": "Ноябрь",
        "main_value": "Дней в месяце: 30 дней\nСолнечная радиация: 150 МДж/м²",
        "image_key": "November_Apple.jpeg",
        "description": "Поздняя осень. Низкие температуры, короткий световой день.",
        "stats": {
            "temperature": "+5...+7°C (днём), 0...+3°C (ночью)",
            "precipitation": "50-60 мм",
        },
    },
]

APPLICATIONS = {
    1: {
        "id": 1,
        "result": "42.0",
        "location_person": "Московская обл., Петров В. П.",
        "items": [
            {
                "service_id": 2,
                "quantity": 1,
                "order": 1,
                "primary": True,
                "comment": "Погибло несколько деревьев",
                "other": "—",
                "sum_precipitation": "100 мм",
                "avg_temp": "18°C",
            },
            {
                "service_id": 5,
                "quantity": 3,
                "order": 2,
                "primary": False,
                "comment": "Урожая меньше нормы",
                "other": "калибровка требуется",
                "sum_precipitation": "40 мм",
                "avg_temp": "24°C",
            },
        ],
    }
}