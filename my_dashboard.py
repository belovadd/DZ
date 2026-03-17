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

TABLES = {
    "Статусы книг": "mwwnbvne3kvgw6k",
    "Распределение по жанру": "myp7iugfdlrjzmr",
    "Участники книжных клубов": "m3gdo93ofe696qh",
    "Популярное время чтения": "m0nxjvdrn59q8w7",
    "Библиотеки": "mfn3zacjj7i9rrq"
}

app = dash.Dash(__name__)
app.title = "Ad Quercum: Dashboard 🌳"

# ==========================================
# 2. ЛОГИКА ОБРАБОТКИ
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
        html.H1("Ad Quercum: Dashboard 🌳", 
                style={'color': '#2d4d1a', 'textAlign': 'center', 'fontFamily': 'Arial', 'margin': '0'})
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
                style_table={'overflowX': 'auto', 'borderRadius': '8px'},
                style_header={'backgroundColor': '#f2f5f0', 'fontWeight': 'bold', 'color': '#2d4d1a'},
                style_cell={'textAlign': 'left', 'padding': '12px', 'fontFamily': 'Arial', 'fontSize': '13px'}
            )
        ])
    ], style={'maxWidth': '1100px', 'margin': '0 auto', 'padding': '20px'})
], style={'backgroundColor': '#fcfdfa', 'minHeight': '100vh'})

# ==========================================
# 4. CALLBACK
# ==========================================
@app.callback(
    [Output('main-viz', 'figure'), Output('main-table', 'data'), Output('main-table', 'columns')],
    Input('master-dropdown', 'value')
)
def update_analytics(table_id):
    headers = {"xc-token": API_TOKEN}
    try:
        res = requests.get(f"{BASE_URL}/api/v2/tables/{table_id}/records", headers=headers, params={"limit": 500}, timeout=10)
        raw_data = res.json().get('list', [])
        
        if not raw_data:
            return px.bar(title="Данные в таблице отсутствуют"), [], []

        df = prepare_df(pd.DataFrame(raw_data))
        cols_low = {c.lower().strip(): c for c in df.columns}
        oak_palette = ['#5e813f', '#8cae68', '#c2b078', '#a0522d', '#d4be8d']
        fig = None

        # --- КЕЙС 1: СТАТУСЫ ---
        if table_id == "mwwnbvne3kvgw6k":
            col = cols_low.get('status') or cols_low.get('статус')
            if col and col in df.columns:
                counts = df[col].value_counts().reset_index()
                counts.columns = [col, 'Количество']
                fig = px.bar(counts, x=col, y='Количество', color=col, color_discrete_sequence=oak_palette, title="Статусы чтения пользователей")

        # --- КЕЙС 2: ЖАНРЫ ---
        elif table_id == "myp7iugfdlrjzmr":
            col = cols_low.get('genre') or cols_low.get('жанр')
            if col and col in df.columns:
                counts = df[col].value_counts().reset_index()
                counts.columns = ['Жанр', 'Книг']
                fig = px.bar(counts.sort_values('Книг', ascending=False), x='Жанр', y='Книг', color='Жанр', color_discrete_sequence=oak_palette, title="Популярность жанров")

        # --- КЕЙС 3: КЛУБЫ (ИСПРАВЛЕНО) ---
        elif table_id == "m3gdo93ofe696qh":
            name_col = cols_low.get('name') or cols_low.get('title') or cols_low.get('клуб') or df.columns[0]
            member_col = cols_low.get('members') or cols_low.get('участники') or cols_low.get('users')
            
            if member_col and member_col in df.columns:
                # Превращаем текст с именами в число (считаем запятые + 1, если строка не пуста)
                def count_members(val):
                    s = str(val).strip()
                    if not s or s == '0' or s == 'None': return 0
                    return len([name for name in s.replace(';', ',').split(',') if name.strip()])

                df['Количество участников'] = df[member_col].apply(count_members)
                df_sorted = df.sort_values(by='Количество участников', ascending=False).head(15)
                
                fig = px.bar(df_sorted, x=name_col, y='Количество участников',
                             color=name_col, color_discrete_sequence=oak_palette,
                             title="Количество участников в книжных клубах")
                fig.update_yaxes(dtick=1)
            else:
                fig = px.bar(title="Колонка с участниками не найдена")

        # --- КЕЙС 4: ТАЙМЕРЫ ---
        elif table_id == "m0nxjvdrn59q8w7":
            col = cols_low.get('setting') or cols_low.get('time') or cols_low.get('время')
            if col and col in df.columns:
                clean_time = df[col].astype(str).str.extract(r'(\d{2}:\d{2})')[0]
                df[col] = "⏳ " + clean_time.fillna(df[col].astype(str))
                counts = df[col].value_counts().reset_index()
                counts.columns = ['Выбранное время', 'Количество']
                fig = px.bar(counts, x='Выбранное время', y='Количество', color='Выбранное время', color_discrete_sequence=oak_palette, title="Популярность времени чтения")
                fig.update_yaxes(dtick=1)

        # --- КЕЙС 5: БИБЛИОТЕКИ ---
        elif table_id == "mfn3zacjj7i9rrq":
            lib_name_col = cols_low.get('library') or cols_low.get('библиотека') or cols_low.get('name') or df.columns[0]
            if lib_name_col in df.columns:
                counts = df[lib_name_col].value_counts().reset_index()
                counts.columns = ['Библиотека', 'Книг']
                fig = px.bar(counts, x='Библиотека', y='Книг', color='Библиотека', color_discrete_sequence=oak_palette, title="Книги в библиотеках")
                fig.update_yaxes(dtick=1)

        if fig:
            fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', showlegend=False)
            fig.update_yaxes(gridcolor='#eee')
        else:
            fig = px.bar(title="График не настроен")

        return fig, df.to_dict('records'), [{"name": i, "id": i} for i in df.columns[:8]]

    except Exception as e:
        return px.bar(title=f"Ошибка: {e}"), [], []

# ==========================================
# 5. ЗАПУСК
# ==========================================
if __name__ == '__main__':
    print("--- Аналитическая панель Ad Quercum готова к работе ---")
    app.run(debug=True, port=8055, host='127.0.0.1')
