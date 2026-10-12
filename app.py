import streamlit as st
import requests
import pandas as pd
from datetime import datetime

API_KEY = "748344eb910871ffcbf283ad80e50bd7"

st.set_page_config(page_title="Pro Weather Analytics", layout="centered")
st.title("🌤️ Pro Weather App & Analytics")

city = st.text_input("Enter City Name", value="Hyderabad")

if st.button("Get Weather"):
    curr_url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&units=metric&appid={API_KEY}"
    res = requests.get(curr_url)
    
    if res.status_code == 200:
        data = res.json()
        temp = data["main"]["temp"]
        humidity = data["main"]["humidity"]
        wind = data["wind"]["speed"] * 3.6
        condition = data["weather"][0]["main"]
        
        # Current Weather Card
        st.subheader(f"Current Weather in {data['name']}, {data['sys'].get('country', '')}")
        col1, col2, col3 = st.columns(3)
        col1.metric("Temperature", f"{temp} °C")
        col2.metric("Humidity", f"{humidity} %")
        col3.metric("Wind Speed", f"{wind:.1f} km/h")
        
        # Lifestyle Recommendation Logic
        st.info("💡 **Daily Activity Advice**")
        if condition in ["Rain", "Drizzle", "Thunderstorm"]:
            st.write("☔ Carry an umbrella and expect wet roads.")
        elif temp > 35:
            st.write("🔥 Extreme heat: Stay hydrated and avoid direct noon sun.")
        else:
            st.write("🏃 Weather conditions are suitable for daily outdoor activities.")
            
        # 24-Hour Forecast Graph
        forecast_url = f"https://api.openweathermap.org/data/2.5/forecast?q={city}&units=metric&appid={API_KEY}"
        f_res = requests.get(forecast_url).json()
        
        entries = f_res["list"][:8]
        times = [datetime.fromtimestamp(item["dt"]).strftime("%H:%M") for item in entries]
        temps = [item["main"]["temp"] for item in entries]
        
        df = pd.DataFrame({"Time": times, "Temp (°C)": temps}).set_index("Time")
        st.line_chart(df)
    else:
        st.error("City not found or invalid API Key.")