"""Editor SQL y vistas de análisis; solo Ejecutar puede modificar la base."""
import json
from pathlib import Path
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QAction, QCloseEvent
from PyQt6.QtWidgets import (QApplication,QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,
    QPlainTextEdit,QPushButton,QTabWidget,QTableWidget,QTableWidgetItem,QTreeWidget,
    QTreeWidgetItem,QFileDialog,QMessageBox,QLineEdit,QLabel,QComboBox,QSplitter)
from .api import analyze_sql,execute_sql
from .cli import serialize
from .storage import FileStorage
from .file_io import atomic_write_text


class SqlWorker(QThread):
    completed = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self,source,database,execute,revision,path):
        super().__init__()
        self.source,self.database,self.execute,self.revision,self.path = source,database,execute,revision,path

    def run(self):
        try:
            store = FileStorage(self.database)
            result = execute_sql(self.source,store,self.path) if self.execute else analyze_sql(self.source,store.catalog,self.path,storage=store)
            self.completed.emit(result)
        except Exception as exc:
            self.failed.emit(f'{type(exc).__name__}: {exc}')


class MainWindow(QMainWindow):
    def __init__(self,database='database'):
        super().__init__()
        self.setWindowTitle('Intérprete SQL • Archivos')
        self.resize(1200,850)
        self.path = None
        self.worker = None
        self.outputs = []
        self.revision = 0
        central = QWidget()
        layout = QVBoxLayout(central)
        self.setCentralWidget(central)
        controls = QHBoxLayout()
        controls.addWidget(QLabel('Base de datos:'))
        self.database = QLineEdit(str(database))
        controls.addWidget(self.database)
        choose = QPushButton('Carpeta…')
        choose.clicked.connect(self.choose_database)
        controls.addWidget(choose)
        self.analyze_button = QPushButton('Analizar')
        self.execute_button = QPushButton('Ejecutar')
        self.analyze_button.clicked.connect(self.start_analysis)
        self.execute_button.clicked.connect(self.start_execution)
        controls.addWidget(self.analyze_button)
        controls.addWidget(self.execute_button)
        layout.addLayout(controls)
        self.editor = QPlainTextEdit()
        self.editor.setPlaceholderText('SELECT nombre FROM estudiantes WHERE edad >= 18;')
        self.editor.setStyleSheet('font-family: Consolas; font-size: 14px;')
        self.editor.textChanged.connect(self.changed)
        split = QSplitter()
        from PyQt6.QtCore import Qt
        split.setOrientation(Qt.Orientation.Vertical)
        split.addWidget(self.editor)
        self.tabs = QTabWidget()
        self.tokens = QTableWidget(0,4)
        self.tokens.setHorizontalHeaderLabels(['Token','Texto','Línea','Columna'])
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(['Árbol sintáctico'])
        self.ast_tree = QTreeWidget()
        self.ast_tree.setHeaderLabels(['AST SQL'])
        self.errors = QTableWidget(0,4)
        self.errors.setHorizontalHeaderLabels(['Etapa','Línea','Columna','Mensaje'])
        self.errors.cellDoubleClicked.connect(self.go_to_error)
        self.results = QTableWidget()
        result_panel = QWidget()
        result_layout = QVBoxLayout(result_panel)
        self.result_selector = QComboBox()
        self.result_selector.currentIndexChanged.connect(self.show_output)
        result_layout.addWidget(self.result_selector)
        result_layout.addWidget(self.results)
        for title,view in [('Tokens',self.tokens),('Árbol sintáctico',self.tree),('AST',self.ast_tree),('Errores',self.errors),('Resultados',result_panel)]:
            self.tabs.addTab(view,title)
        split.addWidget(self.tabs)
        split.setSizes([350,450])
        layout.addWidget(split)
        menu = self.menuBar().addMenu('Archivo')
        for name,shortcut,handler in [('Nuevo','Ctrl+N',self.new_document),('Abrir…','Ctrl+O',self.open_document),('Guardar','Ctrl+S',self.save_document),('Guardar como…','Ctrl+Shift+S',self.save_as)]:
            action = QAction(name,self)
            action.setShortcut(shortcut)
            action.triggered.connect(handler)
            menu.addAction(action)
        self.statusBar().showMessage('Listo. Analizar no modifica el almacenamiento.')

    def changed(self):
        self.revision += 1

    def choose_database(self):
        selected = QFileDialog.getExistingDirectory(self,'Base de datos',self.database.text())
        if selected: self.database.setText(selected)

    def start_analysis(self): self.start(False)
    def start_execution(self): self.start(True)

    def start(self,execute):
        if self.worker is not None: return
        self.worker = SqlWorker(self.editor.toPlainText(),self.database.text(),execute,self.revision,self.path)
        self.worker.completed.connect(self.present)
        self.worker.failed.connect(self.worker_error)
        self.worker.finished.connect(self.finished)
        self.analyze_button.setEnabled(False)
        self.execute_button.setEnabled(False)
        self.database.setEnabled(False)
        self.statusBar().showMessage('Ejecutando…' if execute else 'Analizando…')
        self.worker.start()

    def finished(self):
        self.worker.deleteLater()
        self.worker = None
        self.analyze_button.setEnabled(True)
        self.execute_button.setEnabled(True)
        self.database.setEnabled(True)

    def worker_error(self,message):
        self.statusBar().showMessage(message)
        QMessageBox.critical(self,'Error',message)

    @staticmethod
    def fill(table,rows):
        table.setRowCount(len(rows))
        for r,row in enumerate(rows):
            for c,value in enumerate(row):
                table.setItem(r,c,QTableWidgetItem('NULL' if value is None else str(value)))
        table.resizeColumnsToContents()

    @staticmethod
    def add_object(parent,name,value):
        item = QTreeWidgetItem([name])
        parent.addTopLevelItem(item) if isinstance(parent,QTreeWidget) else parent.addChild(item)
        if isinstance(value,dict):
            for key,child in value.items(): MainWindow.add_object(item,key,child)
        elif isinstance(value,list):
            for i,child in enumerate(value): MainWindow.add_object(item,str(i),child)
        else: item.setText(0,f'{name}: {value}')

    def present(self,result):
        if self.worker.revision != self.revision:
            self.statusBar().showMessage('El documento cambió; vuelva a analizar. La ejecución solicitada puede haber finalizado.')
            return
        self.fill(self.tokens,[(t.token_type,t.text,t.location.line,t.location.column) for t in result.syntax.tokens])
        self.tree.clear()
        def append(parent,node):
            item = QTreeWidgetItem([node.symbol])
            parent.addTopLevelItem(item) if isinstance(parent,QTreeWidget) else parent.addChild(item)
            for child in node.children: append(item,child)
        if result.syntax.tree: append(self.tree,result.syntax.tree)
        self.tree.expandToDepth(1)
        self.ast_tree.clear()
        if result.ast: self.add_object(self.ast_tree,'Script',serialize(result.ast))
        self.ast_tree.expandToDepth(2)
        self.fill(self.errors,[(d.stage,d.location.line,d.location.column,d.message) for d in result.diagnostics])
        self.outputs = result.results
        self.result_selector.clear()
        for i,output in enumerate(self.outputs): self.result_selector.addItem(f'{i+1}. {output.kind} — {len(output.rows) if output.kind == "select" else output.affected} filas')
        if self.outputs: self.result_selector.setCurrentIndex(len(self.outputs)-1)
        else: self.results.setRowCount(0)
        self.tabs.setCurrentIndex(3 if result.diagnostics else 4 if result.results else 2)
        self.statusBar().showMessage('Error: consulte la pestaña Errores' if result.diagnostics else 'Operación completada')

    def show_output(self,index):
        if index < 0 or index >= len(self.outputs): return
        output = self.outputs[index]
        self.results.setColumnCount(len(output.columns))
        self.results.setHorizontalHeaderLabels(output.columns)
        self.fill(self.results,output.rows)
        self.results.setToolTip(json.dumps(output.stats,ensure_ascii=False))

    def go_to_error(self,row,column):
        line = int(self.errors.item(row,1).text())
        col = int(self.errors.item(row,2).text())
        block = self.editor.document().findBlockByNumber(line-1)
        from PyQt6.QtGui import QTextCursor
        cursor = QTextCursor(block)
        cursor.setPosition(block.position()+col-1)
        self.editor.setTextCursor(cursor)
        self.editor.setFocus()

    def guard_document(self):
        if not self.editor.document().isModified(): return True
        choice = QMessageBox.question(self,'Cambios sin guardar','¿Guardar los cambios del documento?',QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel)
        if choice == QMessageBox.StandardButton.Cancel: return False
        return self.save_document() if choice == QMessageBox.StandardButton.Save else True

    def new_document(self):
        if self.guard_document():
            self.path = None
            self.editor.clear()
            self.editor.document().setModified(False)

    def open_document(self):
        selected,_ = QFileDialog.getOpenFileName(self,'Abrir SQL','','SQL (*.sql);;Todos (*)')
        if not selected or not self.guard_document(): return
        try: text = Path(selected).read_text(encoding='utf-8-sig')
        except (OSError,UnicodeError) as exc:
            QMessageBox.warning(self,'No se pudo abrir',str(exc))
            return
        self.path = selected
        self.editor.setPlainText(text)
        self.editor.document().setModified(False)

    def save_document(self):
        if not self.path: return self.save_as()
        try: atomic_write_text(self.path,self.editor.toPlainText())
        except OSError as exc:
            QMessageBox.warning(self,'No se pudo guardar',str(exc))
            return False
        self.editor.document().setModified(False)
        return True

    def save_as(self):
        selected,_ = QFileDialog.getSaveFileName(self,'Guardar SQL',self.path or 'consulta.sql','SQL (*.sql)')
        if not selected: return False
        old = self.path
        self.path = selected
        if self.save_document(): return True
        self.path = old
        return False

    def closeEvent(self,event: QCloseEvent):
        if self.worker is not None:
            self.statusBar().showMessage('Espere a que termine la operación para cerrar.')
            event.ignore()
        elif self.guard_document(): event.accept()
        else: event.ignore()


def launch(database='database'):
    app = QApplication.instance() or QApplication([])
    window = MainWindow(database)
    window.show()
    return app.exec()
