from PyFoam.Applications.Runner import Runner

# Replace 'path/to/your/OpenFOAM/case' with the actual path to your case folder
case_folder = 'cavity'

# Initialize PyFoamRunner
runner = Runner(args=["pisoFoam", "/asdsaasd/", "cavity"])

# Run the OpenFOAM commands
runner.start()
