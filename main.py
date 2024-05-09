from PIL import Image, ImageEnhance
import numpy as np
import tkinter as tk
from tkinter import filedialog, Scale, HORIZONTAL
from scipy.spatial import cKDTree

def hex_to_rgb(hex_color):
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def replace_colors(image_path, palette, weight=0.5, enhance = 2, back_enhance = 2, saturation = 1, gamma = 1, back_gamma = 1, back_saturation = 1):
    img = Image.open(image_path)
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(enhance)  # Увеличиваем контрастность
    enhancer = ImageEnhance.Color(img)
    img = enhancer.enhance(saturation)  # Регулируем насыщенность
    img = img.point(lambda p: p ** gamma)  # Регулируем гамму
    img_array = np.array(img)
    rgb_array = img_array[:, :, :3]  # Извлекаем RGB каналы
    alpha_array = img_array[:, :, 3] if img_array.shape[2] == 4 else None  # Извлекаем альфа-канал, если он есть
    palette = cKDTree(palette)

    # Преобразуем изображение в одномерный массив
    reshaped_img = rgb_array.reshape(-1, rgb_array.shape[-1])

    # Находим ближайший цвет в палитре для каждого пикселя
    dist, indices = palette.query(reshaped_img)

    # Заменяем цвета пикселей на ближайшие цвета палитры
    new_colors = palette.data[indices]
    final_colors = reshaped_img * (1 - weight) + new_colors * weight
    final_colors = np.clip(final_colors, 0, 255).astype(int)

    # Возвращаем изображение к его исходной форме
    new_rgb_array = final_colors.reshape(rgb_array.shape)
    if alpha_array is not None:
        new_img_array = np.dstack((new_rgb_array, alpha_array))  # Объединяем RGB и альфа-каналы
        new_img = Image.fromarray(new_img_array.astype('uint8'), 'RGBA')
    else:
        new_img = Image.fromarray(new_rgb_array.astype('uint8'), 'RGB')

    # Восстанавливаем контрастность, гамму и насыщенность
    enhancer = ImageEnhance.Contrast(new_img)
    new_img = enhancer.enhance(1 / back_enhance)
    enhancer = ImageEnhance.Color(new_img)
    new_img = enhancer.enhance(back_saturation)
    new_img = new_img.point(lambda p: p ** (1 / back_gamma))
    new_img.show()

def convert_image():
    palette_hex = palette_entry.get("1.0", tk.END).split(',')
    palette = [hex_to_rgb(color.lstrip('#')) for color in palette_hex]
    image_path = filedialog.askopenfilename()
    if image_path:
        weight = weight_scale.get()
        enhance = enhance_scale.get()
        back_enhance = back_enhance_scale.get()
        saturation = saturation_scale.get()
        gamma = gamma_scale.get()
        back_gamma = back_gamma_scale.get()
        back_saturation = back_saturation_scale.get()
        replace_colors(image_path, palette, weight, enhance, back_enhance, saturation, gamma, back_gamma, back_saturation)

def show_context_menu(event):
    context_menu.tk_popup(event.x_root, event.y_root)

root = tk.Tk()
root.geometry('400x600')

palette_label = tk.Label(root, text='Введите цвета палитры через запятую, без пробелов')
palette_label.pack()

example_label = tk.Label(root, text='Пример: #FFE5EC,#FFC2D1,#FFB3C6,#FF8FAB,#FB6F92')
example_label.pack()

palette_entry = tk.Text(root, height=3, width=40)
palette_entry.pack()

# Создаем контекстное меню
context_menu = tk.Menu(root, tearoff=0)
context_menu.add_command(label="Вставить", command=lambda: palette_entry.event_generate('<<Paste>>'))

# Привязываем контекстное меню к текстовому полю
palette_entry.bind("<Button-3>", show_context_menu)

# Добавляем ползунки и кнопки для настройки параметров
weight_label = tk.Label(root, text='Weight')
weight_label.pack()
weight_scale = Scale(root, from_=0, to=1, resolution=0.01, orient=HORIZONTAL)
weight_scale.set(0.5)
weight_scale.pack()

enhance_label = tk.Label(root, text='Enhance')
enhance_label.pack()
enhance_scale = Scale(root, from_=0.5, to=4, resolution=0.1, orient=HORIZONTAL)
enhance_scale.set(1)
enhance_scale.pack()

back_enhance_label = tk.Label(root, text='Back Enhance')
back_enhance_label.pack()
back_enhance_scale = Scale(root, from_=0.5, to=2, resolution=0.1, orient=HORIZONTAL)
back_enhance_scale.set(1)
back_enhance_scale.pack()

saturation_label = tk.Label(root, text='Saturation')
saturation_label.pack()
saturation_scale = Scale(root, from_=0.1, to=4, resolution=0.1, orient=HORIZONTAL)
saturation_scale.set(1)
saturation_scale.pack()

back_saturation_label = tk.Label(root, text='Back Saturation')
back_saturation_label.pack()
back_saturation_scale = Scale(root, from_=0.2, to=2, resolution=0.1, orient=HORIZONTAL)
back_saturation_scale.set(1)
back_saturation_scale.pack()

gamma_label = tk.Label(root, text='Gamma')
gamma_label.pack()
gamma_scale = Scale(root, from_=0.7, to=1.3, resolution=0.1, orient=HORIZONTAL)
gamma_scale.set(1)
gamma_scale.pack()

back_gamma_label = tk.Label(root, text='Back Gamma')
back_gamma_label.pack()
back_gamma_scale = Scale(root, from_=0.7, to=1.3, resolution=0.1, orient=HORIZONTAL)
back_gamma_scale.set(1)
back_gamma_scale.pack()

convert_button = tk.Button(root, text='Запустить конвертацию', command=convert_image)
convert_button.pack()

root.mainloop()