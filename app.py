
from flask import Flask
from flask import request
from flask import render_template
from flask import send_from_directory
from PIL import Image, UnidentifiedImageError
import os
import glob
import sys
import binascii
import argparse
import json
import errno
import random

THUMBNAIL_SIZE = (200, 200)

app = Flask("Flask Image Gallery")
app.config['IMAGE_EXTS'] = [".png", ".jpg", ".jpeg", ".gif", ".tiff"]
app.config['THUMBNAIL_DIR'] = ".thumbnails"

def mkdir_p(directory_name):
    try:
        os.makedirs(directory_name)
    except OSError as exc: 
        if exc.errno == errno.EEXIST and os.path.isdir(directory_name):
            pass

def is_image(filename):
    return any(filename.lower().endswith(ext) for ext in app.config['IMAGE_EXTS'])

def getdir(path):
    dirs=[]
    files=[]
    for dir_entry in os.scandir(path):
        if dir_entry.is_dir():
            dirs.append(dir_entry)
        elif dir_entry.is_file():
            files.append(dir_entry)
    return (dirs, files)
    

class ThumbnailDB(object):
    """Entry:
        size
        ctime
        mtime
        atime
    """

    def __init__(self, root_path):
        self.root_path=root_path
        try:
            with open(os.path.join(app.config['THUMBNAIL_DIR'], root_path, '.thumbnails.json'),'r') as f:
                self.entries=json.load(f)
        except FileNotFoundError as e:
            self.entries={}

    def __call__(self,path):
        """Generate thumbnail. Return thumbnail entry"""
        images_path=app.config['ROOT_DIR']
        thumbnails_path=app.config['THUMBNAIL_DIR']
        image_path=os.path.join(images_path, self.root_path, path)
        image_stat=os.stat(image_path)
        thumbnail_path=os.path.join(thumbnails_path,self.root_path, path)
        thumbnail_dir=os.path.dirname(thumbnail_path)
        stored_entry=self.entries.get(path, None)
        if stored_entry:
            if stored_entry['mtime']==image_stat.st_mtime_ns and \
                stored_entry['size']==image_stat.st_size:
                    # no need to regen thumbnail
                    pass
            else:
                stored_entry=None
        if stored_entry is None:
                # regen thumbnail
                print("Generating thumbnail for {}".format(image_path))
                image=None
                try:
                    image = Image.open(image_path)
                    image.thumbnail(THUMBNAIL_SIZE)
                except OSError:
                    # There was an error generating thumbnail
                    image = None
                except UnidentifiedImageError:
                    image = None
                if image:
                    mkdir_p(thumbnail_dir)
                    image.save(thumbnail_path)
                    e={}
                    e['mtime']=image_stat.st_mtime_ns
                    e['size']=image_stat.st_size
                    self.entries[path]=e
                    stored_entry=e
                    # save new entries
        return stored_entry

    def scan(self):
        """Scan directory for thumbnails and generate them if needed"""
        my_dir = os.path.join(app.config['ROOT_DIR'],self.root_path)
        for dir_entry in os.scandir(my_dir):
            if dir_entry.is_file():
                file=dir_entry.name  
                if is_image(file):
                    self.__call__(file)

    def __setitem__(self,path,entry):
        self.entries[path]=entry

    def save(self):
        mkdir_p(os.path.join(app.config['THUMBNAIL_DIR'], self.root_path))
        with open(os.path.join(app.config['THUMBNAIL_DIR'], self.root_path, '.thumbnails.json'),'w') as f:
            f.write(json.dumps(self.entries))
            
def encode(x):
    return binascii.hexlify(x.encode('utf-8')).decode()

def decode(x):
    return binascii.unhexlify(x.encode('utf-8')).decode()

