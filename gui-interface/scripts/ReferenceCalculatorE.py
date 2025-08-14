# ReferenceCalculatorEmma
# output moet zijn een txt bestand met:
# - motor positie
# - motor velocity
# - delta pitch

import time
import numpy as np
from ClassSensorDataProducerE import SensorDataProducer

# motor constraints
min_motorsteps = -44000
max_motorsteps = 44000
motor_range = max_motorsteps - min_motorsteps

#  wordt nu nog niet gebruikt, moet wel uiteindelijk
# motion limits -> in toekomst deze opmeten met gebruiker in plaats van aannemen
qe_min, qe_max = 0, 180    # elevation
# measured individual elevation, gotten from a json file that measures the pROM (for now i gave it a value)
elev_min = -90
elev_max = 90
qh_min, qh_max = -90, 90    # horizontal rotation
qa_min, qa_max = -90, 90    # medial axial rotation
qelbow_min, qelbow_max = -40, 110 # elbow rotation

# under this number the motor should not move because the delta pitch is too small
pitch_threshold = 5 # degrees , this value needs to be tuned as well

# E-Vari-A manipulation limits
# the E-Vari-A has a range of 44 degrees, it should raise in the range of the arm pitch being 20 and 120 degrees
start_motor = 20 
stop_motor = 120 

# gather sensor data from ClassSensorDataProducerE.py
sensor = SensorDataProducer()
input("plaats arm in houding en druk ENTER om te taren...")
sensor.tare()

# ----------------------------------------- reference position calculation
def referencePosition(pitch):
    if pitch <= start_motor:
        return min_motorsteps 
    elif pitch >= stop_motor:
        return max_motorsteps
    else:
        scale = (pitch - start_motor) / (stop_motor - start_motor)
    return int(min_motorsteps + scale * motor_range)


# ----------------------------------------- logging data
filename = 'motor_reference.txt'
with open(filename, "w") as f:
    f.write("time\tmotor_position\tmotor_velocity\tdelta_pitch\n")

prev_pitch = None
prev_time = time.time()

while True:
    data = sensor.read()
    pitch = data["pitch"]
    current_time = time.time()

    # calculate delta_pitch and with that the velocity
    if prev_pitch is not None:
        delta_pitch = pitch - prev_pitch
        dt = current_time - prev_time
        velocity = delta_pitch / dt
    else:
        delta_pitch = 0
        volocity = 0

    prev_pitch = pitch
    prev_time = current_time

    if abs(delta_pitch) > pitch_threshold:
        motor_pos = referencePosition(pitch)



    # print output
        print(f"RefPos: {motor_pos} steps | RefVel: {velocity:.2f} °/s | ΔPitch: {delta_pitch:.2f}°")

    # write to file
        with open(filename, "a") as f:
            f.write(f"{current_time:.3f}\t{motor_pos}\t{velocity:.3f}\t{delta_pitch:.3f}\n")

    time.sleep(0.01) 



