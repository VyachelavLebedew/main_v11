"""
Основной скрипт
"""

import math

import pickle
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.backends.backend_tkagg import NavigationToolbar2Tk
from matplotlib.figure import Figure

from helpers import is_corner_hexagon, find_closest_edge, hex_to_name, key_by_value
from info import MESSAGE_INFO


# pylint:disable=line-too-long,attribute-defined-outside-init
mpl.rcParams['savefig.dpi'] = 840  # Устанавливаем DPI для сохраняемых изображений

BUTTON_FONT = ("Times New Roma", 12)
BUTTON_PADDING = 3
NUM_SIDES_HEXAGON = 6
BASE_COLOR = 'white'

# Яркость
ALPHA = 0.6

# Размер окна графика
FIGSIZE = (16, 8)

# Шаг расстояния между элементами (шаг конфигурации)
STEP_PADDING = 1.2

# Цвета
COLORS = [('Красный', 'red'),
          ('Желтый', 'yellow'),
          ('Зеленый', 'green'),
          ('Синий', 'blue'),
          ('Оранжевый', 'orange'),
          ('Серый', 'gray'),
          ('Белый', 'white')]

# Цвета в черно-белом режиме
COLOR_TO_HATCH = {
            'red': '//////',
            'yellow': 'xxxxxx',
            'green': '......',
            'blue': 'oooo',
            'orange': '-----',
            'gray': '\\\\\\\\\\\\',
            'white': None
        }


