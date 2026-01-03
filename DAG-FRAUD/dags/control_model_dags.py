import logging
import json
import requests
import pandas as pd
import io
import os
import plotly.express as px
from datetime import datetime
from sqlalchemy import create_engine
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.hooks.S3_hook import S3Hook
from airflow.hooks.base import BaseHook
from airflow.models import Variable
from airflow.operators.email import EmailOperator
from airflow.operators.python import BranchPythonOperator
from airflow.operators.empty import EmptyOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import confusion_matrix, classification_report, roc_auc_score, f1_score, recall_score, precision_score
defaults_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "retries": 2
    }

def fetch_transaction_data(ti, **kwargs):
    hook=PostgresHook(postgres_conn_id="neon_default")
    engine = hook.get_sqlalchemy_engine()
    query = f"""
    SELECT *
    FROM fraud_transaction
    WHERE year = 2025
    """
    df = pd.read_sql(query, engine)
    path="/tmp/transactions.csv"
    df.to_csv(path,index=False)
    ti.xcom_push(key="transaction_path", value=path)
    logging.info("données chargées")

def analyse_model_data(ti, **kwargs):
    path=ti.xcom_pull(key="transaction_path", task_ids="fetch_transaction_data")
    df=pd.read_csv(path)
    y_pred=df["is_fraud_pred"]
    y_true=df["is_fraud"]
    score_f1=f1_score(y_true,y_pred)
    cm=confusion_matrix(y_true,y_pred)
 
    if score_f1 < 0.80:
        print(f"Attention le model perd en performance {score_f1.round(2)}")

    logging.info(f"Matrice de confusion : {cm}")
    logging.info(f"nous avons un f1_score de: {score_f1.round(2)}")
    ti.xcom_push(key="f1_score", value=score_f1)
    report_text = f"""
    <h3>Rapport d'analyse F1_score</h3>
    <p>Dernier résultat du f1_score <b>{score_f1.round(2)}</b></p>
    <p>Résulat inférieur à 0.8, le model est réentrainé</p>
    """
    ti.xcom_push(key="text", value=report_text)

def check_model(ti,**kwargs):
    score_f1=ti.xcom_pull(key="f1_score", task_ids="analyse_model_data")
    if score_f1 <0.8:
        return ["call_retrain_api","sendemail_check_model"]
    return "end"

def call_retrain_api():
    url = "https://gdleds-retrain.hf.space/retrain"
    resp = requests.post(url, timeout=900)

    if resp.status_code != 200:
        raise ValueError(f"Erreur API retrain : {resp.status_code} | {resp.text}")

    logging.info("Réentraînement lancé avec succès")

with DAG(
    dag_id="check_model_dag",
    default_args=defaults_args,
    description="DAG for reporting daily BI",
    schedule_interval="@daily",
    start_date=datetime(2023, 1, 1),
    catchup=False,

) as dag:
    fetch_transaction_data_task = PythonOperator(
        task_id="fetch_transaction_data",
        python_callable=fetch_transaction_data
    )
    analyse_model_data_task=PythonOperator(
        task_id="analyse_model_data",
        python_callable= analyse_model_data
    )
    branch_check_model=BranchPythonOperator(
        task_id="check_model",
        python_callable=check_model
    )
    fetch_call_retrain_api=PythonOperator(
        task_id="call_retrain_api",
        python_callable=call_retrain_api
    )
    sendemail_check_model = EmailOperator(
        task_id="sendemail_check_model",
        to="gdleds31@gmail.com",
        subject="Analyse F1_score du model",
        html_content= "{{ti.xcom_pull(key='text', task_ids='analyse_model_data')}}"
    )
    fetch_transaction_data_task >> analyse_model_data_task >> branch_check_model 
    branch_check_model >> [fetch_call_retrain_api, sendemail_check_model]
