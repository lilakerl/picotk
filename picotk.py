#!/usr/bin/python3
import sys
import os
import getopt
import subprocess
import shutil
import re
import yaml
from typing import List

VERSION = "0.0.1"
CONFIG_LOCATION = f"/home/{os.environ['USER']}/"


def run_command(command: List[str], process_name: str, standard_name: str) -> bool:
   print(f"{process_name}... ", end="", flush=True)
   out = subprocess.run(command, capture_output=True, text=True)
   if out.returncode == 0:
      print("done.")
      return True
   else:
      print(f"failed with return code {out.returncode}. {standard_name} output:\n{out.stderr}")
      return False

# ********** individual actions **********
# TODO: add command to register pico SDK location so it doesn't have to be specified every time using '-s'
def update_cmake(build_directory: str, pico_sdk_path: str) -> None:
   os.environ["PICO_SDK_PATH"] = pico_sdk_path
   return run_command(["cmake", "-S", ".", "-B", build_directory], "Updating CMake", "CMake")
def make(build_directory: str) -> None:
   return run_command(["make", "-C", build_directory], "Building", "make")


# ********** commands **********
def help() -> None:
   print(f"""
   Picotools v{VERSION}
   A suite of tools to make working with the Raspberry Pi Pico a little faster 

   Commands:
      build          Build a project
      upload         Upload a binary to the pico
      attach-sdk   Register the Pico SDK with Picotools so it knows where to find it
   """)


def build(argv: List[str]) -> None:  
   build_directory = "build"
   path_to_sdk = ""

   def print_help():
      print("Usage: picotools build [-b <build-directory>] -s <path-to-sdk>")
      print("build-directory defaults to 'build' if unspecified")

   try:
      opts, args = getopt.getopt(argv, "hb:s:", ["help", "build-directory=", "sdk-path=="])
   except getopt.GetoptError:
      print_help()
      return

   for opt, arg in opts:
      if opt in ("-h", "--help"):
         print_help()
         return
      elif opt in ("-b", "--build-directory"):
         build_directory = arg
      elif opt in ("-s", "--sdk-path"):
         path_to_sdk = arg
         if not os.path.isdir(arg):
            print(f"Given path to Pico SDK '{arg}' not found")
            return
    
   if path_to_sdk == "":
      print("No path given to Pico SDK. Please supply one using: '-s <path-to-sdk>'")
      return    
    
   if not os.path.isdir(build_directory):
      os.mkdir(build_directory)

   update_cmake(build_directory, path_to_sdk)
   make(build_directory)


def upload(argv: List[str]) -> None:
   def print_help():
      print("Usage: picotools upload -p <path-to-pico> [optional-flags]")
      print("Required arguments:")
      print("   -p, --pico-path         Path to where the Pico has mounted itself as a mass storage device")
      print("Optional arguments")
      print("   -b, --build-directory   Supply a custom build subdirectory. Defaults to 'build'")
      print("   -t, --target            The target to flash the Pico with. If unsupplied, picotools reads CMakeLists.txt and uses the name of the project there")
      print("   -B, --build-first       Build the project before uploading")

   try:
      opts, args = getopt.getopt(argv, "hb:t:p:B", ["help", "build-directory=", "target=", "pico-path=", "build-first"])   
   except getopt.GetoptError:
      print_help()
      return
   
   build_directory = "build"
   target = ""
   pico_path = ""
   build_first = False
   
   for opt, arg in opts:
      if opt in ("-h", "--help"):
         print_help()
         return
      elif opt in ("-b", "--build-directory"):
         if not os.path.isdir(f"{os.path.curdir}/{arg}"):
            print(f"Given build directory '{arg}' not found")
            return
         build_directory = arg
      elif opt in ("-t", "--target"):
         target = arg
      elif opt in ("-p", "--pico-path"):
         if not os.path.isdir(arg):
            print(f"Given path to Pico '{arg}' not found")
            return
         pico_path = arg
      elif opt in ("-B", "--build-first"):
         build_first = True

   if pico_path == "":
      print("No path supplied to Pico. Please supply one using -p")
      return

   if target == "":
      print("No target provided - checking CMakeLists.txt... ", end="", flush=True)
      # TODO: look through CMakeLists.txt
      cmake = open("CMakeLists.txt", "r")
      if cmake is None:
         print(" failed. No CMakeLists.txt found")
         return
      match = re.search(r"add_executable\((.*?) ", cmake.read())
      cmake.close()

      if match is None:
         print("failed. No 'project()' declaration found in CMakeLists.txt")
      target = match.group(1)
      print(f"done. Using target '{target}'.")

   if build_first:
      build(["-b", build_directory, "-s"])

   if not os.path.isfile(f"{os.path.curdir}/{build_directory}/{target}.uf2"):
      print(f"Could not find target UF2 in build directory (looking for '{build_directory}/{target}.uf2')")
      return
   
   print(f"Flashing '{build_directory}/{target}.uf2' to Pico at '{pico_path}'... ", end="", flush=True)
   shutil.copyfile(f"{os.path.curdir}/{build_directory}/{target}.uf2", f"{pico_path}/{target}.uf2")
   print("done.")



def attach_sdk(argv: List[str]) -> None:
   def print_help():
      print("Usage: picotools attach-sdk <path-to-sdk>")

   if len(argv) == 0:
      print("A path to the Pico SDK was not provided. Please supply one.")
      print_help()
      return
   elif len(argv) >= 2:
      print("Excessive arguments provided.")
      print_help()
      return
   else:
      path = argv[0]

      if not os.path.isdir(path):
         print(f"Invalid path supplied: '{path}'")
         return

      # TODO: add a check to make sure the path points to a Pico SDK
      config = None
      try:
         f = open(CONFIG_LOCATION + ".picotools", "r")
         config = yaml.load(f.read(), Loader=yaml.CLoader)
      except FileNotFoundError:
         pass
      if config is None:
         config = {}
      config["pico-sdk"] = path
      with open(CONFIG_LOCATION + ".picotools", "w") as f:
         f.write(yaml.dump(config))
      




def main(argv: List[str]) -> None:
   if len(argv) == 0:
      pass # print help screen
   elif argv[0] == "help":
      help()
   elif argv[0] == "build":
      build(argv[1:]) 
   elif argv[0] == "upload":
      upload(argv[1:])
   elif argv[0] == "attach-sdk":
      attach_sdk(argv[1:])

if __name__ == "__main__":
    main(sys.argv[1:])
