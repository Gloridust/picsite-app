from flask import Flask, render_template, jsonify, request, send_from_directory
import os
import git
import shutil
import yaml
import threading
from config import GIT_REPO_URL, GIT_LOCAL_PATH, ALBUMS_PATH, IMAGES_PATH, GIT_USER, GIT_TOKEN
import sys

def resource_path(relative_path):
    """获取资源的绝对路径"""
    try:
        # PyInstaller 创建临时文件夹，将路径存储在 _MEIPASS 中
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)

app = Flask(__name__, 
           template_folder=resource_path('templates'))
clone_progress = 0
clone_status = "未开始"

class GitHandler:
    def __init__(self):
        self.repo = None
        
    def remove_readonly(self, func, path, excinfo):
        os.chmod(path, 0o777)
        func(path)
        
    def clone_repo(self):
        global clone_progress, clone_status
        try:
            clone_status = "正在检查目录..."
            clone_progress = 5
            
            if os.path.exists(GIT_LOCAL_PATH):
                clone_status = "正在清理旧目录..."
                clone_progress = 10
                shutil.rmtree(GIT_LOCAL_PATH, onerror=self.remove_readonly)
            
            clone_status = "正在克隆仓库..."
            clone_progress = 20
            
            def progress_callback(op_code, cur_count, max_count=None, message=''):
                global clone_progress, clone_status
                if max_count:
                    progress = int(20 + (cur_count / max_count * 70))  # 20-90%
                    clone_progress = min(progress, 90)
                    clone_status = f"正在克隆: {int(cur_count / max_count * 100)}%"
            
            self.repo = git.Repo.clone_from(
                GIT_REPO_URL, 
                GIT_LOCAL_PATH,
                progress=progress_callback
            )
            
            clone_progress = 100
            clone_status = "完成"
            return True
        except git.GitCommandError as e:
            clone_status = f"克隆失败: {str(e)}"
            clone_progress = 0
            return False
        except Exception as e:
            clone_status = f"发生错误: {str(e)}"
            clone_progress = 0
            return False

    def commit_and_push(self, message):
        try:
            self.repo.git.add(A=True)
            self.repo.index.commit(message)
            origin = self.repo.remote(name='origin')
            origin.push()
            return True, "提交成功"
        except git.GitCommandError as e:
            return False, f"Git错误: {str(e)}"

git_handler = GitHandler()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/clone-status')
def get_clone_status():
    return jsonify({
        'progress': clone_progress,
        'status': clone_status
    })

@app.route('/api/albums')
def get_albums():
    albums = []
    if os.path.exists(ALBUMS_PATH):
        for file_name in os.listdir(ALBUMS_PATH):
            if file_name.endswith('.md'):
                file_path = os.path.join(ALBUMS_PATH, file_name)
                try:
                    with open(file_path, 'r', encoding='utf-8') as file:
                        content = file.read()
                        parts = content.split('---')
                        if len(parts) >= 2:
                            # 尝试解析 YAML
                            try:
                                album = yaml.safe_load(parts[1])
                                if album:
                                    # 确保所有必需字段都存在
                                    required_fields = ['id', 'name', 'date', 'coverImage']
                                    if all(field in album for field in required_fields):
                                        album['path'] = file_path
                                        # 统一日期格式
                                        if isinstance(album['date'], str):
                                            album['date'] = album['date'].replace("'", "")
                                        albums.append(album)
                                    else:
                                        print(f"警告: {file_name} 缺少必需字段")
                            except yaml.YAMLError as e:
                                print(f"警告: {file_name} YAML 解析错误: {str(e)}")
                except Exception as e:
                    print(f"警告: 读取文件 {file_name} 时出错: {str(e)}")
    return jsonify(albums)

@app.route('/api/album/<album_id>')
def get_album(album_id):
    try:
        file_path = os.path.join(ALBUMS_PATH, f'{album_id}.md')
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
                parts = content.split('---')
                if len(parts) >= 3:
                    # 解析 frontmatter
                    try:
                        album_data = yaml.safe_load(parts[1])
                        if not album_data:
                            return jsonify({
                                'success': False,
                                'message': '相册元数据解析失败',
                                'images': []
                            })
                    except yaml.YAMLError:
                        return jsonify({
                            'success': False,
                            'message': 'YAML 解析错误',
                            'images': []
                        })

                    # 解析图片列表
                    images_content = parts[2].strip()
                    images = []
                    for line in images_content.split('\n'):
                        line = line.strip()
                        if line.startswith('- '):
                            image_path = line[2:].strip()
                            images.append(image_path)
                        elif line.startswith('/images/'):  # 兼容没有 "- " 前缀的路径
                            images.append(line.strip())

                    return jsonify({
                        'success': True,
                        'images': images,
                        'album': album_data  # 添加相册信息
                    })
                else:
                    return jsonify({
                        'success': False,
                        'message': '相册格式错误',
                        'images': []
                    })
        return jsonify({
            'success': False,
            'message': '相册不存在',
            'images': []
        })
    except Exception as e:
        print(f"加载相册 {album_id} 时出错: {str(e)}")  # 添加日志
        return jsonify({
            'success': False,
            'message': f'加载相册失败: {str(e)}',
            'images': []
        })

