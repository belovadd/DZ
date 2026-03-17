import dash
from dash import dcc, html, dash_table, Input, Output
import pandas as pd
import requests
import plotly.express as px
import os

# ==========================================
# 1. НАСТРОЙКИ И ПОДКЛЮЧЕНИЕ
# ==========================================
os.environ['NO_PROXY'] = '127.0.0.1'
BASE_URL = "http://127.0.0.1:8080"
API_TOKEN = "rPENZslfEJKgGqPg_VFry4AbL8P2hMyBmgolXoLn"

# Итоговый список таблиц
TABLES = {
    "Статусы книг": "mwwnbvne3kvgw6k",
    "Распределение по жанру": "myp7iugfdlrjzmr",
    "Участники книжных клубов": "m3gdo93ofe696qh",
    "Популярное время чтения": "m0nxjvdrn59q8w7",
    "Библиотеки": "mfn3zacjj7i9rrq"
}

app = dash.Dash(__name__)

# ==========================================
# 2. ЛОГИКА ОБРАБОТКИ (УМНАЯ НОРМАЛИЗАЦИЯ)
# ==========================================
def smart_normalize(v):
    if v is None or (isinstance(v, float) and pd.isna(v)): 
        return 0
    if isinstance(v, list):
        return len(v)
    if isinstance(v, dict):
        return v.get("name") or v.get("title") or v.get("Id") or 1
    return str(v)

def prepare_df(df):
    if df.empty: return df
    hide = ("nc_", "CreatedAt", "UpdatedAt", "Id")
    cols = [c for c in df.columns if not any(c.startswith(p) for p in hide)]
    df = df[cols].copy()
    return df.map(smart_normalize)

# ==========================================
# 3. ИНТЕРФЕЙС (LAYOUT)
# ==========================================
app.layout = html.Div([
    html.Div([
        html.H1("🌳 Ad Quercum: Аналитическая панель", 
                style={'color': '#2d4d1a', 'textAlign': 'center', 'fontFamily': 'Arial'}),
        html.P("Визуализация данных дипломного проекта", style={'textAlign': 'center', 'color': '#666'})
    ], style={'padding': '20px', 'backgroundColor': '#fff', 'borderBottom': '2px solid #e8eedf'}),

    html.Div([
        html.Div([
            html.Label("Выберите раздел анализа:", style={'fontWeight': 'bold', 'marginBottom': '10px', 'display': 'block'}),
            dcc.Dropdown(
                id='master-dropdown',
                options=[{'label': k, 'value': v} for k, v in TABLES.items()],
                value="mwwnbvne3kvgw6k",
                clearable=False
            ),
        ], style={'width': '50%', 'margin': '20px auto'}),

        html.Div([
            dcc.Graph(id='main-viz', style={'height': '550px'}),
        ], style={'backgroundColor': '#fff', 'padding': '20px', 'borderRadius': '12px', 'boxShadow': '0 4px 15px rgba(0,0,0,0.05)'}),

        html.Div([
            html.H4("Детальная таблица данных", style={'marginTop': '40px', 'color': '#2d4d1a'}),
            dash_table.DataTable(
                id='main-table',
                page_size=10,
                sort_action="native",
                filter_action="none",
                style_table={'overflowX': 'auto', 'borderRadius': '8px'},
                style_header={'backgroundColor': '#f2f5f0', 'fontWeight': 'bold', 'color': '#2d4d1a'},
                style_cell={'textAlign': 'left', 'padding': '12px', 'fontFamily': 'Arial', 'fontSize': '13px'}
            )
        ])
    ], style={'maxWidth': '1100px', 'margin': '0 auto', 'padding': '20px'})
], style={'backgroundColor': '#fcfdfa', 'minHeight': '100vh'})

