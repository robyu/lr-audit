import unittest
import lrcat
import correlate

class TestAll(unittest.TestCase):
    def test_smoke(self):
        self.assertTrue(True)

    def test_query_picasa_root_folder(self):
        lrdb = lrcat.LrCat('./2021-08-10/lightroom-catalog-2.lrcat')
        ret=lrdb.get_picasa_root_folder_id('picasa_snapshot_2018.08')
        print(ret)
        self.assertTrue(ret[0]==11705398)

    def test_query_all_picasa_files(self):
        lrdb = lrcat.LrCat('./2021-08-10/lightroom-catalog-2.lrcat')
        dict_list = lrdb.get_picasa_files('picasa_snapshot_2018.08')
        self.assertTrue(len(dict_list)==96530)
        print(dict_list[0])

    def test_corr_smoketest(self):
        corr = correlate.Correlate("corr.db")
        self.assertTrue(True)

    def test_corr_populate_tables(self):
        corr = correlate.Correlate("corr.db", drop_flag=True)
        corr.populate_from_lrcat('./2021-08-10/lightroom-catalog-2.lrcat')
        self.assertTrue(True)
        
if __name__=='__main__':
    unittest.main()
    
