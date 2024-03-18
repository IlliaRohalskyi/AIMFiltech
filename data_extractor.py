from PyFoam.Applications.Runner import Runner
import subprocess

runner = Runner(args=["pisoFoam", "-case", "cavity"])