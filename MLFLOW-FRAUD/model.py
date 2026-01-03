import mlflow
import pandas as pd
import os
import subprocess
import numpy as np
from dotenv import load_dotenv
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import f1_score, accuracy_score, precision_score, recall_score, roc_auc_score
from xgboost.sklearn import XGBClassifier
import boto3
import joblib
import io
load_dotenv(dotenv_path=".secrets")

mlflow.set_tracking_uri("https://gdleds-mlflow-fraud.hf.space")
os.environ["AWS_ACCESS_KEY_ID"] = os.getenv('AWS_ACCESS_KEY_ID')
os.environ["AWS_SECRET_ACCESS_KEY"] = os.getenv('AWS_SECRET_ACCESS_KEY')
os.environ["MLFLOW_DEFAULT_ARTIFACT_ROOT"] = os.getenv('MLFLOW_DEFAULT_ARTIFACT_ROOT')
os.environ["S3_BUCKET"] = os.getenv('S3_BUCKET')

# Log configurations au démarrage
print("=== Configuration MLflow ===")
print(f"Tracking URI: {mlflow.get_tracking_uri()}")
print(f"Artifact Store: {os.getenv('MLFLOW_DEFAULT_ARTIFACT_ROOT')}")
print(f"AWS Access: {'Configuré' if os.getenv('AWS_ACCESS_KEY_ID') else 'Manquant'}")

s3 = boto3.client('s3')
try:
   response = s3.list_objects_v2(Bucket=os.getenv('S3_BUCKET'))
   print("S3 contents:", response.get('Contents', []))
except Exception as e:
   print("S3 error:", e)

df=pd.read_csv("s3://fraud-detect-17/dataset/fraudTest.csv")

df["trans_date_trans_time"] = pd.to_datetime(df["trans_date_trans_time"], format="%Y-%m-%d %H:%M:%S")
df["year"]= df["trans_date_trans_time"].dt.year
df["month"]=df["trans_date_trans_time"].dt.month
df["day"]=df["trans_date_trans_time"].dt.day
df["hour"]=df["trans_date_trans_time"].dt.hour
df["minute"]=df["trans_date_trans_time"].dt.minute
df["second"]=df["trans_date_trans_time"].dt.second
df["dob"] = pd.to_datetime(df["dob"], format="%Y-%m-%d")
df["dob_year"] = df["dob"].dt.year
df["dob_month"] = df["dob"].dt.month
df["dob_day"] = df["dob"].dt.day

# Suppression des colonnes inutiles
df.drop(columns=["trans_date_trans_time", "Unnamed: 0", "trans_num","unix_time","dob"], inplace=True)

# Séparation des features et de la target
X = df.drop(columns=["is_fraud"])
y = df["is_fraud"]
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y) 

# Préparation du préprocesseur
numeric_features = X.select_dtypes(include=['int64', 'float64', "int32"]).columns
categoric_features = X.select_dtypes(include=['object']).columns
numeric_transformer = StandardScaler()
categorical_transformer = OneHotEncoder()
preprocessor = ColumnTransformer(
    transformers=[
        ('num', numeric_transformer, numeric_features),
        ('cat', categorical_transformer, categoric_features)])

# fonction d'entraînement et d'évaluation avec MLflow
def train_evaluate_model_with_mlflow(model, X_train, X_test, y_train, y_test, model_name):
   print(f"\n=== Démarrage entraînement {model_name} ===")
   print(f"Tracking URI: {mlflow.get_tracking_uri()}")
   print(f"Registry URI: {mlflow.get_registry_uri()}")
   
   mlflow.set_experiment("fraud_detection")
   print(f"Experiment: fraud_detection")
   s3 = boto3.client('s3')

   with mlflow.start_run() as run:
       print(f"Run ID: {run.info.run_id}")
       
       print("Entraînement du modèle...")
       model.fit(X_train, y_train)
       
       #save model to S3
       print("Enregistrement du modèle sur S3...")
       model_path = f"mlflow/models/{model_name}_{run.info.run_id}.joblib"
       buffer = io.BytesIO()
       joblib.dump(model, buffer)
       s3.put_object(
           Bucket=os.getenv('S3_BUCKET'),
           Key=model_path,
           Body=buffer.getvalue()
       )
       print("Modèle enregistré")
       
       y_pred = model.predict(X_test)
       metrics = {
           "F1score": f1_score(y_test, y_pred),
           "Recall": recall_score(y_test, y_pred),
           "Precision": precision_score(y_test, y_pred)
       }
       
       print("\nEnregistrement des métriques...")
       for name, value in metrics.items():
           mlflow.log_metric(name, value)
           print(f"{name}: {value:.2f}")
       
       return model, run.info.run_id

if __name__ == "__main__":
   xgb = XGBClassifier(n_estimators=1200,max_depth=10, learning_rate=0.2, random_state=42)
   xgb_final = Pipeline(steps=[
      ('preprocessor', preprocessor),
      ('xgboost_best', xgb)
    ])
   _, run_id = train_evaluate_model_with_mlflow(
      xgb_final, X_train, X_test, y_train, y_test, "xgboost_model"
   )
   print(f"Run ID: {run_id}")