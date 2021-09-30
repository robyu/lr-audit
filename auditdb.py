import lrcat
import sqlite3
import sys
import os
import media_ext

class AuditDb:
    def __init__(self, fname="audit.sqlite3", drop_flag=False):
        if os.path.exists(fname)==False:
            drop_flag=True   # force all tables to be reconstructed
        #end
        
        self.con = sqlite3.connect(fname)
        cur = self.con.cursor()

        if drop_flag:
            self.create_table_lr_files()
            self.create_table_picasafiles()
            self.create_table_dirpaths()
        #end

        self.path_cache = {}

    def create_table_dirpaths(self):
        print("deleting table: dirpaths");
        cur = self.con.cursor()
        cmd = """
        DROP TABLE IF EXISTS dirpaths;
        """

        cur.execute(cmd)
        cmd = """
        CREATE TABLE IF NOT EXISTS dirpaths(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        root_path TEXT NOT NULL,
        path_from_root TEXT NOT NULL UNIQUE);
        """

        cur.execute(cmd)
        return

    def create_table_lr_files(self):
        print("deleting table: lr_files");
        cur = self.con.cursor()
        cmd = """
        DROP TABLE IF EXISTS lr_files;"""
        cur.execute(cmd)

        cmd = """
        CREATE TABLE IF NOT EXISTS lr_files(
        id  INTEGER PRIMARY KEY AUTOINCREMENT,
        path_id INTEGER NOT NULL,
        extension TEXT,
        picasa_file_id INTEGER,
        filename TEXT NOT NULL);
        """
        cur.execute(cmd)
        return

    def create_table_picasafiles(self):
        print("deleting table: picasa_files");
        cur = self.con.cursor()
        cmd = """
        DROP TABLE IF EXISTS picasa_files;
        """
        cur.execute(cmd)

        cmd = """
        CREATE TABLE IF NOT EXISTS picasa_files(
        id  INTEGER PRIMARY KEY AUTOINCREMENT,
        path_id INTEGER NOT NULL,
        extension TEXT,
        lr_file_id INTEGER,
        filename TEXT NOT NULL);
        """
        cur.execute(cmd)
        return

    def normalize_path_from_root(self, path_from_root):
        """
        normalize path_from_root wrt begin and end path separators

        returns normalized path
        """
        if path_from_root[0:1]=='/':
            path_from_root=path_from_root[1:]
        #end

        if path_from_root[-1] != '/':
            path_from_root = path_from_root + '/'
        #end

        return path_from_root
            
    
    def register_path_from_root(self, path_from_root, root_dir):
        """
        given path_from_root (a string), return the 
        corresponding row ID (an integer) from the database.
        
        the row ID is either an existing table entry or a new table entry.

        returns row ID (integer)
        """
        path_from_root = self.normalize_path_from_root(path_from_root)
        #
        # try reading rowid from cache
        try:
            rowid = self.path_cache[path_from_root]
        except KeyError:
            rowid = -1
        #end

        #
        # try to retrieve existing row ID
        if rowid < 0:
            cur = self.con.cursor()

            cmd = f"""
            SELECT * FROM dirpaths WHERE path_from_root="{path_from_root}" """
            cur.execute(cmd)
            results = cur.fetchall()
            assert len(results) <= 1

            if len(results)==1:
                rowid = results[0][0]
                #
                # add to cache
                self.path_cache[path_from_root] = rowid
            #end
        #end

        #
        # create new table entry
        if rowid < 0:
            cmd = f"""
            INSERT INTO dirpaths(root_path, path_from_root) VALUES ("{root_dir}", "{path_from_root}")
            """
            cur.execute(cmd)
            rowid = cur.lastrowid
            self.con.commit()

            #
            # add to cache
            self.path_cache[path_from_root] = rowid
        # end

        assert rowid >= 0
        return rowid

    def commit(self):
        self.con.commit()
        return

    def extract_extension(self, fname):
        (_, ext) = os.path.splitext(fname)
        ext = ext.lower()
        return ext
    
    def insert_into_lr_files(self, path_id, fname):
        ext = self.extract_extension(fname)
        cur = self.con.cursor()
        cmd = f"""
        INSERT INTO lr_files(path_id, extension, filename) VALUES ({path_id}, "{ext}", "{fname}")"""
        cur.execute(cmd)

        return

    def insert_into_picasa_files(self, path_id, fname):
        ext = self.extract_extension(fname)
        
        cur = self.con.cursor()
        cmd = f"""
        INSERT INTO picasa_files(path_id, extension, filename) VALUES ({path_id}, "{ext}","{fname}")"""
        cur.execute(cmd)

        return

    def update_picasa_files_lr_id(self, picasa_id, lr_id):
        cmd = f"""
        UPDATE picasa_files
        SET lr_file_id={lr_id}
        WHERE picasa_files.id={picasa_id}"""

        cur = self.con.cursor()
        cur.execute(cmd)

        return

    def update_lr_files_picasa_id(self, lr_id, picasa_id):
        cmd = f"""
        UPDATE lr_files
        SET picasa_file_id={picasa_id}
        WHERE lr_files.id={lr_id}"""

        cur = self.con.cursor()
        cur.execute(cmd)

        return
    

    def get_num_db_entries(self):
        """
        return dictionary containing number of entries per auditdb table
        """
        cur = self.con.cursor()

        cmd = """SELECT * FROM lr_files"""
        cur.execute(cmd)
        results = cur.fetchall()
        num_lr = len(results)

        
        # OMIT .picasaoriginals and .converted directories!
        # OMIT non-media files, .e.g .db
        cmd = """
        SELECT picasa_files.id FROM picasa_files
        INNER JOIN dirpaths
        WHERE picasa_files.path_id = dirpaths.id
        AND dirpaths.path_from_root NOT LIKE "%picasaoriginals/"
        AND dirpaths.path_from_root NOT LIKE "%converted/"
        AND 
        """
        ext = media_ext.IGNORABLE_EXT_TUPLE[0]
        cmd = cmd + f"""picasa_files.extension NOT LIKE "{ext}" """
        for ext in media_ext.IGNORABLE_EXT_TUPLE[1:]:
            cmd = cmd + f"""AND picasa_files.extension NOT LIKE "{ext}" """
        #end
        #print(cmd)
        
        cur.execute(cmd)
        results = cur.fetchall()
        num_picasa = len(results)
        
        cmd = """
        SELECT * FROM dirpaths
        WHERE dirpaths.path_from_root NOT LIKE "%picasaoriginals/"
        AND dirpaths.path_from_root NOT LIKE "%converted/"
        """
        cur.execute(cmd)
        results = cur.fetchall()
        num_paths = len(results)

        d = {'num_paths': num_paths, 'num_lr':num_lr, 'num_picasa':num_picasa}
        return d


        
    
        
