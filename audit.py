import lrcat
import auditdb
import argparse
import os
import sys
import analyze

LRCAT='/Users/chuyu/Pictures/lightroom-catalog-local/lightroom-catalog-2.lrcat'
PICASA_DIR='/Volumes/extern-photo/picasa_snapshot_2018.08'


def parse_args():
    action_choices = ('read-lrcat', 'walk-picasa-dir','report','report-vids','summary')
    parser = argparse.ArgumentParser()
    parser.add_argument('action',choices=action_choices,help=f"desired action")
    parser.add_argument("--lrcat", dest='lrcat_fname',
                        type=str,
                        default=LRCAT,
                        help=f"specify lightroom catalog; default={LRCAT}")
    parser.add_argument("--picasa-dir",
                        dest='picasa_dir',
                        action='store',
                        type=str,
                        default=PICASA_DIR,
                        help=f"specify picasa root directory; default={PICASA_DIR}")
    parser.add_argument("--force-drop", dest='force_drop', action="store_true", default=False, help="force delete all tables prior to action")
    parser.add_argument("--subdir", dest='subdir',  default="", help="for action=report: limit search to directories which start with 'subdir', e.g. '1999' -> '1999/*'")

    args = parser.parse_args()
    return args

def populate_from_lrcat(lrcat_fname, picasa_root_dir):
    """
    given the path to the lightroom catalog (lrcat)
    and the full path to the picasa directory (/foo/bar/picasa_dirs),
    search the lrcat for files which have picasa_dirs in the path.

    insert these entries into the Audit DB tables

    returns nothing
    """
    adb = auditdb.AuditDb()

    adb.create_table_lr_files()  # drop existing lr_files data
    adb.create_table_dirpaths()
    
    lrdb = lrcat.LrCat(lrcat_fname)

    picasa_root_dir = os.path.abspath(picasa_root_dir)  # normalize
    picasa_root_partial = os.path.split(picasa_root_dir)[-1]  # /foo/bar/picasa_dirs -> picasa_dirs
    
    dict_list = lrdb.get_picasa_files(picasa_root_partial)

    count=0
    for d in dict_list:
        if (count%1000)==0:
            print(".",end='');sys.stdout.flush()
        #end
        count += 1
        path_id = adb.register_path_from_root(d['path_from_root'], picasa_root_dir)
        fname = d['original_filename']
        adb.insert_into_lr_files(path_id, fname)
    #end
    print(".")
    #
    # need to commit, otherwise file is not updated

    adb.commit()
    return


def derive_path_from_root(dir_path, root_dir):
    """
    given
    /Volumes/picasa_root/2003/2003.12.15-xmas_lights
    ^^^^^^^^^^^^^^^^^^^^
           |
         root

    return the path after the root, i.e. 2003/2003.12.15-xmas_lights
    """

    t = dir_path.rpartition(root_dir)
    assert t[0]==''
    path_from_root=t[2]
    if path_from_root[0:1]=='/':
        path_from_root=path_from_root[1:]
    #end

    return path_from_root

def picasa_file_filter(fname):
    """
    first-pass filter to separate out non-desirable picasa files
    """
    fname = fname.lower()
    is_valid = True
    (root, ext) = os.path.splitext(fname)
    if len(ext) <= 0:
        is_valid = False
    #end
    
    if fname=="thumbs.db":
        is_valid = False
    #end
    if fname==".picasa.ini" or fname=="picasa.ini":
        is_valid = False
    #end

    return is_valid


def walk_picasa_dir(picasa_root_dir):
    picasa_root_dir = os.path.normpath(picasa_root_dir)
    assert os.path.exists(picasa_root_dir), f"{picasa_root_dir} does not exist"

    adb = auditdb.AuditDb()
    adb.create_table_picasafiles()  # fresh table 
    
    num_files = 0
    print(picasa_root_dir)
    for dir_path, subdir_list, file_list in os.walk(picasa_root_dir):
        for f in file_list:
            if picasa_file_filter(f):
                path_from_root = derive_path_from_root(dir_path, picasa_root_dir)
                path_id = adb.register_path_from_root(path_from_root, picasa_root_dir)
                adb.insert_into_picasa_files(path_id, f)
                
                num_files += 1
                if (num_files%1000)==0:
                    print('.',end='');sys.stdout.flush()
                #end
            #end
        #end
    #end
    adb.commit()
    print('')
    print(f'walk_picasa_dir processed {num_files} files')
    return

def correlate():
    adb = auditdb.AuditDb()
    cur = adb.con.cursor()

    #
    # write lr_files_id in picasa_files:
     # image files found in lr_files
    cmd = """\
    SELECT picasa_files.id, lr_files.id, lr_files.path_id, picasa_files.path_id, lr_files.filename, picasa_files.filename FROM picasa_files
    INNER JOIN lr_files WHERE picasa_files.path_id=lr_files.path_id AND picasa_files.filename=lr_files.filename
    """

    cur.execute(cmd)
    entry_list = cur.fetchall()
    assert(len(entry_list) > 0)
    print(f"correlate found {len(entry_list)} matches")

    for entry in entry_list:
        adb.update_picasa_files_lr_id(entry[0], entry[1])
    #end


    cmd = """\
    SELECT picasa_files.id, lr_files.id, lr_files.path_id, picasa_files.path_id, lr_files.filename, picasa_files.filename FROM lr_files
    INNER JOIN picasa_files WHERE picasa_files.path_id=lr_files.path_id AND picasa_files.filename=lr_files.filename
    """

    cur.execute(cmd)
    entry_list = cur.fetchall()
    assert(len(entry_list) > 0)
    for entry in entry_list:
        adb.update_lr_files_picasa_id(entry[1], entry[0])
    #end

    #
    # write picsa_id in lr_files:
    # image files found in lr_files
    
    adb.commit()
    print("Correlation Analysis Complete");
    
        

def print_db_stats():
    adb = auditdb.AuditDb()
    d = adb.get_num_db_entries()
    print(f"stats: {d}")
    return

if __name__=="__main__":
    args = parse_args()
    
    if args.force_drop:
        #
        # --force_drop forces the db to wipe out all tables
        a = auditdb.AuditDb(drop_flag=True)
    #end
    if args.action=='read-lrcat':
        assert os.path.exists(args.picasa_dir)
        assert os.path.exists(args.lrcat_fname)
        populate_from_lrcat(args.lrcat_fname,args.picasa_dir)
        print_db_stats()
    elif args.action=='walk-picasa-dir':
        walk_picasa_dir(args.picasa_dir)
        print_db_stats()
        correlate()
    elif args.action=='report':
        #
        # full analysis (takes time)
        a = analyze.Analyzer()
        if len(args.subdir) > 0:
            a.report(subdir=args.subdir)
        else:
            a.report()
        #endf
    elif args.action=='report-vids':
        #
        # full analysis (takes time)
        a = analyze.Analyzer()
        a.report_unregistered_videos(subdir=args.subdir)
    elif args.action=='summary':
        a = analyze.Analyzer()
        a.print_summary()
    #end
        
    
    
