import sqlite3

"""
SELECT file.folder, file.originalFilename, folder.pathFromRoot
FROM AgLibraryFile file
INNER JOIN AgLibraryFolder folder ON file.folder==folder.id_local
WHERE folder.id_local==8520


AgLibraryRootFolder
    id_local = 11705398
    absolutePath = "/Volumes/extern-photo/picasa_snapshot_2018.08/"
    name = "picasa_snapshot_2018.08"

SELECT file.folder, file.originalFilename, folder.pathFromRoot
FROM AgLibraryFile file
INNER JOIN AglibraryFolder folder ON file.folder=folder.id_local
WHERE folder.rootFolder= (
    SELECT  root.id_local
	FROM AgLibraryRootFolder root
	WHERE root.absolutePath LIKE "%picasa_snapshot%"
	)
"""
class LrCat:
    def __init__(self, fname):
        self.con = sqlite3.connect(fname)
        self.cur = self.con.cursor()


        
    def get_picasa_root_folder_id(self, picasa_root):
        """
        return id_local, absolutePath
            where id_local integer
                  absolutePath string
        """
        cmd = "SELECT id_local, absolutePath FROM AgLibraryRootFolder WHERE absolutePath LIKE (:term)"
        search_term = f"%{picasa_root}%"  # convert into a sqlite LIKE term
        self.cur.execute(cmd, {"term":search_term})
        root_list = self.cur.fetchall()

        assert(len(root_list)==1)

        root_id = root_list[0][0]
        abs_path = root_list[0][1]
        return root_id, abs_path

    def tuple_to_dict(self,t):
        assert len(t)==3
        d = {'path_from_root': t[0],
             'folder_id': t[1],
             'original_filename': t[2]}
        return d
    
    def get_picasa_files(self, picasa_root):
        """
        result list is a list of tuples
        (pathFromRoot, folder ID, originalFilename)

        call get_picasa_root_folder_id to get the actual absolute root path

        """

        root_folder_id, abs_picasa_root = self.get_picasa_root_folder_id(picasa_root)
        
        cmd = \
        """SELECT folder.pathFromRoot, file.folder, file.originalFilename 
           FROM AgLibraryFile file 
           INNER JOIN AgLibraryFolder folder ON file.folder==folder.id_local
           WHERE folder.rootFolder==(:root_folder_id)"""
        self.cur.execute(cmd, {"root_folder_id": root_folder_id})
        tuple_list = self.cur.fetchall()

        dict_list = [self.tuple_to_dict(x) for x in tuple_list]
        
        #
        # add root path to each dict
        [x.update({'root_path':abs_picasa_root}) for x in dict_list]
        
        return dict_list

    





        

        
        
        
    
    
