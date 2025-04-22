import os
import unittest
import pandas as pd
from src.components.openfoam_handler import OpenFoamHandler
from src.utility import get_root


class TestOpenFoamHandler(unittest.TestCase):
    def test_simulate(self):
        """
        Test the simulate method of OpenFoamHandler.
        """
        input_data = pd.DataFrame(
            {
                "asd": ["a"],
                "UIn": [1.0],
                "p": [101325],
            }
        )

        handler = OpenFoamHandler(input_data)

        handler.case_path = os.path.join(get_root(), "test", "test_openfoam_case")

        results = handler.simulate()

        self.assertEqual(results.shape[1], 7)
        self.assertIn("OUT_p_1", results.columns)
        self.assertIn("OUT_magU_1", results.columns)

if __name__ == "__main__":
    unittest.main()