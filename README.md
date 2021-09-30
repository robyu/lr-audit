
# Lightroom-Picasa Audit Tool

This tool reads a lightroom catalog, walks a Picasa photo directory, and generates
a report to identify whether the lightroom catalog is missing any files.

Notes:
1. The unregistered file count in 'report' is misleading, because it counts media files in the picasa dir
which have already been converted & registered in LR, 
```
e.g. foo.avi converted to foo.mp4
             copied to ./converted/foo.avi             
```
but then foo.avi was subsequently regenerated again when I tried to fix picasa_snapshot*.

2. The report-vid statement, however, seems to be correct (and currently shows 0 unregistered videos).

**Audit Usage**


Read the lightroom catalog, select the picasa-based image files, and store them in a database.
```
chuyu@ryu-mac:lr-audit$ python audit.py read-lrcat
..................................................................................................
stats: {'num_paths': 7913, 'num_lr': 96530, 'num_picasa': 0}
```

Walk the picasa directory and store them in the database. Also do a correlation
analysis, which matches LR files with picasa files and vice versa.
```
chuyu@ryu-mac:lr-audit$ python audit.py walk-picasa-dir
........................................................................................................................
walk_picasa_dir processed 108658 files
stats: {'num_paths': 9046, 'num_lr': 96530, 'num_picasa': 108293}
correlate found 102592 matches
Correlation Analysis Complete
```

Generate a summary report:
```
chuyu@ryu-mac:lr-audit$ python audit.py summary
DATABASE STATS
==============
Number of paths in picasa: 9046

Number of files in picasa:     108293
Number of entries in LR db:  -  96530
                             -----------------
Unmatched entries               11763

SUMMARY
=======
Identified 12138 files missing in Lightroom
across 1384 directory paths
```

Generate a detailed report: per directory, report the number of
picasa files which are NOT registered in lightroom.
```
chuyu@ryu-mac:lr-audit$ python audit.py report
Unmatched entries               13179
| index/total | path                                                                             | #reg | totl |      % | cum missing  |
| -----/----- | -------------------------------------------------------------------------------- | ---- | ---- | -----% | ----------   |
|     4/  838 | 1990s/1996-Arizona/                                                              |    6 |    7 | 85.71% |            1 |
```

Generate a missing-video report: for each video file V in picasa,
check whether V or a converted variant (V.mp4) is registered in lightroom.
```
chuyu@ryu-mac:lr-audit$ python  audit.py report-vids        
searching 9707 video files                          
Unregistered files:                                                                                                   
                                                                                                                      
|      1 | 2003/2003.08-ourhouse/IMGP0013.mp4                                                                                       |
|      2 | 2006/2006.03.26-xxxxxxxxxxx/IMGP3405.mp4                                                                                 |

```

** Convert Usage **

convert_media.py converts unsupported media into .jpg (images) or .mp4 (videos).

Use -p to specify a partial path (a subidrectory).
By default, convert_media will list any candidate media files which need converting and then stop.

Then return the command with -X to "execute" the conversion.
```
$ python convert_media.py -p 2008/2008.07.22

convert all
candidates:  35 files
candidates:  1 files (after filtering)
1/1 video convert {'fname': 'Video_072208_001.3gp', 'extension': '.3gp', 'root_path': '/Volumes/extern-photo/picasa_snapshot_2018.08', 'path_from_root': '2008/2008.07.22-fdjflksadsda/'}

$ python convert_media.py -p 2008/2008.07.22 -X

convert all
candidates:  35 files
candidates:  1 files (after filtering)
SUCCESS: converted /Volumes/extern-photo/picasa_snapshot_2018.08/2008/2008.07.22-fdskljfsldfsad/.converted/Video_072208_001.3gp
```
