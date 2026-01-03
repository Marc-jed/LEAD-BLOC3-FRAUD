from fastapi import FastAPI, HTTPException
from fastapi import BackgroundTasks
from pydantic import BaseModel
from typing import Literal
import pandas as pd
import boto3
import joblib
import os
import io

# === Initialisation FastAPI ===
app = FastAPI(
    title="Fraude Détection API",
    description="""
### 🎯 Description  
Cette API permet de détecter automatiquement les transactions potentiellement frauduleuses en se basant sur un modèle de machine learning entraîné avec des données historiques de paiements.

Elle reçoit en entrée les caractéristiques complètes d’une transaction bancaire (hors identifiants techniques comme Unnamed: 0 et trans_num), puis renvoie une prédiction :

1 → transaction frauduleuse

0 → transaction légitime

Le modèle est chargé dynamiquement depuis le registre de modèles MLflow (ou S3), garantissant une traçabilité complète et une mise à jour continue.

🧾 Champs d’entrée attendus (JSON)
Champ	Type	Description
cc_num	float	Numéro de carte anonymisé
merchant	string	Nom du commerçant ou de l’établissement
category	string	Catégorie du commerçant (ex : "gas_transport", "shopping_net", "travel")
amt	float	Montant de la transaction
first	string	Prénom du client
last	string	Nom du client
gender	string	Sexe du client ("M" ou "F")
street	string	Adresse postale du client
city	string	Ville du client
state	string	Code État ou Région (ex : "TX", "CA")
zip	int	Code postal
lat	float	Latitude du domicile
long	float	Longitude du domicile
city_pop	int	Population de la ville
job	string	Profession du client
merch_lat	float	Latitude du commerçant
merch_long	float	Longitude du commerçant
year    int	Année de la transaction
month   int	Mois de la transaction
day     int	Jour de la transaction
hour    int	Heure de la transaction
minute  int	Minute de la transaction
second  int	Seconde de la transaction
dob_year : int année de naissance
dob_month : int mois de naissance
dob_day : int jour de naissance
""",
version="1.0"
)

# Schéma attendu pour l'entrée
class InputData(BaseModel):
    cc_num: int
    merchant: str
    category: str
    amt: float
    first: str
    last: str
    gender: Literal["M", "F"]
    street: str
    city: str
    state: str
    zip: int
    lat: float
    long: float
    city_pop: int
    job: str
    merch_lat: float
    merch_long: float
    year : int         
    month : int
    day : int
    hour : int         
    minute : int       
    second : int
    dob_year : int
    dob_month : int
    dob_day : int   


S3_BUCKET = os.getenv("S3_BUCKET")
S3_PREFIX = "mlflow/models/"
s3 = boto3.client("s3")

def get_latest_model_key():
    try:
        response = s3.list_objects_v2(
            Bucket=S3_BUCKET,
            Prefix=S3_PREFIX
        )

        if "Contents" not in response:
            raise ValueError("Aucun modèle trouvé dans le bucket S3.")

        # Filtrer uniquement les .joblib
        models = [
            obj for obj in response["Contents"]
            if obj["Key"].endswith(".joblib")
        ]

        if not models:
            raise ValueError("Aucun fichier .joblib trouvé.")

        # Trier par LastModified (date d'upload dans S3)
        models.sort(key=lambda x: x["LastModified"], reverse=True)

        latest_key = models[0]["Key"]
        print(f"Dernier modèle détecté : {latest_key}")
        return latest_key

    except Exception as e:
        raise RuntimeError(f"Erreur récupération modèle S3 : {e}")

def load_latest_model():
    global model
    latest_model_key = get_latest_model_key()
    print(f"Rechargement du modèle : {latest_model_key}")

    response = s3.get_object(Bucket=S3_BUCKET, Key=latest_model_key)
    model_bytes = io.BytesIO(response["Body"].read())

    model = joblib.load(model_bytes)
    print("Nouveau modèle chargé avec succès")
    return latest_model_key

@app.on_event("startup")
def load_model():
    global model
    try:
        latest_model_key = get_latest_model_key()
        print(f"Téléchargement du dernier modèle depuis s3://{S3_BUCKET}/{latest_model_key}")
        response = s3.get_object(Bucket=S3_BUCKET, Key=latest_model_key)
        model_bytes = io.BytesIO(response["Body"].read())
        model = joblib.load(model_bytes)
        print("Modèle chargé avec succès")
    except Exception as e:
        print(f"Erreur chargement modèle : {e}")
        raise RuntimeError(f"Impossible de charger le modèle : {e}")


@app.get("/")
def home():
    return {"message": "Bienvenue sur l'API Fraude détéction - Utilisez /predict pour faire une prédiction"}


@app.post("/predict")
def predict(data: InputData):
    try:
        
        df = pd.DataFrame([data.dict()])
        print("Données reçues :", df.head(1).to_dict())
        
        prediction = model.predict(df)
        is_fraud = int(prediction[0])

        return {"is_fraud": is_fraud}

    except Exception as e:
        print(f"Erreur prédiction : {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/reload-model")
def reload_model(background_tasks: BackgroundTasks):
    """
    Recharge le dernier modèle S3 sans redémarrer l'API.
    """
    background_tasks.add_task(load_latest_model)
    latest_key = get_latest_model_key()
    return {"status - Rechargement en arrière-plan modèle :", latest_key}  
