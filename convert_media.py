import logging
import os
import argparse
import subprocess
import sys
import auditdb
import media_ext


def subprocess_with_logging(cmd_list):
    """
    invoke subprocess, send output to logger
    https://stackoverflow.com/questions/18774476/subprocess-call-logger-info-and-error-for-stdout-and-stderr-respectively
    """
    print(cmd_list)
    p = subprocess.Popen(cmd_list, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = p.communicate()

    if stdout:
        print(stdout)
    #end
    if stderr:
        print(stderr)
    #end
    return p.returncode    


def make_dest_fname(src_fname, orig_ext, replacement_ext):
    """
    given foo.avi, .avi, .mp4
    convert foo.avi -> foo.mp4

    return foo.mp4
    """
    assert orig_ext[0]=='.'
    assert replacement_ext[0]=='.'
    
    _, ext = os.path.splitext(src_fname)
    assert ext.lower()==orig_ext
    dest_fname = src_fname.replace(ext,replacement_ext)
    return dest_fname
    

def convert_to_mp4(path, fname, ext):
    """
    convert foo/bar.avi -> foo/bar.mp4
    then create foo/.converted
    rename foo/bar.avi -> foo/bar/.converted/bar.avi
    """
    assert ext in media_ext.UNSUPPORTED_VIDEO_EXT_TUPLE
    
    path = os.path.abspath(path)

    src_fname = os.path.join(path, fname)
    dest_fname = make_dest_fname(src_fname, ext, '.mp4')
    convert_dir = os.path.join(path,'.converted')
    moved_fname = os.path.join(convert_dir, fname)

    if os.path.exists(src_fname)==False:
        print("")
        print(f"ERROR: file does not exist {src_fname}")
        print("")
        return
    #end

    if os.path.exists(dest_fname):
        print("")
        print(f"ERROR: converted file already exists {dest_fname}")
        print("")
        sys.exit(0)
        # assert os.path.exists(src_fname)
        # if os.path.exists(moved_fname):
        #     print(f"*** deleting original because it's already in .converted {src_fname}")
        #     os.remove(src_fname)
        # #end
        # return
    #end

    #
    # ffmpeg -i DSCN0619.AVI -c:v h264 -c:a mp3 -y -strict -1 DSCN0619.mp4
    #
    # strict -1 allows weird sample rates used by old audio codecs.
    # -crf 10 is perceptually lossless compression
    # see     http://trac.ffmpeg.org/wiki/Encode/H.264
    cmd = ['ffmpeg','-loglevel','quiet','-i', src_fname, '-c:v','h264','-crf','10','-c:a','mp3', '-y','-strict','-1',dest_fname]
    retcode = subprocess_with_logging(cmd)
    assert retcode==0

    try:
        os.mkdir(convert_dir)
    except OSError:
        pass
    #end

    assert os.path.exists(dest_fname)

    os.rename(src_fname, moved_fname)
    print(f"SUCCESS: converted {moved_fname}")

    return

def convert_to_jpg(path, fname, ext):
    """
    given ./foo/ and bar.pdf
    convert foo/bar.pdf -> foo/bar-*.jpg
    then create foo/.converted
    rename foo/bar.pdf -> foo/bar/.converted/bar.pdf
    """
    assert os.path.isabs(path)
    assert ext in media_ext.UNSUPPORTED_IMAGE_EXT_TUPLE
    
    src_fname = os.path.join(path, fname)
    dest_fname = make_dest_fname(src_fname, ext, '.jpg')
    convert_dir = os.path.join(path,'.converted')
    moved_fname = os.path.join(convert_dir, fname)

    if os.path.exists(src_fname)==False:
        print("")
        print(f"ERROR: file does not exist {src_fname}")
        print("")
        return
    #end

    if os.path.exists(dest_fname) or os.path.exists(dest_fname.replace('.jpg','-0.jpg')):
        print("")
        print(f"ERROR: converted file already exists {dest_fname}")
        sys.exit(0)
        # print("")
        # assert os.path.exists(src_fname)
        # if os.path.exists(moved_fname):
        #     print(f"*** deleting original because it's already in .converted {src_fname}")
        #     os.remove(src_fname)
        # #end
        # return
    #end

    #
    # ffmpeg -i DSCN0619.AVI -c:v h264 -c:a mp3 -y -strict -1 DSCN0619.mp4
    #
    # strict -1 allows weird sample rates used by old audio codecs.
    cmd = ['magick', src_fname, dest_fname]
    retcode = subprocess_with_logging(cmd)
    assert retcode==0

    try:
        os.mkdir(convert_dir)
    except OSError:
        pass
    #end

    #
    # output for foo.pdf will be named foo-0.pdf (for multi-page pdf)
    assert os.path.exists(dest_fname) or os.path.exists(dest_fname.replace('.jpg','-0.jpg'))

    os.rename(src_fname, moved_fname)
    print(f"SUCCESS: converted {moved_fname}")

    #
    # if the file failed to move to .convert because it's already there, then
    # delete the old version
    if os.path.exists(src_fname) and os.path.exists(moved_fname):
        print(f"*** deleting original because it's already in .converted {src_fname}")
        #os.remove(src_fname)
        sys.exit(0)
    #end

    return

def tuple_to_dict(x):
    """
    convert query result tuple into a dict
    
    returns dict
    """
    d = {'fname': x[0],
         'extension': x[1],
         'root_path': x[2],
         'path_from_root': x[3]}
    return d

def get_media_list():
    a = auditdb.AuditDb()
    cur=a.con.cursor()
    #
    # get list of all media which are NOT lightroom-compatible, regardless of whether
    # LR previously imported it (LR can import some but not all .mov files)
    cmd = """
    SELECT picasa_files.filename, picasa_files.extension, dirpaths.root_path, dirpaths.path_from_root FROM picasa_files
    INNER JOIN dirpaths
    WHERE picasa_files.path_id==dirpaths.id 
        AND dirpaths.path_from_root NOT LIKE "%picasaoriginals/"
        AND dirpaths.path_from_root NOT LIKE "%converted/"
        AND (
    """
    ext = media_ext.UNSUPPORTED_VIDEO_EXT_TUPLE[0]
    cmd = cmd + f"""picasa_files.extension="{ext}" """
    for ext in media_ext.UNSUPPORTED_VIDEO_EXT_TUPLE[1:] + media_ext.UNSUPPORTED_IMAGE_EXT_TUPLE:
        cmd = cmd + f"""OR picasa_files.extension="{ext}" """
    #end
    cmd = cmd + """) """
    cmd = cmd + "ORDER BY dirpaths.path_from_root"
    #print(cmd)
    cur.execute(cmd)
    result_list = cur.fetchall()

    #
    # convert to list of dicts
    media_list = [tuple_to_dict(x) for x in result_list]
    return media_list

def convert_all(dry_run_flag=False, partial_path=""):
    """
    open database
    select rows with media which need converting
    and convert them
    """
    target_media_list = get_media_list()
    if len(target_media_list ) <= 0:
        print("did not find any files to convert")
        print("exiting")
        sys.exit(0)
    #end
    print(f"candidates:  {len(target_media_list)} files")
    
    if len(partial_path) > 0:
        #
        # filter target_media_list with partial_path
        len_partial = len(partial_path)
        target_media_list = [t for t in target_media_list if t['path_from_root'][0:len_partial]==partial_path]
        print(f"candidates:  {len(target_media_list)} files (after filtering)")
    #end

    index = 1
    for target_dict in target_media_list:
        full_path = os.path.join(target_dict['root_path'], target_dict['path_from_root'])  # e.g. /foo/bar
        full_fname = os.path.join(full_path, target_dict['fname'])  # e.g. /foo/bar/image.gif
        assert os.path.isabs(full_fname)


        # if len(partial_path) > 0 and (partial_path not in target_dict['path_from_root']):
        #     continue # go to top of loop
        # #end
        
        print(f"{index}/{len(target_media_list)} ",end='')
        if os.path.exists(full_fname)==False:
            print(f"ERROR: file does not exist {full_fname}")
            print("")
        elif target_dict['extension'] in media_ext.UNSUPPORTED_VIDEO_EXT_TUPLE:
            print(f"video convert {target_dict}")
            if dry_run_flag==False:
                convert_to_mp4(full_path, target_dict['fname'], target_dict['extension'])
            #end

        elif target_dict['extension'] in media_ext.UNSUPPORTED_IMAGE_EXT_TUPLE:
            print(f"image convert {target_dict}")
            if dry_run_flag==False:
                convert_to_jpg(full_path, target_dict['fname'], target_dict['extension'], dry_run_flag = dry_run_flag)
            #end
        else:
            print(f"unhandled file type {target_dict['extension']}")
        #end
        index += 1
    #end


def print_extension_summary():
    a = auditdb.AuditDb()
    cur=a.con.cursor()
    cmd = """
    SELECT DISTINCT picasa_files.extension
    FROM picasa_files
    WHERE picasa_files.lr_file_id IS NULL AND picasa_files.is_lr_compat=0
    ORDER BY picasa_files.extension ASC
    """
    cur.execute(cmd)
    result_list = cur.fetchall()

    print("LIGHTROOM UNSUPPORTED EXTENSIONS")
    print(f"""| {"ext":15s} | {"video":5s} | {"image":5s} | """)
    print("===================================")
    for result in result_list:
        ext = result[0]
        # convert_to_video = ext in media_ext.UNSUPPORTED_VIDEO_EXT_TUPLE
        # convert_to_image = ext in media_ext.IMAGE_EXT_TUPLE
        # try
        # except ValueError:
        #     convert_to_video = False

        # try:
        #     convert_to_image = IMAGE_EXT_LIST.index(ext) >= 0
        print(f"| {ext:15s} ",end='')
        if ext in media_ext.UNSUPPORTED_VIDEO_EXT_TUPLE:
            print(f"""| {"*":5s} """, end='')
        else:
            print(f"""| {" ":5s} """, end='')
        #end
        if ext in media_ext.UNSUPPORTED_IMAGE_EXT_TUPLE:
            print(f"""| {"*":5s} |""")
        else:
            print(f"""| {" ":5s} |""")
        #end
        
    #end

def delete_dups(dry_run_flag=True):
    """
    find all F.mov s.t. path looks like "/.converted"

    if ../F.mp4  exists   # was converted
    and ../F.mov exists   # is duplicated under ./converted
    and ../F.mov is NOT registered  # is not already registered in LR

    then rm ../F.mov    # delete dup
    """

    cmd = """
    SELECT * FROM picasa_files
    JOIN dirpaths
    WHERE picasa_files.extension=".mov"
    AND dirpaths.path_from_root LIKE "%.converted/"
    AND dirpaths.id=picasa_files.path_id
    """

    
    
def parse_args():
    parser = argparse.ArgumentParser()
    test_choices = (None, 'video', 'image')
    parser.add_argument("--test",  metavar='test', choices=test_choices, default=None, help=f"convert 1 file of type {test_choices}")
    parser.add_argument("--fname",    type=str, help="path+fname of file to convert for --test")
    parser.add_argument("--ext-summary",  dest="flag_ext_summary", action="store_true", default=False, help="generate extension summary")
    parser.add_argument("-X", "--execute", dest="flag_execute", action="store_true", default=False, help="execute conversion actions")
    parser.add_argument("-p", "--partial-path", dest="partial_path", type=str, default="", help="specify partial path (path-from-root) for conversion")
    args = parser.parse_args()
    return args

if __name__=="__main__":
    args = parse_args()
    if args.test=='video':
        assert len(args.fname) > 0
        srcpath, fname = os.path.split(args.fname)
        _, ext = os.path.splitext(fname)
        convert_to_mp4(srcpath, fname, ext)
    elif args.test=='image':
        assert len(args.fname) > 0
        srcpath, fname = os.path.split(args.fname)
        _, ext = os.path.splitext(fname)
        convert_to_jpg(srcpath, fname, ext)
    elif args.flag_ext_summary:
        print_extension_summary()
    else:
        assert args.test==None
        print("convert all")
        dry_run_flag = args.flag_execute==False
        convert_all(dry_run_flag=dry_run_flag, partial_path = args.partial_path)
    #end
    
        

    
