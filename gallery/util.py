import os
from addict import Dict
from sys import stderr

from gallery.models import Directory
from gallery.models import File

def get_dir_file_contents(dir_id):
    print(File.query.filter(File.parent == dir_id).all())
    return File.query.filter(File.parent == dir_id).all()

def get_full_dir_path(dir_id):
    path_stack = []
    dir_model = Directory.query.filter(Directory.id == dir_id).first()
    path_stack.append(dir_model.name)
    while dir_model.parent != None:
        dir_model = Directory.query.filter(Directory.id == dir_model.parent).first()
        path_stack.append(dir_model.name)
    path_stack.pop()
    path = ""

    while not len(path_stack) == 0:
        path = os.path.join(path, path_stack.pop())

    return os.path.join('/', path)
def get_dir_tree_dict():
    path = os.path.normpath("/gallery-data/root")
    file_tree = Dict()
    for root, _, files in os.walk(path, topdown=True):
        path = root.split('/')
        path.pop(0)
        file_tree_fd = file_tree
        for part in path:
            file_tree_fd = file_tree_fd[part]
        file_tree_fd['.'] = files

    return file_tree

def convert_bytes_to_utf8(dic):
    for key in dic:
        if isinstance(key, bytes):
            try:
                k = key.decode('utf-8')
            except Exception as e:
                print(e, file=stderr)
            v = dic[key]
            del dic[key]
            dic[k] = v
        if isinstance(dic[key], bytes):
            try:
                v = dic[key].decode('utf-8')
            except Exception as e:
                print(e, file=stderr)
            dic[key] = v
    return dic

def allowed_file(filename):
    return '.' in filename and filename.lower().rsplit('.', 1)[1] in \
            [
                    'txt',
                    'png',
                    'jpg',
                    'jpeg',
                    'mpg',
                    'mp4',
                    'avi',
                    'cr2'
            ]