@app.route('/dir/', defaults={'filepath':''})
@app.route('/dir/<path:filepath>')
def dirlist(filepath):
    print(filepath)
    if filepath:
        parent=os.path.dirname(filepath)
        print("Parent: {}".format(parent))
    else:
        parent=None
    tb=ThumbnailDB(filepath)
    root_dir = os.path.join(app.config['ROOT_DIR'],filepath)
    print(app.config['ROOT_DIR'], root_dir)
    images = []
    dir_paths = {}
    for dir_entry in os.scandir(root_dir):
        if dir_entry.is_dir():
            if dir_entry.name.startswith('.'):
                continue
            _, subfiles = getdir(os.path.join(root_dir, dir_entry.name))
            icon_files=list(filter(lambda s: is_image(s.name), subfiles))
            if icon_files:
                dir_icon=random.choice(icon_files)
                subtb=ThumbnailDB(os.path.join(filepath, dir_entry.name))
                subtb(dir_icon.name)

                dir_paths[dir_entry.name]={"path": os.path.join(filepath, dir_entry.name),
                                        "thumb": encode(os.path.join(app.config['THUMBNAIL_DIR'],filepath,dir_entry.name,dir_icon.name))
                }
            else:
                dir_paths[dir_entry.name]={"path": os.path.join(filepath, dir_entry.name),
                                        "thumb": None}
        if dir_entry.is_file():
            file=dir_entry.name  
            if is_image(file):
                print(file)
                tb(file)
                images.append({"path": encode(os.path.join(app.config['ROOT_DIR'], filepath,file)), 
                                "thumb": encode(os.path.join(app.config['THUMBNAIL_DIR'], filepath, file)),
                                "filename": file })
        # dir_paths.extend(os.path.join(filepath,d) for d in dirs)
    response=render_template('folder.html', images=images, dirs=dir_paths, parent=parent)
    tb.save()
    return response

@app.route('/', redirect_to='/dir/')
def root():
    pass

@app.route('/scan/', defaults={'filepath':''})
@app.route('/scan/<path:filepath>')
def scan(filepath):
    root_dir = os.path.join(app.config['ROOT_DIR'],filepath)
    for root,dirs,_ in os.walk(root_dir):
        for dir in dirs:
            tb=ThumbnailDB(os.path.join(root,dir))
            tb.scan()
    return render_template('scan.html')

@app.route('/all/<path:filepath>')
def all(filepath):
    root_dir = os.path.join(app.config['ROOT_DIR'],filepath)
    img_paths=[]
    for root,dirs,files in os.walk(root_dir):
        for dir in dirs:
            tb=ThumbnailDB(os.path.join(filepath,dir))
            try:
                tb.scan()
                tb.save()
            except FileNotFoundError:
                pass
        for file in files:
            if is_image(file):
                # print(root[len(root_dir)+1:])
                print(os.path.join(app.config['ROOT_DIR'], filepath, root[len(root_dir)+1:], file))
                img_paths.append({"path": encode(os.path.join(app.config['ROOT_DIR'], filepath, root[len(root_dir)+1:], file)), 
                              "thumb": encode(os.path.join(app.config['THUMBNAIL_DIR'], filepath, root[len(root_dir)+1:], file)),
                              "filename": file })
    return render_template('index.html', paths=img_paths)


@app.route('/cdn/<path:filepath>')
def download_file(filepath):
    dir,filename = os.path.split(decode(filepath))
    # return send_from_directory(dir, filename, attachment_filename=filename, as_attachment=False)
    return send_from_directory(dir, filename, as_attachment=False)

if __name__=="__main__":
    parser = argparse.ArgumentParser('Usage: %prog [options]')
    parser.add_argument('root_dir', help='Gallery root directory path')
    parser.add_argument('-l', '--listen', dest='host', default='127.0.0.1', \
                                    help='address to listen on [127.0.0.1]')
    parser.add_argument('-p', '--port', metavar='PORT', dest='port', type=int, \
                                default=5000, help='port to listen on [5000]')
    parser.add_argument('-t', '--thumbnails-dir', default='.thumbnails')
    args = parser.parse_args()
    app.config['ROOT_DIR'] = args.root_dir
    app.config['THUMBNAIL_DIR'] = args.thumbnails_dir
    app.run(host=args.host, port=args.port, debug=True)
