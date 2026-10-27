import json, pathlib, sqlite3, subprocess, sys, tempfile, unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
SCRIPT=ROOT/"news_factory.py"
SAMPLE=ROOT/"samples"/"example.json"
class SmokeTest(unittest.TestCase):
    def test_import_and_approval_guard(self):
        with tempfile.TemporaryDirectory() as tmp:
            db=pathlib.Path(tmp)/"news.db"
            def run(*args):
                return subprocess.run([sys.executable,str(SCRIPT),*map(str,args)],capture_output=True,text=True)
            self.assertEqual(run("check",SAMPLE).returncode,0)
            self.assertEqual(run("import",SAMPLE,"--db",db).returncode,0)
            self.assertEqual(run("import",SAMPLE,"--db",db).returncode,0)
            con=sqlite3.connect(db)
            self.assertEqual(con.execute("select count(*) from news").fetchone()[0],1)
            self.assertEqual(con.execute("select review from news").fetchone()[0],"needs_review")
            con.close()
            self.assertNotEqual(run("draft","--date","2026-10-27","--db",db).returncode,0)
            self.assertNotEqual(run("approve","20261027-EXAMPLE","--db",db).returncode,0)
            self.assertNotEqual(run("approve","20261027-EXAMPLE","--checked","--db",db).returncode,0)
            self.assertEqual(run("report","--date","2026-10-27","--db",db).returncode,0)
if __name__=="__main__": unittest.main()
