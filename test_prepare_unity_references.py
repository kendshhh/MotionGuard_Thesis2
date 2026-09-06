import unittest

from prepare_unity_references import has_valid_feature_frames


def make_frames(count=18, values=None):
    values = values or [0.1, 0.2, 0.3, 0.4, 0.5]
    return [{"values": list(values)} for _ in range(count)]


class PrepareUnityReferencesTests(unittest.TestCase):
    def test_accepts_complete_five_feature_sequence(self):
        self.assertTrue(has_valid_feature_frames(make_frames()))

    def test_rejects_sequence_shorter_than_minimum(self):
        self.assertFalse(has_valid_feature_frames(make_frames(17)))

    def test_rejects_wrong_feature_dimension(self):
        self.assertFalse(has_valid_feature_frames(make_frames(values=[0.1, 0.2, 0.3, 0.4])))

    def test_rejects_non_finite_feature(self):
        self.assertFalse(has_valid_feature_frames(make_frames(values=[0.1, 0.2, float("nan"), 0.4, 0.5])))


if __name__ == "__main__":
    unittest.main()