# ==========================================
# 4. CALLBACK (ОБЪЕДИНЕННАЯ АНАЛИТИКА)
# ==========================================
@app.callback(
    [Output('main-viz', 'figure'), Output('main-table', 'data'), Output('main-table', 'columns')],
    Input('master-dropdown', 'value')
)
def update_analytics(table_id):
    headers = {"xc-token": API_TOKEN}
    try:
        res = requests.get(f"{BASE_URL}/api/v2/tables/{table_id}/records", headers=headers, params={"limit": 500}, timeout=10)
        data = res.json().get('list', [])
        
        if not data:
            return px.bar(title="Данные в таблице отсутствуют"), [], []

        df = prepare_df(pd.DataFrame(data))
        cols_low = {c.lower().strip(): c for c in df.columns}
        
        oak_palette = ['#5e813f', '#8cae68', '#c2b078', '#a0522d', '#d4be8d']
        fig = None

        if table_id == "mwwnbvne3kvgw6k":
            col = cols_low.get('status') or cols_low.get('статус')
            if col and col in df.columns:
                counts = df[col].value_counts().reset_index()
                counts.columns = [col, 'Количество']
                fig = px.bar(counts, x=col, y='Количество', color=col,
                             color_discrete_sequence=oak_palette, title="Статусы чтения пользователей")
            else:
                fig = px.bar(title="Колонка 'Статус' не найдена")

        elif table_id == "myp7iugfdlrjzmr":
            col = cols_low.get('genre') or cols_low.get('жанр')
            if col and col in df.columns:
                counts = df[col].value_counts().reset_index()
                counts.columns = ['Жанр', 'Книг']
                fig = px.bar(counts.sort_values('Книг', ascending=False), x='Жанр', y='Книг', 
                             color='Жанр', color_discrete_sequence=oak_palette, title="Популярность жанров")
            else:
                fig = px.bar(title="Колонка 'Жанр' не найдена")

        elif table_id == "m3gdo93ofe696qh":
            name_col = cols_low.get('name') or cols_low.get('title') or cols_low.get('клуб') or df.columns[0]
            member_col = cols_low.get('members') or cols_low.get('участники') or cols_low.get('users')
            
            if member_col and member_col in df.columns:
                df_sorted = df.sort_values(by=member_col, ascending=False).head(15)
                fig = px.bar(df_sorted, x=name_col, y=member_col,
                             color=name_col, color_discrete_sequence=oak_palette,
                             title="Количество участников в книжных клубах")
                fig.update_layout(xaxis_title="Название клуба", yaxis_title="Количество участников")
                fig.update_yaxes(dtick=1)
                fig.update_traces(hovertemplate="Клуб: %{x}<br>Участников: %{y}<extra></extra>")
            else:
                fig = px.bar(title="Колонка с участниками не найдена")

        # --- ИСПРАВЛЕННЫЙ КЕЙС 4: ТАЙМЕРЫ ---
        elif table_id == "m0nxjvdrn59q8w7":
            col = cols_low.get('setting') or cols_low.get('time') or cols_low.get('время') or cols_low.get('duration')
            
            if col and col in df.columns:
                # ВЫТАСКИВАЕМ ТОЛЬКО ВРЕМЯ (ЧЧ:ММ) И ДОБАВЛЯЕМ ТЕКСТ (Эмодзи)
                # Это гарантирует, что Plotly не превратит это в 1999 год
                clean_time = df[col].astype(str).str.extract(r'(\d{2}:\d{2})')[0]
                # Если регулярка не нашла формат 00:00, оставляем старое значение, иначе добавляем значок
                df[col] = "⏳ " + clean_time.fillna(df[col].astype(str))

                counts = df[col].value_counts().reset_index()
                counts.columns = ['Выбранное время', 'Количество пользователей']
                
                fig = px.bar(counts.sort_values('Количество пользователей', ascending=False), 
                             x='Выбранное время', y='Количество пользователей',
                             color='Выбранное время', color_discrete_sequence=oak_palette,
                             title="Популярность настроек времени чтения")
                
                fig.update_layout(xaxis_title="Настройка таймера", yaxis_title="Сколько раз выбрали")
                fig.update_yaxes(dtick=1) 
                fig.update_xaxes(type='category')
            else:
                fig = px.bar(title="Колонка со временем ('setting' или 'time') не найдена. Проверьте названия.")

        elif table_id == "mfn3zacjj7i9rrq":
            lib_name_col = cols_low.get('library') or cols_low.get('библиотека') or cols_low.get('name') or df.columns[0]
            
            if lib_name_col and lib_name_col in df.columns:
                counts = df[lib_name_col].value_counts().reset_index()
                counts.columns = ['Название библиотеки', 'Количество книг']
                
                fig = px.bar(counts, x='Название библиотеки', y='Количество книг',
                             color='Название библиотеки', color_discrete_sequence=oak_palette,
                             title="Количество книг в библиотеках")
                
                fig.update_layout(xaxis_title="Название библиотеки", yaxis_title="Количество книг")
                fig.update_yaxes(dtick=1)
                fig.update_traces(hovertemplate="Библиотека: %{x}<br>Книг: %{y}<extra></extra>")
            else:
                fig = px.bar(title="Колонка с названием библиотеки не найдена")
                
        else:
            fig = px.bar(title="График для этой таблицы не настроен")

        # Общие настройки оформления
        if fig is not None:
            fig.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(family="Arial", size=12),
                showlegend=False
            )
            fig.update_yaxes(gridcolor='#eee')

        table_cols = [{"name": i, "id": i} for i in df.columns[:6]]
        return fig, df.to_dict('records'), table_cols

    except Exception as e:
        return px.bar(title=f"Ошибка: {e}"), [], []

# ==========================================
# 5. ЗАПУСК
# ==========================================
if __name__ == '__main__':
    print("--- Аналитическая панель Ad Quercum готова к работе ---")
    app.run(debug=True, port=8055, host='127.0.0.1')