class HexagonChartApp:
    """
    Класс оконного приложения
    """

    # pylint: disable=redefined-outer-name
    def __init__(self, root):
        # Основные настройки
        self.root = root
        self.root.title("Рисовалка")

        self.initialize_attributes()
        self.setup_UI()

    def initialize_attributes(self):
        """
        Определение атрибутов программы
        """
        self.color_map = {}
        self.original_colors = {}
        self.num_rings = 1
        self.min_rings = 1
        self.max_rings = 30
        self.padding = 0  # Расстояние между шестигранниками и текстом
        self.radius = 0
        self.hexagon_patches = []
        self.selected_color = BASE_COLOR
        self.remove_corners = tk.BooleanVar(value=False)
        self.toolbar = None
        self.editing_color = False
        self.adding_number = False
        self.adding_text = False
        self.editing_hexagon = False
        self.scale_factor = None
        self.coeff_padding = 0.4
        self.hexagon_numbers = {}
        self.hexagon_texts = {}
        self.removed_hexagons = set()
        self.dashed_hexagons = set()
        self.color_titles = {}  # Добавьте эту строку
        self.initial_xlim = None
        self.bw_mode = tk.BooleanVar(value=False)  # Черно-белый режим по умолчанию выключен
        self.color_to_hatch = COLOR_TO_HATCH

    def setup_UI(self):
        self.canvas_frame = ttk.Frame(self.root)
        self.canvas_frame.pack(fill=tk.BOTH, expand=True)
        self.canvas = None

        self.fig = self.draw_hexagon_chart()
        self.canvas = self._create_canvas()

        self.canvas.mpl_connect('button_press_event', self.on_click)
        self.canvas.mpl_connect('draw_event', self.update_text_size)
        self._create_controls()

    def _create_canvas(self):
        canvas = FigureCanvasTkAgg(self.fig, master=self.canvas_frame)
        self.toolbar = NavigationToolbar2Tk(canvas, self.canvas_frame)
        self.toolbar.update()
        # canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        canvas.get_tk_widget().pack(fill=tk.NONE, expand=False)
        return canvas

    def update_text_size(self, event=None):
        xlim = self.fig.axes[0].get_xlim()
        if self.initial_xlim is None:
            self.initial_xlim = xlim  # Сохраняем исходные пределы при первом вызове
            scale_factor = 1
        else:
            scale_factor = (self.initial_xlim[1] - self.initial_xlim[0]) / (xlim[1] - xlim[0])
        for hexagon, elements in self.hexagon_numbers.items():
            text_element = elements
            current_font_size = self.radius * 2  # Исходный размер шрифта
            new_font_size = current_font_size * scale_factor * 0.8  # Новый размер шрифта
            text_element.set_fontsize(new_font_size)
        self.canvas.draw_idle()

    def toggle_bw_mode(self):
        if self.bw_mode.get():
            for hexagon in self.hexagon_patches:
                color = hexagon.get_facecolor()
                color = hex_to_name(mpl.colors.to_hex(color))
                hatch_pattern = self.color_to_hatch.get(color, BASE_COLOR)
                hexagon.set_hatch(hatch_pattern)
                hexagon.set_facecolor(BASE_COLOR)
        else:
            for hexagon in self.hexagon_patches:
                original_color = self.color_map.get(hexagon, BASE_COLOR)
                hexagon.set_alpha(ALPHA)
                hexagon.set_facecolor(original_color)
                hexagon.set_hatch(None)
        self.canvas.draw_idle()
        self.update_legend()

    def _create_controls(self):
        style = ttk.Style()
        style.configure('TButton', font=BUTTON_FONT, padding=(BUTTON_PADDING, BUTTON_PADDING))
        style.configure('TCheckbutton', font=BUTTON_FONT)
        style.configure('TMenubutton', font=BUTTON_FONT)

        self._setup_top_controls()
        self._setup_middle_controls()

    def set_mode(self, value):
        modes = {
            "Просмотр": ("editing_color", False),
            "Изменить цвет": ("editing_color", True),
            "Добавить номер": ("adding_number", True),
            "Добавить текст": ("adding_text", True),
            "Добавить/Удалить элемент": ("editing_hexagon", True)
        }

        if value in modes:
            attribute, mode_value = modes[value]
            self.editing_color = False
            self.adding_number = False
            self.adding_text = False
            self.editing_hexagon = False
            setattr(self, attribute, mode_value)

    def _setup_top_controls(self):
        top_frame = ttk.Frame(self.root)
        top_frame.pack()

        self.size_button = ttk.Button(top_frame, text="Количество рядов", command=self.prompt_num_rings)
        self.add_layer_button = ttk.Button(top_frame, text="Добавить слой", command=self.add_ring)
        self.remove_layer_button = ttk.Button(top_frame, text="Удалить слой", command=self.remove_ring)

        self.mode_var = tk.StringVar(self.root)
        self.mode_var.set("Просмотр")
        self.mode_options = ["Просмотр", "Просмотр", "Изменить цвет", "Добавить номер",
                             "Добавить текст", "Добавить/Удалить элемент"]
        self.mode_dropdown = ttk.OptionMenu(top_frame, self.mode_var, *self.mode_options, command=self.set_mode)

        self.save_button = ttk.Button(top_frame, text="Сохранить фигуру", command=self.save_fig)
        self.load_button = ttk.Button(top_frame, text="Загрузить фигуру", command=self.load_fig)

        self.increase_padding_button = ttk.Button(top_frame, text="Увеличить расстояние", command=self.increase_padding)
        self.decrease_padding_button = ttk.Button(top_frame, text="Уменьшить расстояние", command=self.decrease_padding)

        self.info_button = ttk.Button(top_frame, text="Информация", command=self.show_info)
        self.edit_colors_button = ttk.Button(top_frame, text="Изменить имена цветов", command=self.edit_color_names)

        padx = 7
        pady = 3
        self.mode_dropdown.grid(row=1, column=0, padx=padx, pady=pady)

        self.size_button.grid(row=0, column=1, padx=padx, pady=pady)
        self.add_layer_button.grid(row=1, column=1, padx=padx, pady=pady)
        self.remove_layer_button.grid(row=2, column=1, padx=padx, pady=pady)

        self.save_button.grid(row=0, column=2, padx=padx, pady=pady)
        self.load_button.grid(row=1, column=2, padx=padx, pady=pady)

        self.increase_padding_button.grid(row=0, column=3, padx=padx, pady=pady)
        self.decrease_padding_button.grid(row=1, column=3, padx=padx, pady=pady)
        self.info_button.grid(row=1, column=4, padx=padx, pady=pady)

        self.edit_colors_button.grid(row=1, column=5, padx=padx, pady=pady)

    def _setup_middle_controls(self):
        middle_frame = ttk.Frame(self.root)
        middle_frame.pack(pady=10)

        self.color_button = ttk.Menubutton(middle_frame, text="Выбрать цвет", menu=self._create_color_menu())
        self.color_label = ttk.Label(middle_frame, text="Текущий цвет: " + self.selected_color, font=BUTTON_FONT)
        self.remove_corners_checkbutton = ttk.Checkbutton(middle_frame, text="Удалить угловые элементы",
                                                          variable=self.remove_corners,
                                                          command=self.update_hexagon_chart)

        for col, widget in enumerate([self.color_button, self.color_label, self.remove_corners_checkbutton]):
            widget.grid(row=0, column=col, padx=10)

        self.bw_button = ttk.Checkbutton(middle_frame, text="Черно-белый режим", variable=self.bw_mode,
                                         command=self.toggle_bw_mode)
        self.bw_button.grid(row=0, column=4, padx=10)

    def edit_color_names(self):
        # Создаем новое окно
        window = tk.Toplevel(self.root)
        window.title("Изменить описание")

        entries = {}
        # Для каждого уникального цвета создаем метку и поле для ввода
        for color in COLOR_TO_HATCH.keys():

            current_name = self.color_titles.get(color, '')

            label = ttk.Label(window, text=color)
            label.pack(pady=5)

            entry = ttk.Entry(window)
            entry.insert(0, current_name)
            entry.pack(pady=5)

            entries[color] = entry

        # Кнопка для сохранения изменений
        def save_changes():
            for color, entry in entries.items():
                self.color_titles[color] = entry.get()
            window.destroy()
            self.update_legend()

        save_button = ttk.Button(window, text="Сохранить", command=save_changes)
        save_button.pack(pady=10)

        # Кнопка для закрытия без сохранения
        cancel_button = ttk.Button(window, text="Отменить", command=window.destroy)
        cancel_button.pack(pady=10)

    def show_info(self):
        messagebox.showinfo("Информация", MESSAGE_INFO)

    def _create_color_menu(self):
        color_menu = tk.Menu(self.root, tearoff=0)
        colors = COLORS
        for label, color in colors:
            color_menu.add_command(label=label, command=lambda col=color: self.set_selected_color(col))
        return color_menu

    def add_number_to_hexagon(self, hexagon):
        # Проверяем, есть ли у шестигранника номер
        if hexagon in self.hexagon_numbers:
            if messagebox.askyesno("Удалить номер", "Вы хотите удалить номер с этого элемента?"):
                self.hexagon_numbers[hexagon].remove()
                del self.hexagon_numbers[hexagon]
                self.canvas.draw_idle()
        else:
            # Спрашиваем у пользователя номер для добавления
            number = tk.simpledialog.askinteger("Добавить номер", "Введите номер для элемента:")
            if number:
                radius = self.radius * 2
                x_center = np.mean(hexagon.get_xy()[:, 0])
                y_center = np.mean(hexagon.get_xy()[:, 1])
                text_element = self.fig.axes[0].text(x_center, y_center, str(number) + ' ',
                                                     ha='center', va='center', fontsize=radius)
                self.hexagon_numbers[hexagon] = text_element

    def add_text_to_hexagon(self, hexagon, event_point):
        """Добавляет или удаляет текст рядом с шестигранником."""
        if hexagon in self.hexagon_texts:
            if messagebox.askyesno("Удалить текст", "Вы хотите удалить текст с этого элемента?"):
                # Удаляем текст
                self.hexagon_texts[hexagon].remove()
                del self.hexagon_texts[hexagon]
        else:
            # Спрашиваем у пользователя текст для добавления
            text = tk.simpledialog.askstring("Добавить текст", "Введите текст для шестигранника:")
            if text:
                # Вычисляем позицию для текста вне шестигранника
                direction = np.array([event_point[0], event_point[1]]) - np.array([0, 0])
                norm_direction = direction / np.linalg.norm(direction)

                # Вычисляем максимальное расстояние от центра до края фигуры
                max_distance = self.num_rings * self.radius * 2 + self.padding

                # Вычисляем позицию текста на этом максимальном расстоянии в направлении клика
                text_position = np.array([0, 0]) + norm_direction * max_distance

                # Добавляем аннотацию со стрелкой
                annotation = self.fig.axes[0].annotate(
                    text,
                    xy=(event_point[0], event_point[1]),  # координаты, куда указывает стрелка
                    xytext=text_position,  # координаты текста
                    size=10,
                    ha='center',
                    va='center',
                    arrowprops=dict(facecolor='black', arrowstyle='->', lw=0.5)
                )
                self.hexagon_texts[hexagon] = annotation

    def prompt_num_rings(self):
        num_rings = tk.simpledialog.askinteger("Изменить количество колец",
                                               f"Введите количество колец"
                                               f" ({self.min_rings}-{self.max_rings}):",
                                               minvalue=self.min_rings, maxvalue=self.max_rings)
        if num_rings is not None:
            self.num_rings = num_rings
            self.color_map = {}
            self.update_hexagon_chart()

    def add_ring(self):
        """Добавляем внешний слой."""
        if self.num_rings >= self.max_rings:
            messagebox.showerror('Ошибка', f'Количество колец не может быть больше {self.max_rings}')
            return
        self.num_rings += 1
        self.color_map = {}
        self.update_hexagon_chart()

    def remove_ring(self):
        """Удаляем внешний слой, если он существует."""
        if self.num_rings <= self.min_rings:
            messagebox.showerror('Ошибка', f'Количество колец не может быть меньше {self.min_rings}')
            return
        if self.num_rings > 1:
            self.num_rings -= 1
            self.color_map = {}
            self.update_hexagon_chart()

    def increase_padding(self):
        """
        Увеличение расстояния между шестигранниками
        """
        self.coeff_padding *= STEP_PADDING
        self.update_hexagon_chart()

    def decrease_padding(self):
        """
        Уменьшение расстояния между шестигранниками
        """
        self.coeff_padding /= STEP_PADDING
        self.update_hexagon_chart()

    def find_closest_hexagon(self, x, y):
        min_dist = float('inf')
        closest_hexagon = None
        for hexagon in self.hexagon_patches:
            dist = np.sqrt((x - hexagon.get_xy()[:, 0]) ** 2 + (y - hexagon.get_xy()[:, 1]) ** 2)
            if dist.min() < min_dist:
                min_dist = dist.min()
                closest_hexagon = hexagon
        return closest_hexagon

    def update_legend(self):
        total_count, color_count, color_names = self.count_hexagons_by_color()
        legend_text = [f"Всего {total_count} элементов"]

        if self.bw_mode.get():
            for color, count in color_count.items():
                legend_text.append(f"{color} "
                                   f"({self.color_titles.get(key_by_value(COLOR_TO_HATCH, color), '')}"
                                   f"): {count}")
        else:
            for color, count in color_count.items():
                legend_text.append(f"{color} ({self.color_titles.get(color, '')}): {count}")

        # Удаление старой легенды (если она существует) и добавление новой:
        if hasattr(self, 'legend_text_element'):
            self.legend_text_element.remove()
        self.legend_text_element = self.fig.text(0.85, 0.2, '\n'.join(legend_text), fontsize=12,
                                                 verticalalignment='center')
        self.canvas.draw_idle()

    def on_click(self, event):
        # Получаем координаты точки нажатия
        x, y = event.xdata, event.ydata
        closest_hexagon = self.find_closest_hexagon(x, y)
        if x is not None and y is not None:
            if closest_hexagon:
                if self.adding_text:
                    self.add_text_to_hexagon(closest_hexagon, (x, y))
                elif self.adding_number:
                    self.add_number_to_hexagon(closest_hexagon)
                elif self.editing_color:
                    self.color_map[closest_hexagon] = self.selected_color
                    closest_hexagon.set_alpha(ALPHA)
                    if self.bw_mode.get():
                        closest_hexagon.set_hatch(self.color_to_hatch.get(self.selected_color, BASE_COLOR))
                    else:
                        closest_hexagon.set_facecolor(self.selected_color)
                elif self.editing_hexagon:
                    self.edit_hexagon(closest_hexagon)
                self.canvas.draw_idle()  # Обновляем отображение
                self.update_legend()

    def edit_hexagon(self, closest_hexagon):
        if closest_hexagon not in self.removed_hexagons and closest_hexagon not in self.dashed_hexagons:
            # Сначала делаем границу шестигранника прерывистой
            closest_hexagon.set_linestyle("--")
            self.dashed_hexagons.add(closest_hexagon)
        elif closest_hexagon in self.dashed_hexagons:
            # Если шестигранник уже имеет прерывистую линию, удаляем его
            closest_hexagon.set_visible(False)
            self.removed_hexagons.add(closest_hexagon)
            self.dashed_hexagons.remove(closest_hexagon)
        else:
            # Восстанавливаем шестигранник
            closest_hexagon.set_visible(True)
            closest_hexagon.set_linestyle("-")
            self.removed_hexagons.remove(closest_hexagon)

    def set_selected_color(self, color):
        self.selected_color = color
        for hexagon in self.hexagon_patches:
            self.original_colors[hexagon] = hexagon.get_facecolor()
        self.color_label.config(text="Текущий цвет: " + self.selected_color)

    def update_hexagon_chart(self):
        plt.close(self.fig)  # Закрыть текущую фигуру
        self.fig.clf()
        self.hexagon_patches = []  # Очищаем список элементов

        # Удаляем старый холст и панель инструментов
        self.canvas.get_tk_widget().pack_forget()
        self.canvas.get_tk_widget().destroy()  # Уничтожаем текущий виджет холста
        if self.toolbar:
            self.toolbar.destroy()

        self.canvas.get_tk_widget().destroy()

        self.fig = self.draw_hexagon_chart()  # Создаем новую фигуру

        self.canvas = self._create_canvas()  # Используем метод для создания нового холста и панели инструментов
        self.canvas.mpl_connect('button_press_event', self.on_click)
        self.canvas.mpl_connect('draw_event', self.update_text_size)
        # Обновляем область видимости для скроллинга
        self.canvas.get_tk_widget().configure(scrollregion=self.canvas.get_tk_widget().bbox(tk.ALL))

    def draw_hexagon_chart(self):
        origin = (0, 0)  # Стартовая точка
        base_radius = 100 / (1.5 * self.num_rings + 1)
        self.radius = base_radius  # Радиус шестигранников
        self.padding = base_radius * self.coeff_padding  # Расстояние между шестигранниками
        self.fig = self.draw_hex_grid(origin, self.num_rings, self.radius, self.padding)
        if self.canvas:
            self.update_legend()
        return self.fig

    def draw_hex(self, ax, x, y, size):
        angle = 2 * np.pi / NUM_SIDES_HEXAGON
        x_coords = [x + size * math.cos(angle * i) for i in range(NUM_SIDES_HEXAGON)]
        y_coords = [y + size * math.sin(angle * i) for i in range(NUM_SIDES_HEXAGON)]
        hexagon = plt.Polygon(np.column_stack((x_coords, y_coords)), edgecolor='black', facecolor=BASE_COLOR)
        hexagon.set_alpha(ALPHA)
        # Если шестигранник уже был окрашен, применяем предыдущий цвет:
        if hexagon in self.color_map:
            hexagon.set_facecolor(self.color_map[hexagon])
        self.patches.append(hexagon)
        self.hexagon_patches.append(hexagon)
        ax.add_patch(hexagon)

    def draw_hex_grid(self, origin, num_rings, radius, padding):
        """
        Рисование сетки шестигранников
        :param origin:    Центр для сетки
        :param num_rings: Кольца
        :param radius:    Радиус одного шестигранника
        :param padding:   Отступ между шестигранниками
        :return:
        """
        self.patches = []  # Список для хранения кругов
        fig = Figure(figsize=FIGSIZE)
        ax = fig.add_subplot(111)

        ax.set_aspect(1, 'box')  # Оставим такой тип, т.к. он не растягивает фигуру при приближении

        # При желании можно поиграться с этими стилями
        # ax.set_aspect('equal', 'box')
        # ax.set_aspect(1, adjustable='datalim')
        ang60 = math.radians(60)
        x_off = 1.5 * (radius + padding)
        y_off = math.sqrt(3) * (radius + padding)

        x_center, y_center = origin

        for ring in range(num_rings):
            for i in range(6):
                for j in range(ring):
                    if self.remove_corners.get() and is_corner_hexagon(i, j, num_rings, ring):
                        continue
                    angle = i * ang60
                    x_shift = j * x_off * math.cos(angle + ang60) + (ring - j) * x_off * math.cos(angle)
                    y_shift = j * y_off * math.sin(angle + ang60) + (ring - j) * y_off * math.sin(angle)

                    x = x_center + x_shift
                    y = y_center + y_shift

                    self.draw_hex(ax, y, x, radius)


        # Центр шестигранника
        if num_rings > 0:
            self.draw_hex(ax, x_center, y_center, radius)

        ax.set_xlim(-x_off * self.num_rings * 2.5, x_off * self.num_rings * 2.5)
        ax.set_ylim(-y_off * self.num_rings, y_off * self.num_rings)
        # ax.set_autoscale_on(False)
        # ax.set_axis_off()
        ax.xaxis.set_major_locator(plt.NullLocator())
        ax.yaxis.set_major_locator(plt.NullLocator())
        self.initial_xlim = ax.get_xlim()
        fig.tight_layout()
        return fig

    def count_hexagons_by_color(self):
        color_count = {}
        color_names = {}
        total_count = 0

        if self.bw_mode.get():
            for hexagon in self.hexagon_patches:
                if hexagon not in self.removed_hexagons:  # Не учитываем удаленные шестигранники
                    color = hexagon.get_hatch()
                    color_count[color] = color_count.get(color, 0) + 1
                    if hexagon in self.color_map:
                        color_names[color] = self.color_map[hexagon]
                    total_count += 1
                    if hexagon in self.dashed_hexagons:
                        hexagon.set_linestyle("--")
        else:
            for hexagon in self.hexagon_patches:
                if hexagon not in self.removed_hexagons:  # Не учитываем удаленные шестигранники
                    color = hexagon.get_facecolor()
                    color = mpl.colors.to_hex(color)      # Преобразование цвета к шестнадцатеричному формату
                    color = hex_to_name(color)            # Получаем имя цвета
                    color_count[color] = color_count.get(color, 0) + 1
                    color_names[color] = self.color_map.get(hexagon, BASE_COLOR)
                    total_count += 1
                    if hexagon in self.dashed_hexagons:
                        hexagon.set_linestyle("--")

        return total_count, color_count, color_names

    def save_fig(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".pkl", filetypes=[("Pickle файлы", "*.pkl")])
        if file_path:
            with open(file_path, 'wb') as f:
                if hasattr(self, 'legend_text_element'):
                    self.legend_text_element.remove()
                # Сохраняем все атрибуты класса, чтобы могли потом изменять фигуру
                attributes_to_save = {
                    "color_map": self.color_map,
                    "num_rings": self.num_rings,
                    "padding": self.padding,
                    "hexagon_patches": self.hexagon_patches,
                    "selected_color": self.selected_color,
                    "removed_hexagons": self.removed_hexagons,
                    "remove_corners": self.remove_corners.get(),
                    "hexagon_numbers": self.hexagon_numbers,
                    "hexagon_texts": self.hexagon_texts,
                    "scale_factor": self.scale_factor,
                    "initial_xlim": self.initial_xlim,
                    "fig": self.fig
                }
                pickle.dump(attributes_to_save, f)
                self.update_legend()

    def load_fig(self):
        file_path = filedialog.askopenfilename(defaultextension=".pkl", filetypes=[("Pickle файлы", "*.pkl")])
        if file_path:
            with open(file_path, 'rb') as file:
                loaded_attributes = pickle.load(file)

            # Закрыть текущую фигуру и очистить холст
            plt.close(self.fig)
            self.canvas.get_tk_widget().pack_forget()
            self.canvas.get_tk_widget().destroy()
            if self.toolbar:
                self.toolbar.destroy()

            # Восстанавливаем атрибуты
            self.color_map = loaded_attributes["color_map"]
            self.num_rings = loaded_attributes["num_rings"]
            self.hexagon_patches = loaded_attributes["hexagon_patches"]
            self.selected_color = loaded_attributes["selected_color"]
            self.remove_corners.set(loaded_attributes["remove_corners"])
            self.hexagon_numbers = loaded_attributes["hexagon_numbers"]
            self.hexagon_texts = loaded_attributes["hexagon_texts"]
            self.fig = loaded_attributes["fig"]
            self.scale_factor = loaded_attributes["scale_factor"]

            # Для поддержания старых картограм
            try:
                self.padding = loaded_attributes["padding"]
            except:
                self.padding = 0.4
            try:
                self.removed_hexagons = loaded_attributes["removed_hexagons"]
            except:
                self.removed_hexagons = None
            try:
                self.initial_xlim = loaded_attributes["initial_xlim"]
            except:
                self.initial_xlim = None
            # Пересоздаем холст и обновляем его содержимое
            self.canvas = self._create_canvas()
            self.canvas.mpl_connect('button_press_event', self.on_click)
            self.canvas.mpl_connect('draw_event', self.update_text_size)
            self.canvas.draw()
            self.update_legend()


root = tk.Tk()
app = HexagonChartApp(root)
root.state('zoomed')
root.mainloop()
