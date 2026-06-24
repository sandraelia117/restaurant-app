import oracledb
import pandas as pd
import streamlit as st
import os


# -------------------------
# Oracle Connection (Safe for Cloud)
# -------------------------
def get_connection():
    return oracledb.connect(
        user=st.secrets["DB_USER"],
        password=st.secrets["DB_PASSWORD"],
        dsn=st.secrets["DB_DSN"]
    )


# -------------------------
# Get Data
# -------------------------
@st.cache_data(ttl=5)
def get_data(query):
    conn = get_connection()
    df = pd.read_sql(query, conn)
    conn.close()
    return df


# -------------------------
# Execute Procedure
# -------------------------
def execute_procedure(proc_name, params=None):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.callproc(proc_name, params or [])

    conn.commit()
    cursor.close()
    conn.close()


# -------------------------
# Insert Pizza Sale
# -------------------------
def insert_pizza_sale(pizza_data):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO PIZZA_SALES
        (pizza_id, order_id, pizza_name_id, quantity, order_date,
         order_time, unit_price, total_price, pizza_size,
         pizza_category, pizza_ingredients, pizza_name)
        VALUES
        (:1, :2, :3, :4, :5, :6, :7, :8, :9, :10, :11, :12)
    """, [
        pizza_data['pizza_id'],
        pizza_data['order_id'],
        pizza_data['pizza_name_id'],
        pizza_data['quantity'],
        pizza_data['order_date'],
        pizza_data['order_time'],
        pizza_data['unit_price'],
        pizza_data['total_price'],
        pizza_data['pizza_size'],
        pizza_data['pizza_category'],
        pizza_data['pizza_ingredients'],
        pizza_data['pizza_name'],
    ])

    conn.commit()
    cursor.close()
    conn.close()