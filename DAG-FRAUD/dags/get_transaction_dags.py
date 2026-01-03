import logging
import json
import requests
import pandas as pd
import io
import os
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
from airflow.hooks.postgres_hook import PostgresHook
default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "retries": 2,
}

def fetch_transaction_data(ti, **kwargs):
    response = requests.get("https://djohell-real-time-fraud-detection.hf.space/current-transactions")
    data = response.json()
    ti.xcom_push(key="raw_json", value=data)
    

def save_raw_jsonto_S3(ti, **kwargs):
    data=ti.xcom_pull(key="raw_json", task_ids="fetch_transaction_data")
    bucket = Variable.get("S3BucketName")
    s3 = S3Hook(aws_conn_id="aws_default")
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S%f")
    key=f"data_brute/transaction_{timestamp}.json"
    s3.load_string(
         string_data=json.dumps(data),
         key=key,
         bucket_name=bucket,
    )
    logging.info("Transaction JSON fetched and saved to S3")

def transform_data(ti):
    path = ti.xcom_pull(key="raw_json", task_ids="fetch_transaction_data")
    path = json.loads(path)
    df = pd.DataFrame(path["data"], columns=path["columns"])
    df["timestamp"] = pd.to_datetime(df["current_time"], unit="ms", utc=True)
    df["year"]= df["timestamp"].dt.year
    df["month"]=df["timestamp"].dt.month
    df["day"]=df["timestamp"].dt.day
    df["hour"]=df["timestamp"].dt.hour
    df["minute"]=df["timestamp"].dt.minute
    df["second"]=df["timestamp"].dt.second
    df["dob"] = pd.to_datetime(df["dob"], format="%Y-%m-%d")
    df["dob_year"] = df["dob"].dt.year
    df["dob_month"] = df["dob"].dt.month
    df["dob_day"] = df["dob"].dt.day
    df.drop(columns=["current_time", "trans_num","dob"], inplace=True)
    csv_path="/tmp/transactions.csv"
    df.to_csv(csv_path, index=False)
    ti.xcom_push(key="transaction_csv_path", value=csv_path)
    logging.info(" Transforming raw data to CSV format")

def fetch_api_prediction(ti, **kwargs):
    path = ti.xcom_pull(key="transaction_csv_path", task_ids="transform_data")
    df = pd.read_csv(path)
    api_url = Variable.get("APIFraudURL") + "/predict"
    payload = df.to_dict(orient="records")[0]
    response = requests.post(api_url, json=payload)
    prediction = response.json()
    logging.info(f"API Prediction: {prediction}")
    df["is_fraud_pred"] = prediction.get("is_fraud",None)
    csv_path="/tmp/transactions_with_predictions.csv"
    df.to_csv(csv_path, index=False)
    ti.xcom_push(key="is_fraud_pred", value=int(df["is_fraud_pred"].iloc[0]))
    ti.xcom_push(key="transaction_with_prediction_csv_path", value=csv_path)
    logging.info("Fetched predictions from API and saved to CSV")

def check_fraud(**kwargs):
    ti = kwargs['ti']
    is_fraud = ti.xcom_pull(key="is_fraud_pred", task_ids="fetch_api_prediction")
    if is_fraud == 1:
        return ["send_email_alert", "continue_pipeline"] 
    else:
        return ["continue_pipeline"]
    
def store_data_neon(ti, **kwargs):
    hook = PostgresHook(postgres_conn_id="neon_default")
    engine = hook.get_sqlalchemy_engine()
    path=ti.xcom_pull(key="transaction_with_prediction_csv_path", task_ids="fetch_api_prediction")
    new_data = pd.read_csv(path)
    new_data.to_sql("fraud_transaction", engine, if_exists="append", index=False)
    logging.info("Stored in Neon")

def cleanup_tmp_files(**kwargs):
    tmp_files = ["/tmp/transactions.json", "/tmp/transactions.csv"]
    for file_path in tmp_files:
        try:
            os.remove(file_path)
            logging.info(f"Removed temporary file: {file_path}")
        except OSError as e:
            logging.error(f"Error removing file {file_path}: {e}")

with DAG("Predict_dag",
        default_args=default_args,
        start_date=datetime(2022, 1, 1),
        schedule_interval="* * * * *",
        catchup=False,
        max_active_runs=1,
        description="DAG for processing transaction data") as dag:
    fetch_transaction_data_task = PythonOperator(
        task_id="fetch_transaction_data",
        python_callable=fetch_transaction_data)
    fetch_save_raw_jsonto_S3=PythonOperator(
        task_id = "save_raw_jsonto_S3",
        python_callable =save_raw_jsonto_S3)
    transform_data_task = PythonOperator(
        task_id="transform_data",
        python_callable=transform_data)
    fetch_api_prediction_task = PythonOperator(
        task_id="fetch_api_prediction",
        python_callable=fetch_api_prediction)
    branch_task = BranchPythonOperator(
        task_id="check_fraud_branch",
        python_callable=check_fraud,
        provide_context=True)
    send_email_alert = EmailOperator(
        task_id="send_email_alert",
        to="gdleds31@gmail.com",
        subject="Fraud Alert",
        html_content="A fraudulent transaction has been detected.",
        files=["/tmp/transactions_with_predictions.csv"])
    continue_pipeline = EmptyOperator(
        task_id="continue_pipeline")
    store_to_training_data_task = PythonOperator(
        task_id="store_data_neon",
        python_callable=store_data_neon)
    cleanup_tmp_files_task = PythonOperator(
        task_id="cleanup_tmp_files",
        python_callable=cleanup_tmp_files)
    
    fetch_transaction_data_task >> transform_data_task >>  fetch_api_prediction_task >> branch_task
    branch_task >> [send_email_alert, continue_pipeline]
    continue_pipeline>> store_to_training_data_task >> cleanup_tmp_files_task