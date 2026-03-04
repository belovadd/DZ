import dash
from dash import dcc, html, dash_table, Input, Output
import pandas as pd
import requests
import plotly.express as px
import os

# 1. СЕТЕВЫЕ НАСТРОЙКИ
# Отключаем прокси для локальных адресов, чтобы избежать ошибки 502
os.environ['NO_PROXY'] = '127.0.0.1'

# 2. ПАРАМЕТРЫ ПОДКЛЮЧЕНИЯ
BASE_URL = "http://127.0.0.1:8080"
# API-токен
API_TOKEN = "rPENZslfEJKgGqPg_VFry4AbL8P2hMyBmgolXoLn"

# Словарь всех таблиц из базы NocoDB
TABLES = {
    "Книги": "myp7iugfdlrjzmr",
    "Пользователи": "mqgscggr2fwkc70",
    "Библиотеки": "mfn3zacjj7i9rrq",
    "Сообщения": "mv7tpodwfr5q04i",
    "Книжные клубы": "m3gdo93ofe696qh",
    "Рейтинги книг": "mwwnbvne3kvgw6k",
    "Обложки книг": "mkqpn7wp4dnj0jy",
    "Публикации": "m2nqqar2aajek7v",
    "Настройки таймеров": "m0nxjvdrn59q8w7",
    "Таймеры по умолчанию": "mz1c8m3yga76781",
    "Публикации клубов": "mnqq5ff5qdpjcw3"
}

app = dash.Dash(__name__)

# 3. ЛОГИКА ОБРАБОТКИ СЛОЖНЫХ ДАННЫХ
def normalize_value(x):
    """Превращает объекты и списки NocoDB в читаемый текст."""
    if x is None: return ""
    if isinstance(x, (str, int, float, bool)): return str(x)
    
    # Если это список (связи Many-to-Many)
    if isinstance(x, list):
        return ", ".join([str(i.get("name") or i.get("title") or i.get("Id") or i) 
                          if isinstance(i, dict) else str(i) for i in x])
    
    # Если это словарь (связь One-to-Many)
    if isinstance(x, dict):
        return str(x.get("name") or x.get("title") or x.get("Id") or x)
    
    return str(x)

def process_df(df):
    """Нормализует все колонки DataFrame."""
    df = df.copy()
    for col in df.columns:
        if df[col].apply(lambda v: isinstance(v, (dict, list))).any():
            df[col] = df[col].apply(normalize_value)
    return df

# 4. ВНЕШНИЙ ВИД (ИНТЕРФЕЙС)
app.layout = html.Div([
    html.H1("Dashboard проектов", 
            style={'textAlign': 'center', 'fontFamily': 'Arial', 'color': '#2c3e50', 'padding': '20px'}),
    
    html.Div([
        html.Label("Выберите таблицу для визуализации:", style={'fontWeight': 'bold'}),
        dcc.Dropdown(
            id='table-dropdown',
            options=[{'label': k, 'value': v} for k, v in TABLES.items()],
            value="myp7iugfdlrjzmr"  # По умолчанию открываем 'Книги'
        ),
    ], style={'width': '60%', 'margin': 'auto', 'marginBottom': '30px'}),

    html.Div([
        # Левая часть: График
        html.Div([
            dcc.Graph(id='data-graph')
        ], style={'width': '48%', 'display': 'inline-block'}),
        
        # Правая часть: Таблица
        html.Div([
            html.Div(id='table-container')
        ], style={'width': '48%', 'display': 'inline-block', 'verticalAlign': 'top'})
    ], style={'display': 'flex', 'justifyContent': 'space-around', 'padding': '20px'})
])

# 5. ВЗАИМОДЕЙСТВИЕ (CALLBACK)
@app.callback(
    [Output('table-container', 'children'), Output('data-graph', 'figure')],
    Input('table-dropdown', 'value')
)
def update_dashboard(selected_table_id):
    url = f"{BASE_URL}/api/v2/tables/{selected_table_id}/records"
    headers = {"xc-token": API_TOKEN}
    
    try:
        # Запрос к NocoDB с таймаутом 5 секунд
        response = requests.get(url, headers=headers, params={"limit": 100}, timeout=5)
        
        if response.status_code != 200:
            fig = px.scatter(title=f"Ошибка сервера: {response.status_code}")
            return html.Div(f"Ошибка доступа. Проверьте VPN и токен!"), fig
            
        data = response.json().get('list', [])
        if not data:
            return html.Div("В этой таблице нет записей."), px.scatter(title="Пустая таблица")
            
        # Загрузка и нормализация данных
        df = pd.DataFrame(data)
        clean_df = process_df(df)

        # Выбор колонки для графика (вторая после Id)
        x_col = clean_df.columns[1] if len(clean_df.columns) > 1 else clean_df.columns[0]
        
        # Построение гистограммы в зеленом цвете
        fig = px.histogram(clean_df.head(30), x=x_col, 
                           title=f"Распределение по: {x_col}",
                           template="plotly_white", 
                           color_discrete_sequence=['#58bd7d'])

        # Создание таблицы данных
        table = html.Div([
            html.H3(f"Записей в таблице: {len(clean_df)}"),
            dash_table.DataTable(
                data=clean_df.to_dict('records'),
                columns=[{"name": i, "id": i} for i in clean_df.columns[:5]], 
                page_size=10,
                style_table={'overflowX': 'auto'},
                style_cell={'textAlign': 'left', 'padding': '10px', 'fontFamily': 'Arial'},
                style_header={'backgroundColor': '#f2f2f2', 'fontWeight': 'bold'}
            )
        ])
        
        return table, fig

    except Exception as e:
        return html.Div(f"Критическая ошибка: {str(e)}"), px.scatter(title="Ошибка загрузки")

if __name__ == '__main__':
    # Запуск на порту 8050
    app.run(debug=True, port=8050)