import auditdb
import media_ext
import os

class Analyzer:
    def __init__(self):
        self.adb = auditdb.AuditDb()
        return

    def path_tuple_to_dict(self, pt):
        pd = {'id':pt[0], 'path_from_root':pt[1]}
        return pd

    
    def picasa_count_files_in_path(self,path_id):
        """
        given path_id, count total number of files
        in picasa_files which in the path
        """
        cur = self.adb.con.cursor()
        cmd = f"""
        SELECT COUNT(*)
        FROM picasa_files
        WHERE path_id={path_id}"""
        cur.execute(cmd)
        count_tuple = cur.fetchone()
        return count_tuple[0]

    def picasa_count_files_registered_in_lr(self, path_id):
        """
        given path_id, count the number of files
        in picasa_files which are also registered in lr
        """
        cur = self.adb.con.cursor()
        cmd = f"""
        SELECT COUNT (*)
	FROM picasa_files
	WHERE path_id={path_id} AND lr_file_id IS NOT NULL"""
        cur.execute(cmd)
        count_tuple = cur.fetchone()
        return count_tuple[0]
    

    def print_missing_path_header(self):
        print(f"""| {"index":5s}/{"total":5s} | {"path":80s} | {"#reg":4s} | {"totl":4s} | {"   ":5s}% | {"cum missing":12s} |""")
        print(f"""| {5*'-':5s}/{    5*'-':5s} | {80*'-':80s} | { 4*'-':4s} | { 4*'-':4s} | {5*'-':5s}% | {       10*'-':12s} |""")
        return
    
    def print_missing_path(self, path_dict, num_path_files, num_registered_files, count, num_missing_paths, year_cum_missing_files):
        """
        path dict is:
        'id' = id of path
        'path_from_root'  = text representation of path
        """
        percent_registered = 100 * num_registered_files/num_path_files
        
        print(f"| {count:5d}/{num_missing_paths:5d} | {path_dict['path_from_root']:80s} | {num_registered_files:4d} | {num_path_files:4d} | {percent_registered:5.2f}% | {year_cum_missing_files:12d} |")

        return

    def print_missing_file_header(self):
        print(f"""| {"index":5s}/{"total":5s} | {"ext":5s} | {"path_from_root":40s} | {"filename":20s} |""")
        print(f"""| {  5*'-':5s}/{  5*'-':5s} | {5*'-':5s} | {          40*'-':40s} | {    20*'-':20s} |""")
        
    def print_missing_file(self, file_dict, num_files, count):
        """
        file_dict definition: see file_tuple_to_dict
        """
        extension = file_dict['extension']
        path_from_root = file_dict['path_from_root']
        filename = file_dict['filename']
        print(f"""| {count:5d}/{num_files:5d} | {extension:5s} | {path_from_root:40s} | {filename:20s} |""")
        return
              
    

    def print_db_stats(self):
        print("DATABASE STATS")
        print("==============")
        d = self.adb.get_num_db_entries()
        
        num_picasa = d['num_picasa']
        num_lr = d['num_lr']
        num_paths = d['num_paths']
        
        print(f"Number of paths in picasa: {num_paths}")
        print("")
        print(f"Number of media in picasa:     {num_picasa:>6d} (omit hidden dirs)")
        print(f"Number of entries in LR db:  - {num_lr:>6d}")
        print(f"                             -----------------")
        print(f"Unmatched entries              {num_picasa-num_lr:>6d}")
        return
        
    def print_path_summary(self, num_missing_paths, total_num_path_files, total_num_registered_files):
        print( "")
        print( "SUMMARY")
        print( "=======")
        print(f"Identified {total_num_path_files - total_num_registered_files} files missing in Lightroom")
        print(f"across {num_missing_paths} directory paths")
        

    def generate_query_unsupported_extensions(self, tablename):
        cmd = f"""
        SELECT  DISTINCT extension FROM {tablename}
        INNER JOIN dirpaths
        WHERE dirpaths.id=={tablename}.path_id
        AND dirpaths.path_from_root NOT LIKE "%picasaoriginals/"
        AND dirpaths.path_from_root NOT LIKE "%converted/"
        AND (
        """
        ext = media_ext.UNSUPPORTED_VIDEO_EXT_TUPLE[0]
        cmd = cmd + f"""{tablename}.extension="{ext}" """
        
        for ext in media_ext.UNSUPPORTED_VIDEO_EXT_TUPLE[1:] + media_ext.UNSUPPORTED_IMAGE_EXT_TUPLE:
            cmd = cmd + f"""OR {tablename}.extension="{ext}" """
        #end
        cmd = cmd + """)"""
        return cmd

    def generate_query_all_picasa_extensions(self, tablename):
        cmd = f"""
        SELECT  DISTINCT extension FROM {tablename}
        INNER JOIN dirpaths
        WHERE dirpaths.id=={tablename}.path_id
        AND dirpaths.path_from_root NOT LIKE "%picasaoriginals/"
        AND dirpaths.path_from_root NOT LIKE "%converted/"
        """
        return cmd
        
    def print_ext_report(self):
        """
        search thru picasa_files for file extensions marked as non-LR-compatible
        return list of extensions
        """
        cur = self.adb.con.cursor()
        cmd = self.generate_query_all_picasa_extensions("picasa_files")
        cur.execute(cmd)
        result_list = cur.fetchall()

        print("")
        print("ALL PICASA FILE EXTENSIONS")
        print("- excluding dot directories")
        print("===================================")
        for ext in result_list:
            print(f"{ext[0]} ",end='')
        #end
        print("")

        print("")
        print("UNHANDLED PICASA FILE EXTENSIONS")
        print("- excluding dot directories")
        print("- exclude ignored extensions")
        print("- exclude image extensions")
        print("- exclude video extensions")
        print("===================================")
        for ext in result_list:
            if ( (ext[0] in media_ext.IGNORABLE_EXT_TUPLE) or
                 (ext[0] in media_ext.SUPPORTED_VIDEO_EXT_TUPLE) or
                 (ext[0] in media_ext.SUPPORTED_IMAGE_EXT_TUPLE) ):
                pass
            else:
                print(f"{ext[0]} ",end='')
            #end
        #end

        print("")
        cmd = self.generate_query_unsupported_extensions("lr_files")
        cur.execute(cmd)
        result_list = cur.fetchall()

        print("")
        print("LR DB UNDESIRABLE EXTENSIONS")
        print("===================================")
        for ext in result_list:
            print(f"{ext[0]} ",end='')
        #end
        print("")
        
        return result_list

    def print_summary(self):
        self.print_db_stats()
        self.print_ext_report()

    def report(self, print_table=True, subdir=""):
        """
        print table of picasa files and corresponding LR files
        
        specify subdir="" for all paths
        or sqlite "like" term for filtering, e.g. "1999"
        """
        self.print_db_stats()
        
        cur=self.adb.con.cursor()
        cmd = f"""
        SELECT DISTINCT dirpaths.id, dirpaths.path_from_root 
	FROM dirpaths
	INNER JOIN picasa_files 
          WHERE picasa_files.path_id==dirpaths.id 
          AND picasa_files.lr_file_id IS NULL
          AND dirpaths.path_from_root LIKE "{subdir}%"
          AND dirpaths.path_from_root NOT LIKE "%picasaoriginals/"
          AND dirpaths.path_from_root NOT LIKE "%originals/"
          AND dirpaths.path_from_root NOT LIKE "%converted/"
        """
        # ext = media_ext.IGNORABLE_EXT_TUPLE[0]
        #cmd = cmd + f"""picasa_files.extension != "{ext}" """
        for ext in media_ext.IGNORABLE_EXT_TUPLE:
            cmd = cmd + f"""AND picasa_files.extension != "{ext}" """
        #end
        #cmd = cmd + f""") """
        
        cmd = cmd + """
        ORDER BY dirpaths.path_from_root
        """
        #print(cmd)
        
        cur.execute(cmd)
        missing_path_list = cur.fetchall()
        num_missing_paths = len(missing_path_list)

        total_num_path_files = 0
        total_num_registered_files = 0

        if print_table:
              self.print_missing_path_header()
        #end
              
        curr_year = ''
        path_count = 1
        for missing_path in missing_path_list:
            path_dict = self.path_tuple_to_dict(missing_path)

            num_path_files = self.picasa_count_files_in_path(path_dict['id'])
            num_registered_files = self.picasa_count_files_registered_in_lr(path_dict['id'])
            total_num_path_files += num_path_files
            total_num_registered_files += num_registered_files

            #
            # cumulative per-year totals
            path_year = (path_dict['path_from_root'].split('/'))[0]
            if path_year != curr_year:
                curr_year = path_year
                year_cum_missing_files = 0
                print("")
            #end
            year_cum_missing_files += (num_path_files - num_registered_files)
            #
            
            if print_table:
                self.print_missing_path(path_dict,
                                        num_path_files,
                                        num_registered_files,
                                        path_count,
                                        num_missing_paths,
                                        year_cum_missing_files)
            path_count += 1
        #end

        self.print_path_summary(num_missing_paths, total_num_path_files, total_num_registered_files)


    def video_tuple_to_dict(self, vt):
        fd = {'dirpath_id': vt[0],
              'root_path': vt[1],
              'path_from_root': vt[2],
              'picasa_id': vt[3],
              'extension': vt[4],
              'lr_file_id': vt[5],
              'filename': vt[6]}
        return fd

    def make_alternate_video_names(self, vd):
        """
        generate a list of dictionaries with alternate video names 
        each list entry is a dict (path_from_root, filename)
        """
        avd_list = []

        # first we get rid of ".converted" in the path (if it exists)
        path_from_root = vd['path_from_root']
        if ".converted/" in path_from_root:
            path_from_root = path_from_root.replace('.converted/','')
            assert path_from_root[-1]=="/"   # ends with /

            avd_list.append({'path_from_root':path_from_root, 'filename':vd['filename']})
        #end


        # extension -> .mp4
        # dont bother checking if the extension is an unsupported type. just replace it with 'mp4'
        orig_ext = vd['filename'][-4:]
        alt_fname = vd['filename'].replace(orig_ext, ".mp4")
        avd_list.append({'path_from_root':path_from_root, 'filename':alt_fname})

        return avd_list

    def query_lr_exist(self, cur, path_from_root, fname):
        cmd = f"""
        SELECT COUNT (*) FROM lr_files
        INNER JOIN dirpaths
        WHERE dirpaths.id==lr_files.path_id
        AND lr_files.filename=="{fname}"
        AND dirpaths.path_from_root=="{path_from_root}" 
        """
        cur.execute(cmd)
        result_list = cur.fetchall()
        assert result_list[0][0] in [0,1]   
        return result_list[0][0]==1

    def generate_query_all_video_entries(self, tablename, subdir=""):
        cmd = f"""
        SELECT dirpaths.id, dirpaths.root_path, dirpaths.path_from_root, {tablename}.id, {tablename}.extension, {tablename}.lr_file_id, {tablename}.filename  
        FROM {tablename}
        INNER JOIN dirpaths
        WHERE {tablename}.path_id=dirpaths.id
        AND dirpaths.path_from_root LIKE "{subdir}%"
        AND dirpaths.path_from_root NOT LIKE "%/.picasaoriginals/"
        """
        cmd = cmd + f"""AND ({tablename}.extension="{media_ext.ALL_VIDEO_EXT_TUPLE[0]}" """
        for ext in media_ext.ALL_VIDEO_EXT_TUPLE[1:]:
            cmd = cmd + f"""OR {tablename}.extension="{ext}" """
        #end
        cmd = cmd + """)"""
        cmd = cmd + """ORDER BY dirpaths.path_from_root"""
        return cmd
        

    def report_unregistered_videos(self, subdir=""):
        """
        print table of picasa files and corresponding LR files
        
        specify subdir="" for all paths
         or sqlite "like" term for filtering, e.g. "1999"
        """
        cur=self.adb.con.cursor()
        cmd = self.generate_query_all_video_entries("picasa_files",subdir=subdir)
        #print(cmd)
        
        cur.execute(cmd)
        video_file_list = cur.fetchall()
        num_video_files = len(video_file_list)

        print(f"searching {num_video_files} video files")
        print("Picasa videos which are unregistered in LR:")
        print()
        count = 0
        for v in video_file_list:
            vd = self.video_tuple_to_dict(v)
            partial_path = os.path.join(vd['path_from_root'],vd['filename'])
            if vd['lr_file_id']:
                #print(f"LR registered: {partial_path}")
                pass
            else:
                #print(f"Unregistered: {partial_path}")
                alt_vd_list = self.make_alternate_video_names(vd)
                found_flag = False
                for avd in alt_vd_list:
                    exists_flag = self.query_lr_exist(cur, avd['path_from_root'], avd['filename'])  # query LR for variant
                    alt_partial_path = os.path.join(avd['path_from_root'],avd['filename'])
                    if exists_flag:
                        #print(f"{partial_path} registered as {alt_partial_path}")
                        found_flag = True
                        break # stop searching
                    #end
                #end
                if found_flag==False:
                    count = count + 1
                    print(f"""| {count:6d} | {partial_path:120s} |""")
                #end
            #end
        #end
        if count==0:
            print("no unregistered video files found")
        
                        
                    
                    
                
