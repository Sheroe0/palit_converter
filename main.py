from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFileDialog, QLabel, QSlider, \
    QSpinBox, QTextEdit
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import Qt, QTimer
from PIL import Image, ImageEnhance
import numpy as np
from scipy.spatial import cKDTree
import io
import threading
import re


def hex_to_rgb(hex_color):
    return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))


def replace_colors(image_path, palette, weight=0.5, enhance=2, back_enhance=2, saturation=1, gamma=1, back_gamma=1,
                   back_saturation=1):
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

    return new_img


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.image_path = ""
        self.compare_image_path = ""
        self.converted_image = None
        self.layout = QHBoxLayout()  # Используем горизонтальный макет
        self.setLayout(self.layout)

        self.controls_layout = QVBoxLayout()  # Вертикальный макет для элементов управления
        self.layout.addLayout(self.controls_layout)

        self.select_button = QPushButton('Выберите изображение')
        self.select_button.clicked.connect(self.select_image)
        self.controls_layout.addWidget(self.select_button)

        self.select_compare_button = QPushButton('Выберите изображение для сравнения')
        self.select_compare_button.clicked.connect(self.select_compare_image)
        self.controls_layout.addWidget(self.select_compare_button)

        self.instructions_label = QLabel("Введите цвета в формате HEX (например, #FFFFFF) в поле ввода ниже.\n"
                                         "Вы можете ввести несколько цветов, разделив их запятой, решеткой или пробелом.")
        self.controls_layout.addWidget(self.instructions_label)

        self.palette_entry = QTextEdit()
        self.controls_layout.addWidget(self.palette_entry)

        self.save_button = QPushButton('Сохранить картинку')
        self.save_button.clicked.connect(self.save_image)
        self.controls_layout.addWidget(self.save_button)

        self.weight_slider = self.create_slider('Weight')
        self.enhance_slider = self.create_slider('Enhance')
        self.back_enhance_slider = self.create_slider('Back Enhance')
        self.saturation_slider = self.create_slider('Saturation')
        self.back_saturation_slider = self.create_slider('Back Saturation')
        self.gamma_slider = self.create_slider('Gamma')
        self.back_gamma_slider = self.create_slider('Back Gamma')

        self.preview_layout = QVBoxLayout()  # Вертикальный макет для превью изображения и статуса
        self.layout.addLayout(self.preview_layout)

        self.image_status = QLabel("Выберите изображение")
        self.preview_layout.addWidget(self.image_status)

        self.youtube_link = QLabel()
        self.youtube_link.setText(
            "<a href='https://www.youtube.com/channel/UC9eLWczxGDfHbRU2nE4FODA'>Мой YouTube канал</a>")
        self.youtube_link.setTextInteractionFlags(Qt.TextBrowserInteraction)
        self.youtube_link.setOpenExternalLinks(True)
        self.preview_layout.addWidget(self.youtube_link)

        self.image_label = QLabel()
        self.image_label.setFixedSize(600, 600)
        self.preview_layout.addWidget(self.image_label)

        self.compare_layout = QVBoxLayout()  # Вертикальный макет для превью изображения для сравнения
        self.layout.addLayout(self.compare_layout)

        self.Vimage_status = QLabel("Тут оригинал изображения для сравнения")
        self.compare_layout.addWidget(self.Vimage_status)

        self.Vyoutube_link = QLabel()
        self.Vyoutube_link.setText(
            "<a href='https://youtu.be/aMgwrs-ej0o'>Видео гайд</a>")
        self.Vyoutube_link.setTextInteractionFlags(Qt.TextBrowserInteraction)
        self.Vyoutube_link.setOpenExternalLinks(True)
        self.compare_layout.addWidget(self.Vyoutube_link)

        self.compare_image_label = QLabel()
        self.compare_image_label.setFixedSize(600, 600)
        self.compare_layout.addWidget(self.compare_image_label)

        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.update_image)

    def create_slider(self, name):
        label = QLabel(name)
        self.controls_layout.addWidget(label)

        slider = QSlider(Qt.Horizontal)
        slider.setMinimum(1)
        slider.setMaximum(100)
        slider.setValue(50)
        slider.valueChanged.connect(lambda: spinbox.setValue(slider.value()))
        slider.valueChanged.connect(self.start_timer)
        self.controls_layout.addWidget(slider)

        spinbox = QSpinBox()
        spinbox.setMinimum(1)
        spinbox.setMaximum(100)
        spinbox.setValue(50)
        spinbox.valueChanged.connect(lambda: slider.setValue(spinbox.value()))
        self.controls_layout.addWidget(spinbox)

        return slider

    def select_image(self):
        self.image_path, _ = QFileDialog.getOpenFileName()
        pixmap = QPixmap(self.image_path)
        pixmap = pixmap.scaled(600, 600, Qt.KeepAspectRatio)
        self.image_label.setPixmap(pixmap)
        self.image_label.setText("")
        self.weight_slider.setValue(1)  # Устанавливаем значение ползунка weight в 1
        self.compare_image_path = self.image_path  # Копируем изображение для сравнения
        compare_pixmap = QPixmap(self.compare_image_path)
        compare_pixmap = compare_pixmap.scaled(600, 600, Qt.KeepAspectRatio)
        self.compare_image_label.setPixmap(compare_pixmap)

    def select_compare_image(self):
        self.compare_image_path, _ = QFileDialog.getOpenFileName()
        compare_pixmap = QPixmap(self.compare_image_path)
        compare_pixmap = compare_pixmap.scaled(600, 600, Qt.KeepAspectRatio)
        self.compare_image_label.setPixmap(compare_pixmap)

    def convert_image(self):
        if self.image_path:
            self.image_status.setText("Изменяется")
            palette_hex = re.findall(r'([a-fA-F0-9]{6})', self.palette_entry.toPlainText())
            if not palette_hex:  # Проверяем, пуста ли палитра
                self.image_status.setText("Палитра пуста. Обработка изображения не запускается.")
                return
            palette = [hex_to_rgb(color) for color in palette_hex]
            weight = self.weight_slider.value() / 100
            enhance = self.enhance_slider.value() / 50
            back_enhance = self.back_enhance_slider.value() / 50
            saturation = self.saturation_slider.value() / 50
            gamma = self.gamma_slider.value() / 50
            back_gamma = self.back_gamma_slider.value() / 50
            back_saturation = self.back_saturation_slider.value() / 50 #тут при слишком низких значениях ошибка. не крашится = пофиг
            self.converted_image = replace_colors(self.image_path, palette, weight, enhance, back_enhance, saturation,
                                                  gamma,
                                                  back_gamma, back_saturation)

            # Convert PIL Image to QPixmap and display it
            data = io.BytesIO()
            self.converted_image.save(data, format='PNG')
            data.seek(0)
            qimg = QImage.fromData(data.read())
            pixmap = QPixmap.fromImage(qimg)
            pixmap = pixmap.scaled(600, 600, Qt.KeepAspectRatio)
            self.image_label.setPixmap(pixmap)
            self.image_status.setText("Готово")

    def save_image(self):
        if self.image_path and self.converted_image:
            save_path, _ = QFileDialog.getSaveFileName()
            if save_path:
                if not save_path.endswith('.png'):
                    save_path += '.png'
                self.converted_image.save(save_path, 'PNG')

    def start_timer(self):
        self.timer.start(500)  # Запускаем таймер на 500 мс

    def update_image(self):
        threading.Thread(target=self.convert_image).start()

app = QApplication([])
window = MainWindow()
window.show()
app.exec_()
