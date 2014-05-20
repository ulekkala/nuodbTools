import unittest
import uuid
from nuodb_aws_quickstart import cluster 

config_file = "../config.json"

class nuodbQuickstartTest(unittest.TestCase):
  @classmethod  
  def setUpClass(cls):
    cluster(action="create", config_file=config_file)
  
  @classmethod
  def tearDownClass(cls):
    cluster(action="terminate", config_file=config_file)
  
  def test_membership(self):
    
    self.assertTrue(True)   

if __name__ == "__main__":
  unittest.main()