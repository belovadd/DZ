from locust import HttpUser, task, between

class DashUser(HttpUser):
    wait_time = between(1, 2)
    
    @task
    def load_page(self):
        self.client.get("/")

    @task(2)
    def update_dropdown(self):
        # Имитируем запрос, который Dash шлет при выборе в меню
        self.client.post("/_dash-update-component", json={
            "output": "main-viz.figure, main-table.data, main-table.columns",
            "outputs": [
                {"id": "main-viz", "property": "figure"},
                {"id": "main-table", "property": "data"},
                {"id": "main-table", "property": "columns"}
            ],
            "inputs": [{"id": "master-dropdown", "property": "value", "value": "mwwnbvne3kvgw6k"}],
            "changedPropIds": ["master-dropdown.value"]
        })