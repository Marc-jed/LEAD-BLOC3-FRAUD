import pandas as pd
import mlflow
import joblib
import io
import boto3
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.metrics import f1_score, recall_score, precision_score
from xgboost import XGBClassifier
import psycopg2
from sqlalchemy import create_engine
import os

def run_retraining():
    db_user = os.getenv("DB_USER")
    db_password = os.getenv("DB_PASS")
    db_host = os.getenv("DB_HOST")
    db_name = os.getenv("DB_NAME")
    engine = create_engine(f"postgresql+psycopg2://{db_user}:{db_password}@{db_host}/{db_name}")
    df = pd.read_sql("SELECT * FROM fraud_transaction", engine)
    df=pd.DataFrame(df)
    X=df.drop(columns=["is_fraud", "is_fraud_pred", "timestamp","id", "inserted_at"])
    y=df["is_fraud"]
    X_train, X_test, y_train,y_test=train_test_split(X,y, test_size=0.2, random_state=42, stratify=y)
    numeric_features = X.select_dtypes(include=['int64', 'float64', "int32"]).columns
    categoric_features = X.select_dtypes(include=['object']).columns
    numeric_transformer = StandardScaler()
    categorical_transformer = OneHotEncoder()
    preprocessor = ColumnTransformer(
        transformers=[
            ('num', numeric_transformer, numeric_features),
            ('cat', categorical_transformer, categoric_features)])
    xgb = XGBClassifier(n_estimators=1200,max_depth=10, learning_rate=0.2, random_state=42)
    xgb_final = Pipeline(steps=[
      ('preprocessor', preprocessor),
      ('xgboost_best', xgb)
    ])
    mlflow.set_tracking_uri("https://gdleds-mlflow-fraud.hf.space")
    mlflow.set_experiment("fraud_detection")

    with mlflow.start_run() as run:
        xgb_final.fit(X_train, y_train)
        y_pred = xgb_final.predict(X_test)

        f1 = f1_score(y_test, y_pred)

        mlflow.log_metric("F1", f1)
        mlflow.log_metric("precision", precision_score(y_test, y_pred))
        mlflow.log_metric("recall", recall_score(y_test, y_pred))

        # Sauvegarde modèle dans S3
        s3 = boto3.client("s3")
        bucket = os.getenv("S3_BUCKET")
        key = f"mlflow/models/xgboost_model_{run.info.run_id}.joblib"

        buffer = io.BytesIO()
        joblib.dump(xgb_final, buffer)

        s3.put_object(
            Bucket=bucket,
            Key=key,
            Body=buffer.getvalue()
        )

    return {
        "status": "success",
        "run_id": run.info.run_id,
        "f1_score": f1,
        "model_path": key
    }
