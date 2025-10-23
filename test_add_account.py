#!/usr/bin/env python3
"""
Тестовый скрипт для добавления аккаунта
"""

import requests
import json

# Добавляем тестовый аккаунт
account_data = {
    "name": "Тестовый аккаунт",
    "phone": "9522675444"
}

try:
    response = requests.post(
        "http://localhost:8000/api/v1/accounts/add_account",
        json=account_data,
        headers={"Content-Type": "application/json"}
    )
    
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Session ID: {data.get('session_id')}")
    else:
        print(f"Error: {response.text}")
        
except Exception as e:
    print(f"Error: {e}")
