from fastapi import FastAPI
from retrain import run_retraining
import requests

app = FastAPI()

@app.post("/retrain")
def retrain():
    result = run_retraining()
    requests.post("https://gdleds-api-fraud.hf.space/reload-model", timeout=120)
    return result

@app.get("/")
def home():
    return {"message" : "Bienvenue sur l'API de retrain du modèle XGBoost pour la prédiction de fraude de transaction"}