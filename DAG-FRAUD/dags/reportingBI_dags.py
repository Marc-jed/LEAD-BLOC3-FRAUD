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
defaults_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "retries": 2
    }

def fetch_transaction_data(ti, **kwargs):
    hook=PostgresHook(postgres_conn_id="neon_default")
    engine = hook.get_sqlalchemy_engine()
    yesterday = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=1)
    query = f"""
    SELECT *
    FROM fraud_transaction
    WHERE DATE(timestamp) = '{yesterday}'
    ORDER BY timestamp ASC;
    """
    df_yesterday = pd.read_sql(query, engine)
    path="/tmp/transactions_yesterday.csv"
    df_yesterday.to_csv(path,index=False)
    ti.xcom_push(key="transaction_yesterday_csv_path", value=path)
    logging.info(f"Fetched {len(df_yesterday)} transactions from {yesterday}")

def analyse_transaction_data(ti, **kwargs):
    path=ti.xcom_pull(key="transaction_yesterday_csv_path", task_ids="fetch_transaction_data")
    df=pd.read_csv(path)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    transactions_date = df["timestamp"].dt.date.unique()[0]
    total_transactions = len(df)
    total_amount = df['amt'].sum()
    fraud_count = df[df["is_fraud_pred"] ==1].shape[0]
    fraud_rate = fraud_count / total_transactions
    # enregistrement des valeurs pour airtable
    ti.xcom_push(key="transactions_date", value=str(transactions_date))
    ti.xcom_push(key="total_transactions", value=int(total_transactions))
    ti.xcom_push(key="total_amount", value=float(total_amount))
    ti.xcom_push(key="fraud_count", value=int(fraud_count))
    ti.xcom_push(key="fraud_rate", value=float(fraud_rate))
    # creation de contenu pour le mail quotidien
    mapping={0:"no_fraud", 1:"fraud"}
    df["fraud_label"]= df["is_fraud_pred"].map(mapping)
    fig = px.pie(df, names="fraud_label", title="Répartition fraud / no_fraud")
    fig.write_image("/tmp/resultat_veille.png")
    fig2=px.box(df, y="amt", points="all", title="Répartition des montants de la veille")
    fig2.update_layout(
        yaxis_title='montant des transactions ($)')
    fig2.write_image("/tmp/répartition_montant_transaction_journalier.png")
    fig3=px.bar(df, y='amt', x='category', color='category', title="Montant total par catégorie")
    fig3.update_layout(
        yaxis_title='montant des transactions ($)')
    fig3.write_image("/tmp/transaction_par_categorie.png")
    fig4=px.histogram(df, x='category', title="Nombre de transaction par categorie")
    fig4.write_image("/tmp/nombre_de_transaction_par_categorie.png")
    report_text = f"""
    <h3>Rapport quotidien des transactions</h3>
    <p>Nombre de transactions : <b>{total_transactions}</b></p>
    <p>Montant total : <b>{total_amount}$</b></p>
    <p>Les analyses sont en pièces jointes</p>
    """
    ti.xcom_push(key="text", value=report_text)

def push_summary_to_airtable(ti):
    base_id = Variable.get("AIRTABLE_BASE_ID")
    api_key = Variable.get("AIRTABLE_API_KEY")
    table_name = "daily_summary"

    url = f"https://api.airtable.com/v0/{base_id}/{table_name}"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    data = {
        "records": [{
            "fields": {
                "date": datetime.utcnow().strftime("%Y-%m-%d"),
                "transactions_date": ti.xcom_pull(key="transactions_date"),
                "total_transactions": ti.xcom_pull(key="total_transactions"),
                "total_amount": ti.xcom_pull(key="total_amount"),
                "fraud_count": ti.xcom_pull(key="fraud_count"),
                "fraud_rate": ti.xcom_pull(key="fraud_rate")
            }
        }]
    }
    print("Payload envoyé à Airtable:")
    print(data)
    resp = requests.post(url, headers=headers, json=data)
    print("Code HTTP:", resp.status_code)
    print("Réponse Airtable:", resp.text)

with DAG(
    dag_id="Analysis_dag",
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
    analyse_transaction_data_task=PythonOperator(
        task_id="analyse_transaction_data",
        python_callable= analyse_transaction_data
    )
    push_summary_to_airtable_task = PythonOperator(
        task_id="push_summary_to_airtable",
        python_callable=push_summary_to_airtable
    )
    sendemail_analyse = EmailOperator(
        task_id="Email_analyse",
        to="gdleds31@gmail.com",
        subject="Analyse fraude de la veille",
        html_content= "{{ti.xcom_pull(key='text', task_ids='analyse_transaction_data')}}",
        files= ["/tmp/resultat_veille.png","/tmp/répartition_montant_transaction_journalier.png","/tmp/transaction_par_categorie.png","/tmp/nombre_de_transaction_par_categorie.png"]
    )
    fetch_transaction_data_task >> analyse_transaction_data_task >> push_summary_to_airtable_task >> sendemail_analyse