import tkinter as tk
from tkinter import filedialog, messagebox, Canvas, Scrollbar
from PIL import Image, ImageTk, ImageEnhance
import numpy as np
import cv2
import pyautogui
import time
import threading
import requests
from bs4 import BeautifulSoup
from io import BytesIO
from urllib.request import urlopen

# Попытка импортировать pygetwindow для активации окна (необязательная)
try:
    import pygetwindow as gw
except Exception:
    gw = None

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.01


class DrawingApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Image to Drawing")
        self.image = None  # PIL image (RGB)
        self.processed_image = None  # бинарное (грэй) numpy изображение или обрезок
        self.contours = None
        self.image_list = []
        self.photo_list = []
        self.preview_photo = None

        # Переменная для простого режима (галочка)
        self.simple_var = tk.BooleanVar(value=False)

        self.stop_event = threading.Event()
        self.draw_thread = None

        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        self.main_frame = tk.Frame(self.root)
        self.main_frame.grid(row=0, column=0, sticky="nsew")
        self.main_frame.grid_rowconfigure(7, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)

        self.create_menu()

    def create_menu(self):
        # Очистка и создание стартового меню
        for w in self.main_frame.winfo_children():
            w.destroy()

        self.menu_label = tk.Label(self.main_frame, text="Выберите способ загрузки изображения")
        self.menu_label.grid(row=0, column=0, columnspan=2, pady=10)

        tk.Button(self.main_frame, text="Поиск изображения в интернете", command=self.open_search).grid(
            row=1, column=0, columnspan=2, pady=5
        )
        tk.Button(self.main_frame, text="Выбор изображения с компьютера", command=self.load_local_image).grid(
            row=2, column=0, columnspan=2, pady=5
        )

    def open_search(self):
        # интерфейс поиска
        for w in self.main_frame.winfo_children():
            w.destroy()

        self.search_frame = tk.Frame(self.main_frame)
        self.search_frame.grid(row=0, column=0, columnspan=3, pady=5, sticky="ew")

        self.search_entry = tk.Entry(self.search_frame, width=50)
        self.search_entry.grid(row=0, column=0, pady=5, padx=5)

        tk.Button(self.search_frame, text="Поиск", command=self.perform_search).grid(row=0, column=1, pady=5, padx=5)
        tk.Button(self.search_frame, text="В начало", command=self.restart_to_main).grid(row=0, column=2, pady=5, padx=5)

        self.image_scroll_canvas = Canvas(self.main_frame, height=300)
        self.image_scroll_canvas.grid(row=1, column=0, columnspan=2, pady=5, sticky="nsew")

        self.scrollbar = Scrollbar(self.main_frame, orient="vertical", command=self.image_scroll_canvas.yview)
        self.scrollbar.grid(row=1, column=2, sticky="ns")

        self.image_scroll_canvas.configure(yscrollcommand=self.scrollbar.set)

        self.inner_frame = tk.Frame(self.image_scroll_canvas)
        self.image_scroll_canvas.create_window((0, 0), window=self.inner_frame, anchor="nw")

    def perform_search(self):
        query = self.search_entry.get().strip()
        if not query:
            messagebox.showerror("Ошибка", "Введите текст для поиска!")
            return

        search_query = f"{query} simple art white background"
        url = f"https://www.google.com/search?q={search_query.replace(' ', '+')}&tbm=isch"
        headers = {"User-Agent": "Mozilla/5.0"}
        try:
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, "html.parser")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось выполнить поиск: {e}")
            return

        img_tags = soup.find_all("img")
        self.image_list = []
        self.photo_list = []

        # очистка старого контейнера
        try:
            self.inner_frame.destroy()
        except Exception:
            pass
        self.inner_frame = tk.Frame(self.image_scroll_canvas)
        self.image_scroll_canvas.create_window((0, 0), window=self.inner_frame, anchor="nw")

        count = 0
        for img in img_tags:
            if count >= 20:
                break
            # пытаемся получить URL из разных атрибутов
            img_url = img.get("data-src") or img.get("data-iurl") or img.get("src")
            if not img_url:
                continue
            if img_url.startswith("data:"):  # base64-данные — пропустим
                continue
            if not img_url.startswith("http"):
                continue
            try:
                img_data = urlopen(img_url, timeout=8).read()
                pil = Image.open(BytesIO(img_data)).convert("RGB")
                thumb = pil.copy()
                thumb.thumbnail((100, 100))
                photo = ImageTk.PhotoImage(thumb)
                self.photo_list.append(photo)
                btn = tk.Button(self.inner_frame, image=photo, command=lambda idx=count: self.select_image(idx))
                btn.pack(pady=5)
                self.image_list.append(pil)
                count += 1
            except Exception:
                continue

        self.inner_frame.update_idletasks()
        self.image_scroll_canvas.configure(scrollregion=self.image_scroll_canvas.bbox("all"))

    def select_image(self, idx):
        self.image = self.image_list[idx].copy()
        # удаляем элементы поиска и открываем интерфейс настроек
        try:
            self.search_frame.destroy()
            self.image_scroll_canvas.destroy()
            self.scrollbar.destroy()
            self.menu_label.destroy()
        except Exception:
            pass
        self.create_settings_interface()
        self.update_preview(self.image)

    def load_local_image(self):
        file_path = filedialog.askopenfilename(filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp")])
        if file_path:
            self.image = Image.open(file_path).convert("RGB")
            try:
                self.menu_label.destroy()
            except Exception:
                pass
            self.create_settings_interface()
            self.update_preview(self.image)

    def create_settings_interface(self):
        # очищаем
        for w in self.main_frame.winfo_children():
            w.destroy()

        tk.Label(self.main_frame, text="Коэффициент яркости (1-5):").grid(row=1, column=0, pady=2, sticky="w")
        self.brightness_var = tk.DoubleVar(value=2.0)
        tk.Entry(self.main_frame, textvariable=self.brightness_var).grid(row=1, column=1, pady=2, sticky="e")

        tk.Label(self.main_frame, text="Порог бинаризации (0-255):").grid(row=2, column=0, pady=2, sticky="w")
        self.threshold_var = tk.IntVar(value=128)
        tk.Entry(self.main_frame, textvariable=self.threshold_var).grid(row=2, column=1, pady=2, sticky="e")

        tk.Label(self.main_frame, text="Чувствительность контуров (0.0000001-0.05):").grid(row=3, column=0, pady=2, sticky="w")
        self.epsilon_var = tk.DoubleVar(value=0.000001)
        tk.Entry(self.main_frame, textvariable=self.epsilon_var).grid(row=3, column=1, pady=2, sticky="e")

        tk.Label(self.main_frame, text="Размер кисти (пиксели):").grid(row=4, column=0, pady=2, sticky="w")
        self.brush_size_var = tk.IntVar(value=1)
        tk.Entry(self.main_frame, textvariable=self.brush_size_var).grid(row=4, column=1, pady=2, sticky="e")

        tk.Label(self.main_frame, text="Масштаб изображения (%):").grid(row=5, column=0, pady=2, sticky="w")
        self.scale_var = tk.DoubleVar(value=100.0)
        tk.Entry(self.main_frame, textvariable=self.scale_var).grid(row=5, column=1, pady=2, sticky="e")

        tk.Label(self.main_frame, text="Скорость рисования (пикселей/с):").grid(row=6, column=0, pady=2, sticky="w")
        self.speed_var = tk.IntVar(value=20)
        tk.Entry(self.main_frame, textvariable=self.speed_var).grid(row=6, column=1, pady=2, sticky="e")

        tk.Label(self.main_frame, text="Использовать заливку (контурная):").grid(row=7, column=0, pady=2, sticky="w")
        self.fill_var = tk.BooleanVar(value=False)
        tk.Checkbutton(self.main_frame, variable=self.fill_var).grid(row=7, column=1, pady=2, sticky="e")

        # --- Простой режим: галочка ---
        tk.Checkbutton(self.main_frame, text="Простой режим (без улучшений, исходное разрешение)", variable=self.simple_var).grid(
            row=8, column=0, columnspan=2, pady=2, sticky="w"
        )

        tk.Button(self.main_frame, text="Обработать изображение", command=self.process_image).grid(
            row=9, column=0, columnspan=2, pady=5
        )

        self.preview_label = tk.Label(self.main_frame)
        self.preview_label.grid(row=10, column=0, columnspan=2, pady=5)

        # Кнопки: Нарисовать, Stop, В начало
        tk.Button(self.main_frame, text="Нарисовать", command=self.start_drawing).grid(row=11, column=0, pady=5)
        tk.Button(self.main_frame, text="Stop", command=self.stop_drawing).grid(row=11, column=1, pady=5)
        tk.Button(self.main_frame, text="В начало", command=self.restart_to_main).grid(row=12, column=0, columnspan=2, pady=5)

    def process_image(self):
        if not self.image:
            messagebox.showerror("Ошибка", "Сначала загрузите изображение!")
            return
        try:
            # Если включён простой режим — используем упрощённую обработку
            if self.simple_var.get():
                # Обработка в исходном разрешении, без усиления яркости/CLAHE и без морфологии (минимально)
                img_array = np.array(self.image)  # RGB
                img_gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
                # Берём порог из поля (пользователь всё равно может регулировать)
                threshold = int(self.threshold_var.get())
                if not 0 <= threshold <= 255:
                    messagebox.showerror("Ошибка", "Порог бинаризации должен быть от 0 до 255!")
                    return
                _, img_bin = cv2.threshold(img_gray, threshold, 255, cv2.THRESH_BINARY)

                # Обрезка изображения (если есть не-нулевые пиксели)
                coords = cv2.findNonZero(img_bin)
                if coords is None:
                    messagebox.showwarning("Предупреждение", "В изображении не найдено активных пикселей после бинаризации.")
                    self.processed_image = img_bin
                    self.contours = []
                    self.update_preview(Image.fromarray(cv2.cvtColor(img_bin, cv2.COLOR_GRAY2RGB)))
                    return

                x, y, w, h = cv2.boundingRect(coords)
                img_bin = img_bin[y:y+h, x:x+w].copy()

                # Определение контуров на обрезке
                cnts_info = cv2.findContours(img_bin.copy(), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
                if len(cnts_info) == 3:
                    _, contours, _ = cnts_info
                else:
                    contours, _ = cnts_info

                filtered_contours = [c for c in contours if 20 < cv2.contourArea(c) < img_bin.size * 0.95]

                contour_image = cv2.cvtColor(img_bin, cv2.COLOR_GRAY2RGB)
                if filtered_contours:
                    cv2.drawContours(contour_image, filtered_contours, -1, (0, 255, 0), 1)

                self.contours = filtered_contours
                self.processed_image = img_bin
                self.update_preview(Image.fromarray(contour_image))
                return  # simple mode done

            # --- Сложный режим (твоя прежняя логика) ---
            enhancer = ImageEnhance.Brightness(self.image)
            brightness = self.brightness_var.get()
            if not 1.0 <= brightness <= 5.0:
                messagebox.showerror("Ошибка", "Коэффициент яркости должен быть от 1 до 5!")
                return
            img = enhancer.enhance(brightness)
            img_array = np.array(img)

            img_gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            threshold = int(self.threshold_var.get())
            if not 0 <= threshold <= 255:
                messagebox.showerror("Ошибка", "Порог бинаризации должен быть от 0 до 255!")
                return
            _, img_bin = cv2.threshold(img_gray, threshold, 255, cv2.THRESH_BINARY)

            kernel = np.ones((3, 3), np.uint8)
            img_bin = cv2.morphologyEx(img_bin, cv2.MORPH_OPEN, kernel, iterations=1)
            img_bin = cv2.morphologyEx(img_bin, cv2.MORPH_CLOSE, kernel, iterations=1)

            self.processed_image = img_bin

            # findContours: совместимость с разными версиями OpenCV
            cnts_info = cv2.findContours(img_bin.copy(), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
            if len(cnts_info) == 3:
                _, contours, hierarchy = cnts_info
            else:
                contours, hierarchy = cnts_info

            filtered_contours = [c for c in contours if 20 < cv2.contourArea(c) < img_bin.size * 0.95]

            contour_image = cv2.cvtColor(img_bin, cv2.COLOR_GRAY2RGB)
            if filtered_contours:
                cv2.drawContours(contour_image, filtered_contours, -1, (0, 255, 0), 1)
            else:
                messagebox.showwarning("Предупреждение", "Не найдено ни одного подходящего контура. Попробуйте изменить порог или яркость.")

            self.contours = filtered_contours
            self.update_preview(Image.fromarray(contour_image))

        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка обработки изображения: {e}")

    def update_preview(self, pil_image):
        # отображаем PIL изображение в preview_label и сохраняем ссылку на PhotoImage
        try:
            max_w, max_h = 350, 300
            img = pil_image.copy()
            img.thumbnail((max_w, max_h))
            self.preview_photo = ImageTk.PhotoImage(img)
            self.preview_label.configure(image=self.preview_photo)
        except Exception as e:
            print("Ошибка обновления превью:", e)

    def start_drawing(self):
        if self.processed_image is None or self.contours is None:
            messagebox.showerror("Ошибка", "Сначала обработайте изображение!")
            return

        if self.draw_thread and self.draw_thread.is_alive():
            messagebox.showinfo("Инфо", "Рисование уже выполняется.")
            return

        try:
            scale = float(self.scale_var.get())
            if not 10.0 <= scale <= 500.0:
                messagebox.showerror("Ошибка", "Масштаб должен быть от 10% до 500%!")
                return
            speed = int(self.speed_var.get())
            if not 1 <= speed <= 1000:
                messagebox.showerror("Ошибка", "Скорость должна быть от 1 до 1000 пикселей/с!")
                return
            brush_size = int(self.brush_size_var.get())
            if not 1 <= brush_size <= 10:
                messagebox.showerror("Ошибка", "Размер кисти должен быть от 1 до 10 пикселей!")
                return
            epsilon_factor = float(self.epsilon_var.get())
            if not 0.0000001 <= epsilon_factor <= 0.05:
                messagebox.showerror("Ошибка", "Чувствительность контуров должна быть от 0.0000001 до 0.05!")
                return

            # отсчёт
            for i in range(3, 0, -1):
                print(f"Рисование начнется через {i}...")
                time.sleep(1)

            try:
                start_x, start_y = pyautogui.position()
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось определить позицию курсора: {e}")
                return

            scale_factor = scale / 100.0
            height, width = self.processed_image.shape  # h, w
            resized_size = (int(width * scale_factor), int(height * scale_factor))  # (w, h)
            img_resized = cv2.resize(self.processed_image, resized_size, interpolation=cv2.INTER_AREA)

            # findContours с защитой совместимости
            cnts_info = cv2.findContours(img_resized.copy(), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
            if len(cnts_info) == 3:
                _, contours, hierarchy = cnts_info
            else:
                contours, hierarchy = cnts_info

            print(f"Найдено контуров: {len(contours)}")
            min_contour_area = 20  # можно масштабировать при желании
            max_contour_area = img_resized.size * 0.95

            filtered_contours = []
            for i, c in enumerate(contours):
                area = cv2.contourArea(c)
                if min_contour_area < area < max_contour_area:
                    # hierarchy может быть None
                    if hierarchy is None:
                        filtered_contours.append(c)
                    else:
                        try:
                            parent = hierarchy[0][i][3]
                            if parent == -1 or parent == 0:
                                filtered_contours.append(c)
                        except Exception:
                            filtered_contours.append(c)

            print(f"Отфильтровано контуров: {len(filtered_contours)}")

            # Аппроксимация контуров и подготовка списков точек
            contour_points = []
            fill_areas = []
            for cnt in filtered_contours:
                epsilon = epsilon_factor * cv2.arcLength(cnt, True)
                approx = cv2.approxPolyDP(cnt, epsilon, True)
                pts = approx.reshape(-1, 2).tolist()  # список (x,y)
                if len(pts) >= 2:
                    contour_points.append(pts)
                if self.fill_var.get() and cv2.contourArea(cnt) > 100:
                    fill_areas.append(cnt)

            delay = 1.0 / speed if speed > 0 else 0.01

            # функция безопасного клипа координат в экран
            screen_w, screen_h = pyautogui.size()

            def draw_thread_fn(contour_points, fill_areas, start_x, start_y, delay, brush_size):
                self.stop_event.clear()
                try:
                    # попытка активировать окно Paint, если доступно
                    try:
                        if gw:
                            wins = gw.getWindowsWithTitle("Paint")
                            if wins:
                                wins[0].activate()
                                time.sleep(0.5)
                    except Exception:
                        pass

                    # рисуем контуры
                    for pts in contour_points:
                        if self.stop_event.is_set():
                            print("Остановлено пользователем (контуры).")
                            return
                        if len(pts) < 2:
                            continue
                        first_x, first_y = pts[0]
                        pyautogui.moveTo(int(start_x + first_x), int(start_y + first_y))
                        pyautogui.mouseDown(button="left")
                        for x, y in pts[1:]:
                            if self.stop_event.is_set():
                                break
                            tx = int(start_x + x)
                            ty = int(start_y + y)
                            # защита выхода за экран
                            tx = max(0, min(screen_w - 1, tx))
                            ty = max(0, min(screen_h - 1, ty))
                            pyautogui.moveTo(tx, ty, duration=delay)
                        pyautogui.mouseUp(button="left")
                        time.sleep(delay)

                    # простая (медленная) заливка по пикселям — заметка: очень медленно для больших областей
                    if fill_areas:
                        for cnt in fill_areas:
                            if self.stop_event.is_set():
                                print("Остановлено пользователем (заливка).")
                                return
                            x, y, w, h = cv2.boundingRect(cnt)
                            mask = np.zeros((resized_size[1], resized_size[0]), dtype=np.uint8)
                            cv2.drawContours(mask, [cnt], -1, 255, thickness=cv2.FILLED)
                            pyautogui.mouseDown(button="left")
                            for yy in range(y, y + h):
                                if self.stop_event.is_set():
                                    break
                                for xx in range(x, x + w):
                                    if mask[yy, xx] == 255:
                                        tx = int(start_x + xx)
                                        ty = int(start_y + yy)
                                        tx = max(0, min(screen_w - 1, tx))
                                        ty = max(0, min(screen_h - 1, ty))
                                        pyautogui.moveTo(tx, ty, duration=max(0.001, delay / 10))
                                # небольшая пауза между строками
                                time.sleep(max(0.0, delay / 50))
                            pyautogui.mouseUp(button="left")
                            time.sleep(delay / 10)

                except Exception as e:
                    print("Ошибка при рисовании:", e)
                    try:
                        pyautogui.mouseUp(button="left")
                    except Exception:
                        pass

            # запуск потока рисования
            self.draw_thread = threading.Thread(
                target=draw_thread_fn,
                args=(contour_points, fill_areas, start_x, start_y, delay, brush_size),
                daemon=True,
            )
            self.draw_thread.start()

        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при запуске рисования: {e}")

    def stop_drawing(self):
        # Остановить поток рисования безопасно
        self.stop_event.set()
        if self.draw_thread and self.draw_thread.is_alive():
            try:
                self.draw_thread.join(timeout=1.0)
            except Exception:
                pass
        self.draw_thread = None
        print("Команда остановки отправлена.")

    def restart_to_main(self):
        # Остановим рисование и очистим данные, затем вернёмся в главное меню
        self.stop_drawing()
        # Очистим временные данные
        self.image = None
        self.processed_image = None
        self.contours = None
        self.image_list = []
        self.photo_list = []
        self.preview_photo = None
        # Вернём интерфейс в начальное состояние
        self.create_menu()

def main():
    root = tk.Tk()
    app = DrawingApp(root)
    root.geometry("470x470")
    root.mainloop()


if __name__ == "__main__":
    main()
