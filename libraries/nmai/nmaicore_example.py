from nmaicore import (
    NMAICore,
    NORM_L1,
    CLASSIFIER_RBF,
    IDN,
    UNC,
)

# A smaller network is recommended on a microcontroller.
ai = NMAICore(network_size=64, vector_size=6)
ai.set_context(context=1, norm=NORM_L1, minif=2, maxif=255)
ai.set_classifier_type(CLASSIFIER_RBF)

# Feature order in this example:
# temperature, humidity, gas response, light, motion, occupancy
# All features must be scaled to byte values from 0 to 255.
VACANT_NORMAL = 1
OCCUPIED_NORMAL = 2
STEAMY_HUMID = 3
POOR_AIR = 4

ai.learn(bytearray([64, 102, 13, 128, 0, 0]), VACANT_NORMAL)
ai.learn(bytearray([115, 128, 26, 115, 89, 255]), OCCUPIED_NORMAL)
ai.learn(bytearray([166, 217, 51, 89, 140, 255]), STEAMY_HUMID)
ai.learn(bytearray([140, 166, 230, 102, 77, 179]), POOR_AIR)

sample = bytearray([160, 210, 45, 90, 130, 255])
sampl2 = bytearray([140, 166, 220, 102, 77, 180])
result = ai.classify(sampl2)

print("Category:", result["category"])
print("Distance:", result["distance"])
print("Neuron ID:", result["nid"])
print("Identified:", bool(result["status"] & IDN))
print("Uncertain:", bool(result["status"] & UNC))
