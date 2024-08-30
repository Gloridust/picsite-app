import sys
import os
import git
import shutil
import yaml
from pathlib import Path
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QPushButton, QLabel, 
                             QGridLayout, QFileDialog, QLineEdit, QFormLayout, QDialog, 
                             QProgressDialog, QMainWindow, QMessageBox)
from PyQt5.QtGui import QPixmap, QFont
from PyQt5.QtCore import Qt, QThread, pyqtSignal
import qtawesome as qta
import qdarkstyle

# 更新配置路径
USER_DOCS = Path.home() / "Documents" / "MyAlbumApp"
GIT_LOCAL_PATH = str(USER_DOCS)
ALBUMS_PATH = str(USER_DOCS / "albums")
IMAGES_PATH = str(USER_DOCS / "images")

# 确保必要的目录存在
os.makedirs(GIT_LOCAL_PATH, exist_ok=True)
os.makedirs(ALBUMS_PATH, exist_ok=True)
os.makedirs(IMAGES_PATH, exist_ok=True)

# 从配置文件中读取Git仓库URL和凭证
GIT_REPO_URL = 'https://github.com/MrHeYGeeker/picsite-he.git'
GIT_USER = 'Gloridust'
GIT_TOKEN = 'your_git_token_here'  # 请替换为实际的token，并确保不要在公开场合分享

