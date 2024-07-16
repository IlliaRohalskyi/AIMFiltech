import subprocess
import shutil
import os
import pandas as pd

def copy_and_overwrite(from_path, to_path):
    if os.path.exists(to_path):
        shutil.rmtree(to_path)
    shutil.copytree(from_path, to_path)

print("******************************")
print("STEP 2: Processing Variantfile")

xls2 = pd.ExcelFile('Variantfile.xlsx')

mp2 = xls2.parse(xls2.sheet_names[xls2.sheet_names.index("main")])
mpd2 =dict(zip(mp2["PARAMETER"],mp2["VALUE"]))

df = xls2.parse(xls2.sheet_names[xls2.sheet_names.index("variants")])
variants_dict = df.to_dict()
n_variants = len(variants_dict["ID"])
output_data =[]

for i in range(n_variants):
    print("Processing Variant no "+str(i)+" with ID:"+str(variants_dict["ID"][i]))
    print("Generating parameter file")
    file_name = mpd2["name"] + "_variant_"+str(i)

    with open(file_name, 'w') as f:
        for key in variants_dict:
            line = str(key)+" "+str(variants_dict[key][i])+";"
            print(line, file=f)

    subprocess.run(["pyFoamClearCase.py", "."])
    arg = "--parameter-file="+file_name
    subprocess.run(["pyFoamPrepareCase.py",".",arg])
    os.remove(file_name)
    subprocess.run(["blockMesh"])
    subprocess.run(["simpleFoam"])
    output_file=mpd2["output_file"]

    with open(output_file) as of:
        for line in of:
            pass
        last_line = line
        output_data.append(last_line.split())

results_columns = []
for i in range(len(output_data[0])):
    column_name = "OUT" + str(i)
    results_columns.append(column_name)
results_df = pd.DataFrame(output_data, columns = results_columns)

output_df = pd.concat([df,results_df], axis =1)

shutil.copy("Variantfile.xlsx", "Resultfile.xlsx")
with pd.ExcelWriter('Resultfile.xlsx', engine='openpyxl', mode='a') as writer:
    output_df.to_excel(writer, sheet_name='results', index = False)
