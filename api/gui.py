from PySide6 import QtCore, QtWidgets, QtGui
import random, sys
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from threading import Thread

def version_enter_point(version: str):
    print(f"Entering version: {version}")

class MyWidget(QtWidgets.QMainWindow):
	def __init__(self, versions: list[str]):
		super().__init__()

		self.versions = versions
		self.version = ""

		self.combo = QtWidgets.QComboBox()
		self.combo.setStyleSheet("border-radius: 5px; background-color: lightblue;")
		self.combo.addItems(self.versions)


		self.widget = QtWidgets.QWidget()
		self.sub_layout = QtWidgets.QHBoxLayout(self.widget)


		self.button = QtWidgets.QPushButton("Start")
		self.button.setMinimumHeight(20)
		self.button.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
		self.sub_layout.addWidget(self.button)
		self.button.setStyleSheet("QPushButton {"
"  background-color: #0088ff;"
"  border-radius: 8px;"
"  color: white;"
"  font-size: 20px;"
"}"
""
"QPushButton:hover {"
"  background-color: #339fff;"
"}"
""
"QPushButton:pressed {"
"  background-color: #006fcc;"
"}")

		self.settings_button = QtWidgets.QPushButton("S")
		self.settings_button.setMaximumWidth(20)
		self.settings_button.setMinimumHeight(20)
		self.settings_button.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
		self.sub_layout.addWidget(self.settings_button)
		self.settings_button.setStyleSheet("border-radius: 5px; background-color: lightblue;")
		self.widget.setLayout(self.sub_layout)


		self.text = QtWidgets.QLabel("Hello World", alignment=QtCore.Qt.AlignCenter)
		self.progress = QtWidgets.QProgressBar()
		self.progress.setStyleSheet("border-radius: 5px; background-color: lightblue;")

		central_widget = QtWidgets.QWidget()
		self.setCentralWidget(central_widget)
		self.layout = QtWidgets.QVBoxLayout(central_widget)

		self.layout.addWidget(self.combo)
		self.layout.addWidget(self.text)
		self.layout.addWidget(self.widget, 0, QtCore.Qt.AlignBottom)
		self.layout.addWidget(self.progress)

		self.button.clicked.connect(self.magic)
		self.combo.currentTextChanged.connect(self.magic)
		self.settings_button.clicked.connect(self.settings)

	@QtCore.Slot()
	def magic(self):
		self.progress.setValue(0)
		self.text.setText(self.combo.currentText())
		self.version = self.combo.currentText()

		for i in range(101):
			self.progress.setValue(i)
			#QtCore.QThread.sleep(1)

	@QtCore.Slot()
	def start(self):
		version_enter_point(self.version)

	@QtCore.Slot()
	def add_item(self):
		text, ok = QtWidgets.QInputDialog.getText(self, "Добавить вариант", "Введите новый вариант:")
		if ok and text:
			self.combo.addItem(text)
	
	# Settings of launcher
	@QtCore.Slot()
	def settings(self):
		text, ok = QtWidgets.QInputDialog.getText(self, "Настройки", "Введите настройки:")
		if ok and text:
			print("Настройки:", text)

def open_gui(versions, width: int = 800, height: int = 600):
	
	app = QtWidgets.QApplication([])
	widget = MyWidget(versions)
	widget.resize(width, height)
	widget.show()

	sys.exit(app.exec())

if __name__ == "__main__":
	open_gui(["1.12.2", "1.13", "1.18.2", "1.21.8"], 800, 600)