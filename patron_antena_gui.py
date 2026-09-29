import sys
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QTextEdit, QLabel, QPushButton, QComboBox, QFileDialog, QGroupBox, QMessageBox
)
from PyQt5.QtCore import Qt


class MplCanvas(FigureCanvas):
    def __init__(self, parent=None, width=6, height=6, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.ax = self.fig.add_subplot(111, projection='polar')
        super(MplCanvas, self).__init__(self.fig)
        
        # Orientar 0° al Norte y giro en sentido horario
        self.ax.set_theta_zero_location('N')
        self.ax.set_theta_direction(-1)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Analizador de Patrón de Radiación - Antenna Viewer")
        self.resize(1100, 700)

        # Widget Principal
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)

        # ==========================================
        # PANEL IZQUIERDO: Controles e Ingreso de Datos
        # ==========================================
        left_panel = QVBoxLayout()
        
        # Configuración del barrido
        config_box = QGroupBox("Configuración de Barrido")
        config_layout = QVBoxLayout()
        
        self.combo_paso = QComboBox()
        self.combo_paso.addItems(["Pasos de 10° (36 lecturas)", "Pasos de 5° (72 lecturas)", "Pasos de 15° (24 lecturas)"])
        self.combo_paso.currentIndexChanged.connect(self.actualizar_grafico)
        config_layout.addWidget(QLabel("Resolución angular:"))
        config_layout.addWidget(self.combo_paso)
        config_box.setLayout(config_layout)
        left_panel.addWidget(config_box)

        # Campo de texto para valores dBm
        left_panel.addWidget(QLabel("Valores en dBm (un número por línea, de 0° en adelante):"))
        self.txt_datos = QTextEdit()
        self.txt_datos.setPlaceholderText("-40.5\n-42.0\n-45.1\n-50.2\n...")
        self.txt_datos.textChanged.connect(self.actualizar_grafico)
        left_panel.addWidget(self.txt_datos)

        # Cargar ejemplo por defecto
        btn_ejemplo = QPushButton("Cargar Datos de Ejemplo")
        btn_ejemplo.clicked.connect(self.cargar_ejemplo)
        left_panel.addWidget(btn_ejemplo)

        # Botones de Exportación
        btn_guardar_img = QPushButton("💾 Guardar Gráfica (PNG)")
        btn_guardar_img.clicked.connect(self.guardar_imagen)
        left_panel.addWidget(btn_guardar_img)

        btn_guardar_csv = QPushButton("📄 Exportar Datos (CSV)")
        btn_guardar_csv.clicked.connect(self.guardar_csv)
        left_panel.addWidget(btn_guardar_csv)

        # Ancho fijo para el panel izquierdo
        left_container = QWidget()
        left_container.setLayout(left_panel)
        left_container.setFixedWidth(320)
        main_layout.addWidget(left_container)

        # ==========================================
        # PANEL DERECHO: Canvas Polar de Matplotlib
        # ==========================================
        self.canvas = MplCanvas(self, width=6, height=6, dpi=100)
        main_layout.addWidget(self.canvas, stretch=1)

        # Dibujar gráfico vacío inicial
        self.actualizar_grafico()

    def obtener_paso_angular(self):
        idx = self.combo_paso.currentIndex()
        if idx == 0:
            return 10.0
        elif idx == 1:
            return 5.0
        else:
            return 15.0

    def actualizar_grafico(self):
        paso = self.obtener_paso_angular()
        texto = self.txt_datos.toPlainText()
        lineas = texto.strip().split('\n')

        valores_dbm = []
        for l in lineas:
            l = l.strip()
            if l:
                try:
                    v = float(l.replace(',', '.'))
                    valores_dbm.append(v)
                except ValueError:
                    pass  # Ignorar líneas inválidas o texto mientras se escribe

        # Limpiar gráfico
        ax = self.canvas.ax
        ax.clear()
        ax.set_theta_zero_location('N')
        ax.set_theta_direction(-1)
        ax.grid(True, linestyle='--', alpha=0.7)

        if not valores_dbm:
            ax.set_title("Patrón de Radiación (Ingrese datos a la izquierda)", va='bottom', fontsize=12)
            self.canvas.draw()
            return

        num_lecturas = len(valores_dbm)
        angulos_deg = np.array([i * paso for i in range(num_lecturas)])
        angulos_rad = np.deg2rad(angulos_deg)
        valores_arr = np.array(valores_dbm)

        # Ajuste de límites dinámicos
        max_db = np.max(valores_arr)
        min_db = np.min(valores_arr) - 5
        ax.set_rlim(min_db, max_db + 2)

        # Si se completó la vuelta (360° o más), cerrar el polígono
        puntos_vuelta = int(360.0 / paso)
        if num_lecturas >= puntos_vuelta:
            ang_cierre = np.append(angulos_rad[:puntos_vuelta], angulos_rad[0])
            val_cierre = np.append(valores_arr[:puntos_vuelta], valores_arr[0])
            ax.plot(ang_cierre, val_cierre, 'b-', linewidth=2, label='Patrón CERRADO')
            ax.fill(ang_cierre, val_cierre, color='blue', alpha=0.15)
        else:
            ax.plot(angulos_rad, valores_arr, 'ro-', linewidth=2, markersize=5, label='Lecturas en progreso')

        progres = min(num_lecturas * paso, 360.0)
        ax.set_title(f"Patrón de Radiación - Progreso: {progres:.0f}° / 360° ({num_lecturas} pts)", va='bottom', fontsize=12)
        ax.legend(loc='lower right', bbox_to_anchor=(1.25, 0.0))

        self.canvas.draw()

    def cargar_ejemplo(self):
        # Generar un patrón cardioide direccional de ejemplo
        paso = self.obtener_paso_angular()
        num_puntos = int(360.0 / paso)
        angulos = np.linspace(0, 2*np.pi, num_puntos, endpoint=False)
        
        # Lóbulo direccional simulado hacia el Norte
        patron_dbm = -40 + 15 * np.cos(angulos) + np.random.normal(0, 0.5, num_puntos)
        
        texto_ejemplo = "\n".join([f"{v:.1f}" for v in patron_dbm])
        self.txt_datos.setPlainText(texto_ejemplo)

    def guardar_imagen(self):
        filename, _ = QFileDialog.getSaveFileName(self, "Guardar Gráfico", "", "Imagen PNG (*.png);;Todos los archivos (*)")
        if filename:
            self.canvas.fig.savefig(filename, dpi=300, bbox_inches='tight')
            QMessageBox.information(self, "Éxito", f"Gráfico guardado correctamente en:\n{filename}")

    def guardar_csv(self):
        filename, _ = QFileDialog.getSaveFileName(self, "Exportar a CSV", "", "Archivo CSV (*.csv);;Todos los archivos (*)")
        if filename:
            paso = self.obtener_paso_angular()
            texto = self.txt_datos.toPlainText()
            lineas = texto.strip().split('\n')
            
            with open(filename, 'w') as f:
                f.write("Angulo_deg,Potencia_dBm\n")
                for i, l in enumerate(lineas):
                    l = l.strip()
                    if l:
                        try:
                            v = float(l.replace(',', '.'))
                            f.write(f"{i*paso:.1f},{v:.2f}\n")
                        except ValueError:
                            pass
            QMessageBox.information(self, "Éxito", f"Datos CSV exportados en:\n{filename}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())