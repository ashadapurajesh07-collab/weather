import io
import json
import os
import threading
import tkinter as tk
from datetime import datetime
from tkinter import ttk

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from PIL import Image, ImageTk
import requests

# Set your OpenWeatherMap API Key here
API_KEY = "748344eb910871ffcbf283ad80e50bd7"
FAVORITES_FILE = "favorites.json"

# Theme Configurations
THEMES = {
    "Clear_Day": {"bg": "#fff3e0", "card": "#ffffff", "fg": "#e65100", "accent": "#fb8c00"},
    "Clear_Night": {"bg": "#1a237e", "card": "#283593", "fg": "#e8eaf6", "accent": "#5c6bc0"},
    "Clouds": {"bg": "#eceff1", "card": "#ffffff", "fg": "#37474f", "accent": "#78909c"},
    "Rain": {"bg": "#e1f5fe", "card": "#ffffff", "fg": "#0277bd", "accent": "#29b6f6"},
    "Snow": {"bg": "#f3e5f5", "card": "#ffffff", "fg": "#4a148c", "accent": "#ab47bc"},
    "Dark": {"bg": "#121212", "card": "#1e1e1e", "fg": "#ffffff", "accent": "#bb86fc"},
}


class AdvancedWeatherApp:

    def __init__(self, root):
        self.root = root
        self.root.title("Pro Weather App & Analytics")
        self.root.geometry("620x920")
        self.root.resizable(False, False)

        self.current_unit = "metric"
        self.dark_mode = False
        self.current_theme = THEMES["Clouds"]
        self.icon_cache = {}
        self.favorites = self.load_favorites()

        self.setup_ui()
        self.apply_theme(self.current_theme)
        self.auto_detect_location()

    def load_favorites(self):
        if os.path.exists(FAVORITES_FILE):
            try:
                with open(FAVORITES_FILE, "r") as f:
                    return json.load(f)
            except Exception:
                return []
        return []

    def save_favorites(self):
        try:
            with open(FAVORITES_FILE, "w") as f:
                json.dump(self.favorites, f)
        except Exception:
            pass

    def setup_ui(self):
        # Top Header / Search & Settings (using ttk.Frame for padding support)
        self.top_frame = ttk.Frame(self.root, padding=10)
        self.top_frame.pack(fill="x", padx=10, pady=5)

        self.city_entry = ttk.Entry(self.top_frame, width=18, font=("Segoe UI", 10))
        self.city_entry.pack(side="left", padx=(0, 5))

        self.btn_search = tk.Button(
            self.top_frame, text="Search", command=self.start_fetch_thread, font=("Segoe UI", 9, "bold")
        )
        self.btn_search.pack(side="left", padx=2)

        self.btn_fav = tk.Button(self.top_frame, text="★ Add Fav", command=self.add_favorite, font=("Segoe UI", 9))
        self.btn_fav.pack(side="left", padx=2)

        self.fav_var = tk.StringVar(value="Favorites")
        self.fav_dropdown = ttk.Combobox(
            self.top_frame, textvariable=self.fav_var, values=self.favorites, state="readonly", width=12
        )
        self.fav_dropdown.pack(side="left", padx=5)
        self.fav_dropdown.bind("<<ComboboxSelected>>", self.on_favorite_select)

        self.btn_unit = tk.Button(self.top_frame, text="°C / °F", command=self.toggle_unit, font=("Segoe UI", 9))
        self.btn_unit.pack(side="right", padx=2)

        self.btn_dark = tk.Button(self.top_frame, text="🌙 Mode", command=self.toggle_dark_mode, font=("Segoe UI", 9))
        self.btn_dark.pack(side="right", padx=2)

        # Main Container
        self.main_container = tk.Frame(self.root)
        self.main_container.pack(fill="both", expand=True, padx=10, pady=5)

        # 1. Current Weather Panel
        self.current_card = tk.LabelFrame(self.main_container, text=" Current Weather ", font=("Segoe UI", 10, "bold"))
        self.current_card.pack(fill="x", pady=5)

        self.lbl_city = tk.Label(self.current_card, text="--", font=("Segoe UI", 16, "bold"))
        self.lbl_city.pack()

        self.lbl_icon = tk.Label(self.current_card)
        self.lbl_icon.pack()

        self.lbl_temp = tk.Label(self.current_card, text="-- °C", font=("Segoe UI", 28, "bold"))
        self.lbl_temp.pack()

        self.lbl_desc = tk.Label(self.current_card, text="--", font=("Segoe UI", 11, "italic"))
        self.lbl_desc.pack()

        self.lbl_details = tk.Label(self.current_card, text="Humidity: --% | Wind: -- km/h", font=("Segoe UI", 9))
        self.lbl_details.pack(pady=4)

        # 2. Air Quality & Weather Metrics Card
        self.metrics_card = tk.LabelFrame(self.main_container, text=" Air Quality & UV Details ", font=("Segoe UI", 10, "bold"))
        self.metrics_card.pack(fill="x", pady=5)

        self.lbl_aqi = tk.Label(self.metrics_card, text="AQI: -- | PM2.5: -- | PM10: --", font=("Segoe UI", 9, "bold"))
        self.lbl_aqi.pack(pady=2)

        self.lbl_sun_uv = tk.Label(self.metrics_card, text="Sunrise: -- | Sunset: --", font=("Segoe UI", 9))
        self.lbl_sun_uv.pack(pady=2)

        # 2.5 Lifestyle & Activity Recommendations Card
        self.advice_card = tk.LabelFrame(
            self.main_container,
            text=" Daily Activity Advice ",
            font=("Segoe UI", 10, "bold"),
        )
        self.advice_card.pack(fill="x", pady=5)

        self.lbl_advice = tk.Label(
            self.advice_card,
            text="--",
            font=("Segoe UI", 9),
            justify="left",
            wraplength=520,
        )
        self.lbl_advice.pack(pady=4, padx=5)

        # 3. Interactive Matplotlib Trend Graph
        self.graph_card = tk.LabelFrame(self.main_container, text=" 24-Hour Temperature Trend ", font=("Segoe UI", 10, "bold"))
        self.graph_card.pack(fill="x", pady=5)

        self.fig, self.ax = plt.subplots(figsize=(5.5, 2.0), dpi=90)
        self.fig.patch.set_facecolor("#ffffff")
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.graph_card)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

        # Status Error / Loader Label
        self.lbl_error = tk.Label(self.root, text="", font=("Segoe UI", 9, "bold"), fg="red")
        self.lbl_error.pack(pady=2)

    def apply_theme(self, theme):
        self.current_theme = theme
        bg = theme["bg"]
        card = theme["card"]
        fg = theme["fg"]

        self.root.configure(bg=bg)
        self.main_container.configure(bg=bg)
        self.lbl_error.configure(bg=bg)

        for card_widget in [self.current_card, self.metrics_card, self.advice_card, self.graph_card]:
            card_widget.configure(bg=card, fg=fg)
            for child in card_widget.winfo_children():
                if isinstance(child, tk.Label):
                    child.configure(bg=card, fg=fg)

        self.fig.patch.set_facecolor(card)
        self.ax.set_facecolor(card)
        self.ax.tick_params(colors=fg)
        for spine in self.ax.spines.values():
            spine.set_color(fg)
        self.canvas.draw()

    def update_dynamic_theme(self, weather_condition, icon_code):
        if self.dark_mode:
            return
        is_night = "n" in icon_code
        if is_night:
            self.apply_theme(THEMES["Clear_Night"])
        elif "Rain" in weather_condition or "Drizzle" in weather_condition or "Thunderstorm" in weather_condition:
            self.apply_theme(THEMES["Rain"])
        elif "Snow" in weather_condition:
            self.apply_theme(THEMES["Snow"])
        elif "Clear" in weather_condition:
            self.apply_theme(THEMES["Clear_Day"])
        else:
            self.apply_theme(THEMES["Clouds"])

    def toggle_dark_mode(self):
        self.dark_mode = not self.dark_mode
        if self.dark_mode:
            self.apply_theme(THEMES["Dark"])
        else:
            self.apply_theme(THEMES["Clouds"])

    def show_error(self, message):
        self.lbl_error.config(text=message)

    def clear_error(self):
        self.lbl_error.config(text="")

    def add_favorite(self):
        city = self.city_entry.get().strip()
        if city and city not in self.favorites:
            self.favorites.append(city)
            self.save_favorites()
            self.fav_dropdown["values"] = self.favorites
            self.show_error(f"Added '{city}' to favorites!")

    def on_favorite_select(self, event):
        selected_city = self.fav_var.get()
        if selected_city and selected_city != "Favorites":
            self.city_entry.delete(0, tk.END)
            self.city_entry.insert(0, selected_city)
            self.start_fetch_thread()

    def get_weather_icon(self, icon_code):
        if icon_code in self.icon_cache:
            return self.icon_cache[icon_code]
        try:
            url = f"https://openweathermap.org/img/wn/{icon_code}@4x.png"
            res = requests.get(url, timeout=5)
            if res.status_code == 200:
                img = Image.open(io.BytesIO(res.content)).resize((70, 70), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                self.icon_cache[icon_code] = photo
                return photo
        except Exception:
            pass
        return None

    def toggle_unit(self):
        self.current_unit = "imperial" if self.current_unit == "metric" else "metric"
        if self.city_entry.get().strip():
            self.start_fetch_thread()

    def auto_detect_location(self):
        def task():
            try:
                res = requests.get("https://ipinfo.io/json", timeout=5)
                if res.status_code == 200:
                    city = res.json().get("city")
                    if city:
                        self.city_entry.insert(0, city)
                        self.fetch_all_data(city)
            except Exception:
                self.show_error("Could not auto-detect location.")

        threading.Thread(target=task, daemon=True).start()

    def generate_recommendations(self, curr_data, aqi_data):
        temp = curr_data["main"]["temp"]
        humidity = curr_data["main"]["humidity"]
        condition = curr_data["weather"][0]["main"]
        aqi = aqi_data["list"][0]["main"]["aqi"]

        # Convert temperature threshold to Celsius equivalent if imperial unit is active
        temp_c = temp if self.current_unit == "metric" else (temp - 32) * 5 / 9

        advice_list = []

        # Weather Condition Rules
        if condition in ["Rain", "Drizzle", "Thunderstorm"]:
            advice_list.append("☔ Carry an umbrella and expect wet roads.")
        elif condition == "Clear":
            advice_list.append("☀️ Great clear skies for outdoor activities!")

        # Temperature Rules
        if temp_c > 35:
            advice_list.append("🔥 Extreme heat: Stay hydrated and avoid noon sun.")
        elif temp_c < 10:
            advice_list.append("🧥 Cold weather: Wear warm layers outdoors.")

        # Air Quality Rules
        if aqi >= 4:
            advice_list.append("😷 Poor Air Quality: Limit strenuous outdoor exercise.")
        elif aqi <= 2:
            advice_list.append("🏃 Air quality is good for running/cycling.")

        # Humidity Rules
        if humidity > 80 and temp_c > 28:
            advice_list.append("💦 High humidity: Take frequent water breaks.")

        return "\n".join(advice_list) if advice_list else "👍 Weather conditions are mild and pleasant."

    def start_fetch_thread(self):
        city = self.city_entry.get().strip()
        if not city:
            self.show_error("Please enter a city or ZIP code.")
            return

        if not API_KEY or API_KEY == "YOUR_OPENWEATHERMAP_API_KEY":
            self.show_error("Please configure your valid API Key.")
            return

        self.clear_error()
        self.show_error("Fetching latest weather data...")
        threading.Thread(target=self.fetch_all_data, args=(city,), daemon=True).start()

    def fetch_all_data(self, city):
        try:
            curr_url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&units={self.current_unit}&appid={API_KEY}"
            curr_res = requests.get(curr_url, timeout=5)

            if curr_res.status_code == 404:
                self.root.after(0, self.show_error, "City not found.")
                return
            elif curr_res.status_code != 200:
                self.root.after(0, self.show_error, f"API Error: HTTP {curr_res.status_code}")
                return

            curr_data = curr_res.json()
            lat = curr_data["coord"]["lat"]
            lon = curr_data["coord"]["lon"]

            forecast_url = f"https://api.openweathermap.org/data/2.5/forecast?q={city}&units={self.current_unit}&appid={API_KEY}"
            forecast_data = requests.get(forecast_url, timeout=5).json()

            aqi_url = f"https://api.openweathermap.org/data/2.5/air_pollution?lat={lat}&lon={lon}&appid={API_KEY}"
            aqi_data = requests.get(aqi_url, timeout=5).json()

            self.root.after(0, self.update_all_ui, curr_data, forecast_data, aqi_data)

        except requests.exceptions.Timeout:
            self.root.after(0, self.show_error, "Request timed out.")
        except Exception as e:
            self.root.after(0, self.show_error, f"Error: {str(e)}")

    def update_all_ui(self, curr, forecast, aqi):
        self.clear_error()

        unit_sym = "°C" if self.current_unit == "metric" else "°F"
        speed_sym = "km/h" if self.current_unit == "metric" else "mph"

        temp = curr["main"]["temp"]
        humidity = curr["main"]["humidity"]
        raw_wind = curr["wind"]["speed"]
        wind_speed = round(raw_wind * 3.6, 1) if self.current_unit == "metric" else round(raw_wind, 1)

        city_name = f"{curr['name']}, {curr['sys'].get('country', '')}"
        condition = curr["weather"][0]["main"]
        desc = curr["weather"][0]["description"].title()
        icon_code = curr["weather"][0]["icon"]

        self.lbl_city.config(text=city_name)
        self.lbl_temp.config(text=f"{temp:.1f} {unit_sym}")
        self.lbl_desc.config(text=desc)
        self.lbl_details.config(text=f"Humidity: {humidity}% | Wind: {wind_speed} {speed_sym}")

        photo = self.get_weather_icon(icon_code)
        if photo:
            self.lbl_icon.config(image=photo)
            self.lbl_icon.image = photo

        self.update_dynamic_theme(condition, icon_code)

        aqi_qualities = {1: "Good", 2: "Fair", 3: "Moderate", 4: "Poor", 5: "Very Poor"}
        aqi_val = aqi["list"][0]["main"]["aqi"]
        pm25 = aqi["list"][0]["components"]["pm2_5"]
        pm10 = aqi["list"][0]["components"]["pm10"]

        sunrise = datetime.fromtimestamp(curr["sys"]["sunrise"]).strftime("%I:%M %p")
        sunset = datetime.fromtimestamp(curr["sys"]["sunset"]).strftime("%I:%M %p")

        self.lbl_aqi.config(text=f"AQI: {aqi_qualities.get(aqi_val, '--')} ({aqi_val}) | PM2.5: {pm25} | PM10: {pm10}")
        self.lbl_sun_uv.config(text=f"🌅 Sunrise: {sunrise}  |  🌇 Sunset: {sunset}")

        # Update Lifestyle Advice
        advice_text = self.generate_recommendations(curr, aqi)
        self.lbl_advice.config(text=advice_text)

        self.update_graph(forecast, unit_sym)

    def update_graph(self, forecast_data, unit_sym):
        self.ax.clear()

        entries = forecast_data["list"][:8]
        times = [datetime.fromtimestamp(item["dt"]).strftime("%H:%M") for item in entries]
        temps = [item["main"]["temp"] for item in entries]

        fg_color = self.current_theme["fg"]
        accent_color = self.current_theme["accent"]

        self.ax.plot(times, temps, marker="o", color=accent_color, linewidth=2)
        self.ax.set_ylabel(f"Temp ({unit_sym})", color=fg_color, fontsize=8)
        self.ax.tick_params(colors=fg_color, labelsize=8)
        self.ax.set_facecolor(self.current_theme["card"])
        self.fig.patch.set_facecolor(self.current_theme["card"])

        for spine in self.ax.spines.values():
            spine.set_color(fg_color)

        self.fig.tight_layout()
        self.canvas.draw()


if __name__ == "__main__":
    root = tk.Tk()
    app = AdvancedWeatherApp(root)
    root.mainloop()