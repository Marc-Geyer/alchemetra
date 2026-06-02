
from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton

import sys

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Alchemetra")
        self.setMinimumSize(800, 600)

        button = QPushButton("Start", self)

        self.setCentralWidget(button)

def start_up(name):
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    app.exec()

if __name__ == '__main__':
    start_up('Alchemetra')

