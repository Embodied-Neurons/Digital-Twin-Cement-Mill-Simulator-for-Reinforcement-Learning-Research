import json

class HardnessController:
# Możliwa optymalizacja: Wyszukiwanie binarne

    def __init__(self, initial_hardness, hardness_data_path = "hardnessData.json"):
        self.initial_hardness = initial_hardness
        if hardness_data_path is None:
            self.segments = []
        else:
            with open(hardness_data_path, "r") as f:
                data = json.load(f)
            self.segments = sorted([(s["start_time"], s["end_time"], s["start_hardness"], s["end_hardness"]) for s in data["shift_schedule"]], key=lambda s: s[0])
        print(f"Loaded hardness segments: {self.segments}")

    def get_hardness(self, t) -> float:
        hardness = self.initial_hardness

        for start_t, end_t, start_hardness, end_hardness in self.segments:
            if t < start_t:
                return hardness

            if start_t <= t <= end_t:
                if end_t == start_t:
                    return end_hardness

                ratio = (t - start_t) / (end_t - start_t)
                return start_hardness + ratio * (end_hardness - start_hardness)

            hardness = end_hardness

        return hardness

controller = HardnessController(initial_hardness=1.0, hardness_data_path=None)  # Replace None with the path to your hardnessData.json if needed
for i in range(60):
    print(f"Time: {i} min, Hardness: {controller.get_hardness(i)}")
