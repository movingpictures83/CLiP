import argparse
import sys
import os
from os import listdir
import json
import subprocess
import shutil
import time
import threading

sys.path.insert(0,"./src/")
from plugins.CLiP.src.run_kernel_nosub import run_clip_nosub
from plugins.CLiP.src.run_kernel_sub import run_clip_sub

import PyIO
import PyPluMA


class MyArgs:
   def __init__(self):
       self.snv_input = ""
       self.cn_input = ""
       self.purity_input = ""
       self.sample_id = 'sample'
       self.subsampling = False
       self.lam = None#[0.01, 0.03, 0.05, 0.075, 0.1, 0.125, 0.15, 0.175, 0.2, 0.225, 0.25]
       self.preprocess = 'preprocess_result/'
       self.final = 'final_result/'
       self.subsample_size = 0
       self.rep_num = 0
       self.window_size = 0.05
       self.overlap_size = 0

class CLiPPlugin:
 def input(self, inputfile):
       self.parameters = PyIO.readParameters(inputfile)
 def run(self):
        pass
 def output(self, outputfile):
  args = MyArgs()
  args.snv_input = PyPluMA.prefix()+"/"+self.parameters["snv_file"]
  args.cn_input = PyPluMA.prefix()+"/"+self.parameters["cn_file"]
  args.purity_input = PyPluMA.prefix()+"/"+self.parameters["purity_file"]

  current_dir = os.path.dirname(os.path.abspath(__file__))
  run_preprocess = os.path.join(current_dir, "src/preprocess.R")

  result_dir = outputfile
  #result_dir = os.path.join(current_dir, args.sample_id)
  #if not os.path.exists(result_dir):
  #  os.makedirs(result_dir)

  path_for_preprocess = result_dir
  path_for_preliminary = result_dir
  path_for_final = result_dir

  # Run preprocess
  print("Running preprocessing...")
  p_preprocess = subprocess.Popen(["Rscript", run_preprocess, args.snv_input, args.cn_input, args.purity_input, args.sample_id, path_for_preprocess], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
  _stdout, _stderr = p_preprocess.communicate()
  if _stderr:
    print(_stderr.decode().strip())
    sys.exit()
  print("Preprocessing finished.")

  run_CliP = os.path.join(current_dir, "src/run_kernel_nosub.py")
  python_clip = os.path.join(current_dir, "src/kernel.py")
  run_postprocess = os.path.join(current_dir, "src/postprocess.R")
  run_lambda_selection = os.path.join(current_dir, "src/penalty_selection.py")

  # Run the main CliP function (without subsampling)
  print("Running the main CliP function...")
  if args.subsampling == False:
    if args.lam == None:
      start = time.time()
      t = threading.Thread(name="Running the main CliP function", target=run_clip_nosub, args=(path_for_preprocess, path_for_preliminary))
      t.start()
      t.join()
      end = time.time()
      elapsed_time = end - start
      print("\nElapsed time: %.2fsec" % elapsed_time + "\n")
		
      # Run postprocess
      p_postprocess = subprocess.Popen(["Rscript", run_postprocess, path_for_preliminary, path_for_preprocess, path_for_final, str(1)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
      _stdout, _stderr = p_postprocess.communicate()
      if _stderr:
         print(_stderr.decode().strip())
         sys.exit()
		
      # The lambda selection methods:
      p_lambda_selection = subprocess.Popen(["python3", run_lambda_selection, args.purity_input, path_for_final], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
      _stdout, _stderr = p_lambda_selection.communicate()
      if _stderr:
        print(_stderr.decode().strip())
        sys.exit()
		
    else:
      p_run_CliP = subprocess.Popen(["python3", run_CliP, path_for_preprocess, path_for_preliminary, python_clip, str(args.lam)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
      _stdout, _stderr = p_run_CliP.communicate()
      if _stderr:
         print(_stderr.decode().strip())
         sys.exit()
		
      # Run postprocess
      p_postprocess = subprocess.Popen(["Rscript", run_postprocess, path_for_preliminary, path_for_preprocess, path_for_final, str(1), str(args.lam)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
      _stdout, _stderr = p_postprocess.communicate()
      if _stderr:
        print(_stderr.decode().strip())
        sys.exit()

			
  # Run the main CliP function (with subsampling)
  else:
   subsampling_clip = os.path.join(current_dir, "src/run_kernel_sub.py")
   if args.subsample_size == None:
     sys.exit("Need an input for subsample_size")
		
   if args.rep_num == None:
     sys.exit("Need an input for rep_num")
	
   if args.lam == None:

     start = time.time()
     t = threading.Thread(name="Running the main CliP function", target=run_clip_sub, args=(path_for_preprocess, path_for_preliminary, python_clip, args.subsample_size,args.rep_num, args.window_size, args.overlap_size))
		
     t.start()
     t.join()
     end = time.time()
     elapsed_time = end - start
     print("\nElapsed time: %.2fsec" % elapsed_time + "\n")
		
     # Run postprocess
     p_postprocess = subprocess.Popen(["Rscript", run_postprocess, path_for_preliminary, path_for_preprocess, path_for_final, str(1)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
     _stdout, _stderr = p_postprocess.communicate()
     if _stderr:
       print(_stderr.decode().strip())
       sys.exit()
		
     # The lambda selection methods:
     p_lambda_selection = subprocess.Popen(["python3", run_lambda_selection, args.purity_input, path_for_final], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
     _stdout, _stderr = p_lambda_selection.communicate()
     if _stderr:
       print(_stderr.decode().strip())
       sys.exit()
		
   else:
     p_run_subsampling = subprocess.Popen(["python3", subsampling_clip, path_for_preprocess, path_for_preliminary, python_clip, str(args.subsample_size), str(args.rep_num), str(args.window_size), str(args.overlap_size), str(args.lam)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
     _stdout, _stderr = p_run_subsampling.communicate()
     if _stderr:
       print(_stderr.decode().strip())
       sys.exit()
		
     # Run postprocess
     p_postprocess = subprocess.Popen(["Rscript", run_postprocess, path_for_preliminary, path_for_preprocess, path_for_final, str(1), str(args.lam)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
     _stdout, _stderr = p_postprocess.communicate()
     if _stderr:
       print(_stderr.decode().strip())
       sys.exit()

  #shutil.rmtree(path_for_preliminary)

  print("Main CliP function finished.")


