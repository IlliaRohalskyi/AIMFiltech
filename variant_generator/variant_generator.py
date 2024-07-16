print("Loading masterfile in xls")

import pandas as pd
import shutil
import random
import itertools
print("******************************")
print("STEP 1: Processing Masterfile")

print("Reading Masterfile")
xls = pd.ExcelFile('Masterfile.xlsx')
print("Reading master parameters")
mp = xls.parse(xls.sheet_names[xls.sheet_names.index("main")])
mpd =dict(zip(mp["PARAMETER"],mp["VALUE"]))

def random_generator(par):
    match par["DISTRIBUTION"]:
        case "uniform":
            return random.uniform(par["MIN"],par["MAX"])
        case "normal":
            value =  random.normalvariate(par["MU"],par["SIGMA"])
            if par["LIMITS"] == "YES":
                value = max(par["MIN"],min(value,par["MAX"]))
            return value

def cartesian_generator(par):
    match par["TYPE"]:
        case "arithmetic_progress":
            min_value = par["MIN"]
            max_value = par["MAX"]
            N = int(par["N"])
            start = min_value
            inc = (max_value - min_value)/(N-1)
            list = [start + inc* m for m in range(N)]
            return list
        case "geometric_progress":
            min_value = par["MIN"]
            max_value = par["MAX"]
            N = int(par["N"])
            start = min_value
            q = (max_value / min_value)**(1/(N-1))
            list = [start * q ** m for m in range(N)]
            list[-1] = max_value # to get the exact max_value at the end
            return list
        case "manual":
            list = par["MANUAL"].split(";")
            return [float(i) for i in list]

mode = mpd["mode"]

match mode:
    case "manual":
        print("Working in manual mode")
        variant_df = xls.parse(xls.sheet_names[xls.sheet_names.index("par-manual")])

    case "random":
        print("working in random mode")
        N_random = mpd["N_random"]
        print("Preparing " +str (N_random) + " random variants")
        random_df = xls.parse(xls.sheet_names[xls.sheet_names.index("par-random")])
        print(random_df)
        variables = list(random_df["VARIABLE"])
        variant_columns = ["ID"] + variables
        variant_df = pd.DataFrame(columns = variant_columns)
        for i in range(N_random):
            variant_row = []
            variant_row.append(i)
            for number, name in enumerate(variables):
                variable_params = random_df.loc[number]
                value = random_generator(variable_params)
                variant_row.append(value)
            variant_df.loc[-1] = variant_row
            variant_df.index +=1

    case "cartesian":
        print("working in cartesian mode")
        cartesian_df = xls.parse(xls.sheet_names[xls.sheet_names.index("par-cartesian")])
        variables = list(cartesian_df["VARIABLE"])
        variables_n = len(variables)
        variant_columns = ["ID"] + variables
        variant_df = pd.DataFrame(columns = variant_columns)
        #Preparing lists of variable nodes
        master_value_list = []
        for number, name in enumerate(variables):
            variable_params = cartesian_df.loc[number]
            value_list = cartesian_generator(variable_params)
            master_value_list.append(value_list)

        #Preparing cartesian product
        variant_value_list = []
        for element in itertools.product(*master_value_list):
            variant_value_list.append(element)
        N_cartesian = len(variant_value_list)

        #Generating variant list
        for i in range(N_cartesian):
            variant_row = []
            variant_row.append(i)
            for number, name in enumerate(variables):
                variant_row.append(variant_value_list[i][number])
            variant_df.loc[-1] = variant_row
            variant_df.index +=1

shutil.copy("Masterfile.xlsx", "Variantfile.xlsx")
with pd.ExcelWriter('Variantfile.xlsx', engine='openpyxl', mode='a') as writer:
    variant_df.to_excel(writer, sheet_name='variants', index = False)

