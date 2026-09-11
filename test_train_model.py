import csv
import os
import shutil
import tempfile
import unittest

from train_model import (
    CSV_HEADERS,
    FOLD_CSV_HEADERS,
    cross_validate,
    init_empty_accuracy_csv,
    save_training_accuracy_csv,
)


class TrainModelCsvTests(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.csv_path = os.path.join(self.test_dir, "training_accuracy_results.csv")
        self.fold_csv_path = os.path.join(self.test_dir, "training_accuracy_folds.csv")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_init_empty_accuracy_csv(self):
        init_empty_accuracy_csv(self.csv_path)
        self.assertTrue(os.path.isfile(self.csv_path))
        with open(self.csv_path, mode="r", encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader)
            self.assertEqual(header, CSV_HEADERS)

    def test_save_training_accuracy_csv_creates_and_populates(self):
        mock_model = {
            "Punch": {
                "num_samples": 10,
                "confidence_threshold": 0.85,
                "quality_score": 0.92,
                "reference_sequence_frames": 24,
                "cross_validation": {
                    "mean_accuracy": 0.9450,
                    "std_accuracy": 0.0120,
                    "min_accuracy": 0.9330,
                    "max_accuracy": 0.9570,
                    "fold_accuracies": [0.9450, 0.9330, 0.9570],
                    "folds": 3,
                },
            },
            "Block": {
                "num_samples": 8,
                "confidence_threshold": 0.80,
                "quality_score": 0.88,
                "reference_sequence_frames": 20,
                "cross_validation": {
                    "mean_accuracy": 0.9120,
                    "std_accuracy": 0.0210,
                    "min_accuracy": 0.8910,
                    "max_accuracy": 0.9330,
                    "fold_accuracies": [0.9120, 0.8910, 0.9330],
                    "folds": 3,
                },
            },
        }

        rows = save_training_accuracy_csv(
            mock_model,
            csv_paths=self.csv_path,
            fold_csv_paths=self.fold_csv_path,
            run_id="RUN-TEST-001",
            timestamp="2026-09-11T15:40:00",
        )

        self.assertEqual(len(rows), 3)  # Punch, Block, and OVERALL_AVERAGE

        # Verify summary CSV file
        self.assertTrue(os.path.isfile(self.csv_path))
        with open(self.csv_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            file_rows = list(reader)

        self.assertEqual(len(file_rows), 3)
        self.assertEqual(file_rows[0]["technique"], "Punch")
        self.assertEqual(file_rows[0]["run_id"], "RUN-TEST-001")
        self.assertEqual(file_rows[0]["mean_accuracy"], "0.9450")
        self.assertEqual(file_rows[0]["mean_accuracy_pct"], "94.50%")
        self.assertEqual(file_rows[0]["samples_count"], "10")
        self.assertEqual(file_rows[0]["status"], "SUCCESS")

        self.assertEqual(file_rows[1]["technique"], "Block")
        self.assertEqual(file_rows[1]["mean_accuracy"], "0.9120")

        self.assertEqual(file_rows[2]["technique"], "OVERALL_AVERAGE")
        self.assertEqual(file_rows[2]["samples_count"], "18")
        self.assertAlmostEqual(float(file_rows[2]["mean_accuracy"]), (0.9450 + 0.9120) / 2, places=4)

        # Verify fold details CSV file
        self.assertTrue(os.path.isfile(self.fold_csv_path))
        with open(self.fold_csv_path, mode="r", encoding="utf-8") as f:
            fold_reader = csv.DictReader(f)
            fold_file_rows = list(fold_reader)

        self.assertEqual(len(fold_file_rows), 6)  # 3 folds each for Punch and Block
        self.assertEqual(fold_file_rows[0]["fold_index"], "1")
        self.assertEqual(fold_file_rows[0]["technique"], "Punch")
        self.assertEqual(fold_file_rows[0]["fold_accuracy"], "0.9450")

    def test_save_training_accuracy_csv_appends_subsequent_runs(self):
        mock_model = {
            "Punch": {
                "num_samples": 10,
                "confidence_threshold": 0.85,
                "quality_score": 0.92,
                "reference_sequence_frames": 24,
                "cross_validation": {
                    "mean_accuracy": 0.9450,
                    "std_accuracy": 0.0120,
                    "min_accuracy": 0.9330,
                    "max_accuracy": 0.9570,
                    "fold_accuracies": [0.9450, 0.9330, 0.9570],
                    "folds": 3,
                },
            }
        }

        # Run 1
        save_training_accuracy_csv(
            mock_model,
            csv_paths=self.csv_path,
            fold_csv_paths=self.fold_csv_path,
            run_id="RUN-1",
        )
        # Run 2
        save_training_accuracy_csv(
            mock_model,
            csv_paths=self.csv_path,
            fold_csv_paths=self.fold_csv_path,
            run_id="RUN-2",
        )

        with open(self.csv_path, mode="r", encoding="utf-8") as f:
            file_rows = list(csv.DictReader(f))

        self.assertEqual(len(file_rows), 2)
        self.assertEqual(file_rows[0]["run_id"], "RUN-1")
        self.assertEqual(file_rows[1]["run_id"], "RUN-2")


if __name__ == "__main__":
    unittest.main()