@app.route('/images/<path:filename>')
def serve_image(filename):
    normalized_path = os.path.normpath(filename)
    image_path = os.path.join(GIT_LOCAL_PATH, 'public', 'images', normalized_path)
    directory = os.path.dirname(image_path)
    filename = os.path.basename(image_path)
    return send_from_directory(directory, filename)

@app.route('/api/create-album', methods=['POST'])
def create_album():
    try:
        data = request.json
        album_id = data['id']
        
        album_folder = os.path.join(IMAGES_PATH, album_id)
        os.makedirs(album_folder, exist_ok=True)
        
        # 统一日期格式
        date = data['date']
        if isinstance(date, str):
            date = date.replace("'", "")
        
        album_data = {
            'id': album_id,
            'name': data['name'],
            'date': date,
            'description': data.get('description', ''),  # 使用 get 方法处理可选字段
            'coverImage': data['coverImage']
        }
        
        album_md_path = os.path.join(ALBUMS_PATH, f'{album_id}.md')
        with open(album_md_path, 'w', encoding='utf-8') as file:
            file.write('---\n')
            yaml.dump(album_data, file, allow_unicode=True, default_flow_style=False, sort_keys=False)
            file.write('---\n')
            file.write(f"- {album_data['coverImage']}\n")
        
        success, message = git_handler.commit_and_push('新建相册: ' + album_id)
        
        return jsonify({
            'success': success,
            'message': message
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        })

@app.route('/api/upload-image', methods=['POST'])
def upload_image():
    try:
        album_id = request.form.get('albumId')
        file = request.files['image']
        
        if not file:
            return jsonify({'success': False, 'message': '没有文件被上传'})
            
        filename = file.filename
        save_path = os.path.join(IMAGES_PATH, album_id, filename)
        file.save(save_path)
        
        album_path = os.path.join(ALBUMS_PATH, f'{album_id}.md')
        with open(album_path, 'a', encoding='utf-8') as f:
            f.write(f"- /images/{album_id}/{filename}\n")
            
        success, message = git_handler.commit_and_push(f'添加图片到相册 {album_id}')
        
        return jsonify({
            'success': success,
            'message': message,
            'path': f'/images/{album_id}/{filename}'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        })

@app.route('/api/upload-cover', methods=['POST'])
def upload_cover():
    try:
        file = request.files['cover']
        album_id = request.form.get('albumId')
        
        if not file:
            return jsonify({'success': False, 'message': '没有文件被上传'})
            
        filename = f"cover{os.path.splitext(file.filename)[1]}"
        album_folder = os.path.join(IMAGES_PATH, album_id)
        os.makedirs(album_folder, exist_ok=True)
        
        save_path = os.path.join(album_folder, filename)
        file.save(save_path)
        
        return jsonify({
            'success': True,
            'path': f'/images/{album_id}/{filename}'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        })

@app.route('/api/delete-album/<album_id>', methods=['DELETE'])
def delete_album(album_id):
    try:
        # 删除相册文件
        album_md_path = os.path.join(ALBUMS_PATH, f'{album_id}.md')
        if os.path.exists(album_md_path):
            os.remove(album_md_path)
            
        # 删除相册图片目录
        album_folder = os.path.join(IMAGES_PATH, album_id)
        if os.path.exists(album_folder):
            shutil.rmtree(album_folder)
            
        success, message = git_handler.commit_and_push(f'删除相册: {album_id}')
        
        return jsonify({
            'success': success,
            'message': message
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        })

@app.route('/api/delete-image', methods=['DELETE'])
def delete_image():
    try:
        data = request.json
        album_id = data['albumId']
        image_path = data['imagePath']
        
        # 从相册markdown文件中删除图片记录
        album_md_path = os.path.join(ALBUMS_PATH, f'{album_id}.md')
        with open(album_md_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        with open(album_md_path, 'w', encoding='utf-8') as f:
            for line in lines:
                if image_path not in line:
                    f.write(line)
        
        # 删除图片文件
        image_full_path = os.path.join(GIT_LOCAL_PATH, 'public', image_path.lstrip('/'))
        if os.path.exists(image_full_path):
            os.remove(image_full_path)
            
        success, message = git_handler.commit_and_push(f'删除图片: {image_path}')
        
        return jsonify({
            'success': success,
            'message': message
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        })

def start_clone():
    global clone_progress, clone_status
    clone_progress = 10
    git_handler.clone_repo()

if __name__ == '__main__':
    threading.Thread(target=start_clone).start()
    app.run(debug=True)