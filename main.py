import customtkinter as ctk
import requests
from bs4 import BeautifulSoup
import threading
import time
from plyer import notification
import json
import os
from datetime import datetime

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

DATA_FILE = "products.json"


class ProductDetails(ctk.CTkToplevel):
    def __init__(self, product, on_close):
        super().__init__()
        self.title(f"📦 {product['name']}")
        self.geometry("600x500")
        self.resizable(True, True)
        self.product = product
        self.on_close = on_close
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.lift()
        self.focus_force()
        self.setup_ui()

    def setup_ui(self):
        ctk.CTkLabel(self, text=f"📦 {self.product['name']}",
                     font=ctk.CTkFont(size=20, weight="bold")).pack(pady=15)

        info_frame = ctk.CTkFrame(self, corner_radius=12)
        info_frame.pack(fill="x", padx=20, pady=5)
        info_frame.grid_columnconfigure((0, 1, 2), weight=1)

        self.make_info_card(info_frame, "💰 سعر البداية",
                            f"{self.product['initial_price']:,.0f}", "#3498db", 0)
        self.make_info_card(info_frame, "📊 السعر الحالي",
                            f"{self.product['current_price']:,.0f}", "#2ecc71", 1)

        diff = self.product['current_price'] - self.product['initial_price']
        diff_color = "#2ecc71" if diff < 0 else "#e74c3c" if diff > 0 else "#95a5a6"
        diff_text = f"{'↓' if diff < 0 else '↑' if diff > 0 else '='} {abs(diff):,.0f}"
        self.make_info_card(info_frame, "📈 التغيير", diff_text, diff_color, 2)

        interval_frame = ctk.CTkFrame(self, corner_radius=12)
        interval_frame.pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(interval_frame, text="⏱️ فحص كل:",
                     font=ctk.CTkFont(size=13, weight="bold")).pack(side="left", padx=15, pady=10)

        self.interval_var = ctk.StringVar(value=str(self.product.get("interval", 60)))
        intervals = [("30 دقيقة", "30"), ("ساعة", "60"), ("3 ساعات", "180"), ("6 ساعات", "360")]
        for label, val in intervals:
            ctk.CTkRadioButton(interval_frame, text=label,
                               variable=self.interval_var, value=val,
                               command=self.save_interval).pack(side="left", padx=10, pady=10)

        ctk.CTkLabel(self, text="🖥️ سجل المراقبة:",
                     font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", padx=20, pady=5)

        self.log_box = ctk.CTkTextbox(self, height=220, corner_radius=10,
                                      font=ctk.CTkFont(family="Courier", size=11))
        self.log_box.pack(fill="both", padx=20, pady=5, expand=True)
        self.log_box.configure(state="disabled")

        for entry in self.product.get("logs", []):
            self.append_log(entry)

    def make_info_card(self, parent, title, value, color, col):
        card = ctk.CTkFrame(parent, corner_radius=10, fg_color="#1e1e2e")
        card.grid(row=0, column=col, padx=8, pady=10, sticky="ew")
        ctk.CTkLabel(card, text=title, text_color="#aaaaaa",
                     font=ctk.CTkFont(size=11)).pack(pady=(8, 2))
        ctk.CTkLabel(card, text=value, text_color=color,
                     font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(2, 8))

    def append_log(self, msg):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", f"{msg}\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def save_interval(self):
        self.product["interval"] = int(self.interval_var.get())
        self.on_close()

    def close(self):
        self.on_close()
        self.destroy()


class PriceTracker(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("🐍 py.builds - Price Tracker")
        self.geometry("800x680")
        self.resizable(True, True)
        self.products = self.load_products()
        self.tracking = False
        self.detail_windows = {}
        self.setup_ui()
        self.refresh_list()

    def load_products(self):
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        return []

    def save_products(self):
        with open(DATA_FILE, "w") as f:
            json.dump(self.products, f, ensure_ascii=False)

    def setup_ui(self):
        ctk.CTkLabel(self, text="🔥 Price Tracker",
                     font=ctk.CTkFont(size=30, weight="bold")).pack(pady=15)

        input_frame = ctk.CTkFrame(self, corner_radius=15)
        input_frame.pack(fill="x", padx=25, pady=5)

        ctk.CTkLabel(input_frame, text="➕ إضافة منتج جديد",
                     font=ctk.CTkFont(size=15, weight="bold")).grid(row=0, column=0, columnspan=2, pady=10)

        ctk.CTkLabel(input_frame, text="اسم المنتج:").grid(row=1, column=0, padx=15, pady=8, sticky="e")
        self.name_entry = ctk.CTkEntry(input_frame, width=450, placeholder_text="مثال: لاب توب لينوفو")
        self.name_entry.grid(row=1, column=1, padx=15, pady=8)

        ctk.CTkLabel(input_frame, text="لينك المنتج:").grid(row=2, column=0, padx=15, pady=8, sticky="e")
        self.url_entry = ctk.CTkEntry(input_frame, width=450, placeholder_text="https://...")
        self.url_entry.grid(row=2, column=1, padx=15, pady=8)

        btn_frame = ctk.CTkFrame(input_frame, fg_color="transparent")
        btn_frame.grid(row=3, column=0, columnspan=2, pady=12)

        ctk.CTkButton(btn_frame, text="➕ أضف المنتج وراقب",
                      command=self.add_product,
                      width=220, height=40,
                      font=ctk.CTkFont(size=14, weight="bold"),
                      fg_color="#1f6aa5").pack(side="left", padx=10)

        ctk.CTkButton(btn_frame, text="🔍 فحص دلوقتي",
                      command=self.check_now,
                      width=160, height=40,
                      font=ctk.CTkFont(size=14, weight="bold"),
                      fg_color="#7d3c98").pack(side="left", padx=10)

        ctk.CTkLabel(self, text="📋 قائمة المنتجات — دوس على منتج عشان تشوف التفاصيل",
                     font=ctk.CTkFont(size=13), text_color="#aaaaaa").pack(pady=5)

        self.list_frame = ctk.CTkScrollableFrame(self, height=280, corner_radius=12)
        self.list_frame.pack(fill="x", padx=25, pady=5)
        self.list_frame.grid_columnconfigure(0, weight=1)

        self.status_label = ctk.CTkLabel(self, text="⏳ في الانتظار...",
                                         font=ctk.CTkFont(size=13),
                                         text_color="gray")
        self.status_label.pack(pady=8)

    def log_to_product(self, product, msg):
        timestamp = datetime.now().strftime("%H:%M:%S")
        entry = f"[{timestamp}] {msg}"
        if "logs" not in product:
            product["logs"] = []
        product["logs"].append(entry)
        name = product["name"]
        if name in self.detail_windows:
            try:
                if self.detail_windows[name].winfo_exists():
                    self.detail_windows[name].append_log(entry)
            except Exception:
                pass

    def get_price(self, url, product=None):
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Accept-Language": "ar-EG,ar;q=0.9,en;q=0.8",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "DNT": "1",
        }
        try:
            session = requests.Session()
            response = session.get(url, headers=headers, timeout=15)
            soup = BeautifulSoup(response.content, "html.parser")

            selectors = [
                ("span", {"class": "a-price-whole"}),
                ("span", {"id": "priceblock_ourprice"}),
                ("span", {"id": "priceblock_dealprice"}),
                ("span", {"class": "a-offscreen"}),
            ]
            for tag, attrs in selectors:
                price = soup.find(tag, attrs)
                if price:
                    cleaned = price.text.replace(",", "").replace("ج.م", "").replace("EGP", "").strip()
                    cleaned = ''.join(filter(lambda x: x.isdigit() or x == '.', cleaned))
                    if cleaned:
                        if product:
                            self.after(0, lambda p=product, c=cleaned:
                                       self.log_to_product(p, f"✅ السعر: {float(c):,.0f}"))
                        return float(cleaned)

            if product:
                self.after(0, lambda p=product:
                           self.log_to_product(p, "❌ مش لاقي سعر في الصفحة"))

        except Exception as e:
            if product:
                self.after(0, lambda p=product, err=str(e):
                           self.log_to_product(p, f"❌ Error: {err}"))
        return None

    def open_details(self, product):
        name = product["name"]
        if name in self.detail_windows:
            try:
                if self.detail_windows[name].winfo_exists():
                    self.detail_windows[name].focus()
                    return
            except Exception:
                pass

        def on_close():
            self.save_products()

        win = ProductDetails(product, on_close)
        self.detail_windows[name] = win

    def add_product(self):
        url = self.url_entry.get().strip()
        name = self.name_entry.get().strip()

        if not url or not name:
            self.status_label.configure(text="⚠️ من فضلك املأ الاسم واللينك!", text_color="orange")
            return

        self.status_label.configure(text="⏳ بيجيب السعر الحالي...", text_color="cyan")
        self.update()

        def fetch_and_add():
            product = {
                "name": name, "url": url,
                "initial_price": 0, "current_price": 0,
                "status": "⏳ جاري...", "interval": 60, "logs": []
            }
            self.after(0, lambda p=product:
                       self.log_to_product(p, "🔍 جاري جلب السعر الأولي..."))

            price = self.get_price(url, product)
            if not price:
                self.after(0, lambda: self.status_label.configure(
                    text="❌ مش قادر يجيب السعر، تأكد من اللينك!", text_color="red"))
                return

            product["initial_price"] = price
            product["current_price"] = price
            product["status"] = "🟢 يراقب"
            self.products.append(product)
            self.save_products()

            self.after(0, self.refresh_list)
            self.after(0, lambda: self.status_label.configure(
                text=f"✅ تم إضافة {name} بسعر {price:,.0f}", text_color="green"))
            self.after(0, lambda: self.url_entry.delete(0, "end"))
            self.after(0, lambda: self.name_entry.delete(0, "end"))

            if not self.tracking:
                self.tracking = True
                thread = threading.Thread(target=self.track_all, daemon=True)
                thread.start()

        threading.Thread(target=fetch_and_add, daemon=True).start()

    def check_now(self):
        if not self.products:
            self.status_label.configure(text="⚠️ مفيش منتجات!", text_color="orange")
            return

        self.status_label.configure(text="🔍 جاري الفحص...", text_color="cyan")

        def do_check():
            for p in self.products:
                self.after(0, lambda prod=p:
                           self.log_to_product(prod, "🔍 فحص يدوي..."))
                price = self.get_price(p["url"], p)
                if price:
                    if price < p["current_price"]:
                        p["status"] = "🔴 نزل!"
                        notification.notify(
                            title="🔥 السعر نزل!",
                            message=f"{p['name']} نزل من {p['current_price']:,.0f} لـ {price:,.0f}!",
                            timeout=10
                        )
                        self.after(0, lambda prod=p, old=p["current_price"], new=price:
                                   self.log_to_product(prod, f"🔥 نزل من {old:,.0f} لـ {new:,.0f}!"))
                    else:
                        p["status"] = "🟢 يراقب"
                        self.after(0, lambda prod=p, pr=price:
                                   self.log_to_product(prod, f"✅ السعر ثابت {pr:,.0f}"))
                    p["current_price"] = price
                    self.save_products()
                    self.after(0, self.refresh_list)

            self.after(0, lambda: self.status_label.configure(
                text="✅ تم الفحص!", text_color="green"))

        threading.Thread(target=do_check, daemon=True).start()

    def refresh_list(self):
        for widget in self.list_frame.winfo_children():
            widget.destroy()

        if not self.products:
            ctk.CTkLabel(self.list_frame, text="لا يوجد منتجات مضافة بعد",
                         text_color="gray").grid(row=0, column=0, pady=20)
            return

        for i, p in enumerate(self.products):
            card = ctk.CTkFrame(self.list_frame, corner_radius=10,
                                fg_color="#1e1e2e", cursor="hand2")
            card.grid(row=i, column=0, sticky="ew", padx=5, pady=5)
            card.grid_columnconfigure(1, weight=1)

            card.bind("<Button-1>", lambda e, prod=p: self.open_details(prod))

            status_lbl = ctk.CTkLabel(card, text=p["status"], width=90,
                                      font=ctk.CTkFont(size=12), cursor="hand2")
            status_lbl.grid(row=0, column=0, padx=10, pady=8)
            status_lbl.bind("<Button-1>", lambda e, prod=p: self.open_details(prod))

            name_label = ctk.CTkLabel(card, text=p["name"],
                                      font=ctk.CTkFont(size=13, weight="bold"),
                                      anchor="w", cursor="hand2")
            name_label.grid(row=0, column=1, padx=5, pady=8, sticky="w")
            name_label.bind("<Button-1>", lambda e, prod=p: self.open_details(prod))

            diff = p["current_price"] - p["initial_price"]
            diff_text = f"({'↓' if diff < 0 else '↑'} {abs(diff):,.0f})" if diff != 0 else ""
            diff_color = "#2ecc71" if diff < 0 else "#e74c3c" if diff > 0 else "#aaaaaa"

            price_frame = ctk.CTkFrame(card, fg_color="transparent")
            price_frame.grid(row=1, column=0, columnspan=2, padx=10, pady=4, sticky="w")

            ctk.CTkLabel(price_frame,
                         text=f"سعر البداية: {p['initial_price']:,.0f}  |  الحالي: {p['current_price']:,.0f}  ",
                         text_color="#aaaaaa",
                         font=ctk.CTkFont(size=11)).pack(side="left")

            if diff_text:
                ctk.CTkLabel(price_frame, text=diff_text, text_color=diff_color,
                             font=ctk.CTkFont(size=11, weight="bold")).pack(side="left")

            ctk.CTkButton(card, text="🗑 مسح", width=70, height=30,
                          fg_color="#c0392b", hover_color="#e74c3c",
                          font=ctk.CTkFont(size=12),
                          command=lambda idx=i: self.delete_product(idx)).grid(
                row=0, column=2, padx=10, pady=8)

    def delete_product(self, idx):
        name = self.products[idx]["name"]
        self.products.pop(idx)
        self.save_products()
        self.refresh_list()
        self.status_label.configure(text=f"🗑️ تم حذف {name}", text_color="orange")

    def track_all(self):
        timers = {}
        while self.tracking:
            now = time.time()
            for p in self.products:
                interval = p.get("interval", 60) * 60
                last = timers.get(p["name"], 0)
                if now - last >= interval:
                    timers[p["name"]] = now
                    self.after(0, lambda prod=p:
                               self.log_to_product(prod, "🔄 فحص تلقائي..."))
                    price = self.get_price(p["url"], p)
                    if price:
                        if price < p["current_price"]:
                            notification.notify(
                                title="🔥 السعر نزل!",
                                message=f"{p['name']} نزل من {p['current_price']:,.0f} لـ {price:,.0f}!",
                                timeout=10
                            )
                            p["status"] = "🔴 نزل!"
                            self.after(0, lambda prod=p, old=p["current_price"], new=price:
                                       self.log_to_product(prod, f"🔥 نزل من {old:,.0f} لـ {new:,.0f}!"))
                        else:
                            p["status"] = "🟢 يراقب"
                        p["current_price"] = price
                        self.save_products()
                        self.after(0, self.refresh_list)
            time.sleep(60)


app = PriceTracker()
app.mainloop()