class GitHandler(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.repo = None
        self.action = None
        self.message = None

    def remove_readonly(self, func, path, excinfo):
        os.chmod(path, 0o777)
        func(path)

    def clone_repo(self):
        try:
            if os.path.exists(GIT_LOCAL_PATH):
                shutil.rmtree(GIT_LOCAL_PATH, onerror=self.remove_readonly)
            self.repo = git.Repo.clone_from(GIT_REPO_URL, GIT_LOCAL_PATH)
        except git.GitCommandError as e:
            self.error.emit(f"Git克隆错误: {str(e)}")
        except Exception as e:
            self.error.emit(f"未知错误: {str(e)}")

    def commit_and_push(self, message):
        try:
            if not self.repo:
                self.repo = git.Repo(GIT_LOCAL_PATH)
            self.repo.git.add(A=True)
            self.repo.index.commit(message)
            origin = self.repo.remote(name='origin')
            origin.push()
        except git.GitCommandError as e:
            self.error.emit(f"Git提交和推送错误: {str(e)}")
        except Exception as e:
            self.error.emit(f"未知错误: {str(e)}")

    def run(self):
        if self.action == 'clone':
            self.progress.emit(10)
            self.clone_repo()
            self.progress.emit(100)
        elif self.action == 'commit':
            self.commit_and_push(self.message)
        self.finished.emit()

    def set_action(self, action, message=None):
        self.action = action
        self.message = message

class AlbumApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.git_handler = GitHandler()
        self.git_handler.progress.connect(self.update_progress)
        self.git_handler.finished.connect(self.on_loading_finished)
        self.git_handler.error.connect(self.show_error_message)
        self.show_loading_dialog()
        self.git_handler.set_action('clone')
        self.git_handler.start()

    def show_loading_dialog(self):
        self.loading_dialog = QProgressDialog("加载中...", None, 0, 100, self)
        self.loading_dialog.setWindowTitle("请稍候")
        self.loading_dialog.setWindowModality(Qt.WindowModal)
        self.loading_dialog.setMinimumDuration(0)
        self.loading_dialog.setValue(0)
        self.loading_dialog.show()

    def update_progress(self, value):
        self.loading_dialog.setValue(value)

    def on_loading_finished(self):
        self.loading_dialog.close()
        self.load_albums()

    def show_error_message(self, message):
        QMessageBox.critical(self, "错误", message)

    def initUI(self):
        self.setWindowTitle('Album Viewer')
        self.setGeometry(100, 100, 800, 600)
        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)
        self.layout = QVBoxLayout(self.main_widget)

        self.title_label = QLabel('我的相册')
        self.title_label.setFont(QFont('Arial', 20))
        self.title_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.title_label)

        self.grid_layout = QGridLayout()
        self.grid_layout.setSpacing(20)
        self.layout.addLayout(self.grid_layout)

        self.new_album_button = QPushButton('新建相册')
        self.new_album_button.setStyleSheet("padding: 10px; font-size: 16px;")
        self.new_album_button.setIcon(qta.icon('fa.plus'))
        self.new_album_button.clicked.connect(self.create_new_album)
        self.layout.addWidget(self.new_album_button, alignment=Qt.AlignCenter)

    def load_albums(self):
        self.albums = []
        for file_name in os.listdir(ALBUMS_PATH):
            if file_name.endswith('.md'):
                file_path = os.path.join(ALBUMS_PATH, file_name)
                with open(file_path, 'r', encoding='utf-8') as file:
                    content = file.read()
                    album = yaml.safe_load(content.split('---')[1])
                    album['path'] = file_path
                    self.albums.append(album)

        self.display_albums()

    def display_albums(self):
        for i, album in enumerate(self.albums):
            cover_image_path = os.path.join(GIT_LOCAL_PATH, 'public', album['coverImage'][1:])
            pixmap = QPixmap(cover_image_path)
            label = QLabel()
            label.setPixmap(pixmap.scaled(200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            label.mousePressEvent = lambda event, a=album: self.open_album(a)
            self.grid_layout.addWidget(label, i // 3, (i % 3) * 2)

            album_info = QLabel(f"{album['name']}\n{album['date']}")
            album_info.setFont(QFont('Arial', 14))
            album_info.setAlignment(Qt.AlignCenter)
            self.grid_layout.addWidget(album_info, i // 3, (i % 3) * 2 + 1)

    def open_album(self, album):
        self.album_view = AlbumView(album, self.git_handler)
        self.album_view.show()

    def create_new_album(self):
        dialog = NewAlbumDialog(self)
        if dialog.exec_():
            album_data = dialog.get_album_data()
            self.save_new_album(album_data)

    def save_new_album(self, album_data):
        album_folder = os.path.join(IMAGES_PATH, album_data['id'])
        os.makedirs(album_folder, exist_ok=True)
        cover_image_dest = os.path.join(album_folder, os.path.basename(album_data['coverImage']))
        shutil.copy(album_data['coverImage'], cover_image_dest)

        album_data['coverImage'] = f'/images/{album_data["id"]}/{os.path.basename(album_data["coverImage"])}'

        album_md_path = os.path.join(ALBUMS_PATH, f'{album_data["id"]}.md')
        with open(album_md_path, 'w', encoding='utf-8') as file:
            file.write('---\n')
            yaml.dump(album_data, file)
            file.write('---\n')
            file.write(f"- {album_data['coverImage']}\n")

        self.git_handler.set_action('commit', '新增相册')
        self.git_handler.start()
        self.git_handler.finished.connect(self.on_album_saved)

    def on_album_saved(self):
        self.git_handler.finished.disconnect(self.on_album_saved)
        self.load_albums()

class NewAlbumDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('新建相册')
        self.setGeometry(200, 200, 400, 300)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        form_layout = QFormLayout()
        self.id_edit = QLineEdit()
        self.name_edit = QLineEdit()
        self.date_edit = QLineEdit()
        self.description_edit = QLineEdit()
        form_layout.addRow('ID:', self.id_edit)
        form_layout.addRow('名称:', self.name_edit)
        form_layout.addRow('日期:', self.date_edit)
        form_layout.addRow('描述:', self.description_edit)
        layout.addLayout(form_layout)

        self.image_button = QPushButton('选择封面图片')
        self.image_button.setStyleSheet("padding: 5px; font-size: 14px;")
        self.image_button.setIcon(qta.icon('fa.image'))
        self.image_button.clicked.connect(self.select_cover_image)
        layout.addWidget(self.image_button)

        buttons = QVBoxLayout()
        save_button = QPushButton('保存')
        save_button.setStyleSheet("padding: 10px; font-size: 16px;")
        save_button.setIcon(qta.icon('fa.save'))
        save_button.clicked.connect(self.accept)
        buttons.addWidget(save_button)

        cancel_button = QPushButton('取消')
        cancel_button.setStyleSheet("padding: 10px; font-size: 16px;")
        cancel_button.setIcon(qta.icon('fa.times'))
        cancel_button.clicked.connect(self.reject)
        buttons.addWidget(cancel_button)

        layout.addLayout(buttons)
        self.setLayout(layout)

    def select_cover_image(self):
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(self, "选择封面图片", "", "Images (*.png *.jpg *.jpeg *.webp)", options=options)
        if file_path:
            self.cover_image_path = file_path

    def get_album_data(self):
        return {
            'id': self.id_edit.text(),
            'name': self.name_edit.text(),
            'date': self.date_edit.text(),
            'description': self.description_edit.text(),
            'coverImage': self.cover_image_path
        }

class AlbumView(QWidget):
    def __init__(self, album, git_handler):
        super().__init__()
        self.album = album
        self.git_handler = git_handler
        self.initUI()

    def initUI(self):
        self.setWindowTitle(self.album['name'])
        self.setGeometry(100, 100, 800, 600)
        self.layout = QVBoxLayout()
        self.grid_layout = QGridLayout()
        self.grid_layout.setSpacing(20)

        self.load_images()

        self.add_image_button = QPushButton('添加照片')
        self.add_image_button.setStyleSheet("padding: 10px; font-size: 16px;")
        self.add_image_button.setIcon(qta.icon('fa.plus'))
        self.add_image_button.clicked.connect(self.add_image)

        self.layout.addLayout(self.grid_layout)
        self.layout.addWidget(self.add_image_button, alignment=Qt.AlignCenter)
        self.setLayout(self.layout)

    def load_images(self):
        md_content = ""
        with open(self.album['path'], 'r', encoding='utf-8') as file:
            md_content = file.read()

        image_paths = md_content.split('---')[2].strip().split('\n')
        for i, image_path in enumerate(image_paths):
            image_full_path = os.path.join(GIT_LOCAL_PATH, 'public', image_path[1:].strip())
            pixmap = QPixmap(image_full_path)
            label = QLabel()
            label.setPixmap(pixmap.scaled(200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            self.grid_layout.addWidget(label, i // 3, i % 3)

    def add_image(self):
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(self, "选择照片", "", "Images (*.png *.jpg *.jpeg *.webp)", options=options)
        if file_path:
            image_name = os.path.basename(file_path)
            album_folder = os.path.join(IMAGES_PATH, self.album['id'])
            image_dest = os.path.join(album_folder, image_name)
            shutil.copy(file_path, image_dest)

            with open(self.album['path'], 'a', encoding='utf-8') as file:
                file.write(f"- /images/{self.album['id']}/{image_name}\n")

            self.git_handler.set_action('commit', '添加照片')
            self.git_handler.start()
            self.git_handler.finished.connect(self.on_image_added)

    def on_image_added(self):
        self.git_handler.finished.disconnect(self.on_image_added)
        self.load_images()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
    ex = AlbumApp()
    ex.show()
    sys.exit(app.exec_())