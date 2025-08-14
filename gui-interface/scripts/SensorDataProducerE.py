# SensorDataProducerEmma
# return: quaternions, euler: yaw, pitch, roll, elbow angle

import busio, board, time
import numpy as np
import smbus2 as smbsus # dit moet veranderen naar smbus > geen 2 

from scipy.spatial.transform import Rotation as R

from adafruit_bno08x import BNO_REPORT_GAME_ROTATION_VECTOR
from adafruit_bno08x.i2c import BNO08X_I2C

# ----------------------------------- configuration IMU BNO085
i2c = busio.I2C(board.SCL, board.SDA)
bno = BNO08X_I2C(i2c)

bno.enable_feature(BNO_REPORT_GAME_ROTATION_VECTOR)

# ------------------------------------ processing IMU data
# q_rel = q_tare^-1 x q_cur

# q_tare^1 is the complex conjugate quaternion at the moment of tare
def tareQuat(w, x, y, z):
    return np.array([w, -x, -y, -z])

# q_rel multiplication -> q_rel = q_tare^-1 x q_cur with (q = q_cur)
def applyTare(tare_q, q):
    w1, x1, y1, z1 = tare_q
    w2, x2, y2, z2 = q
    w = w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2
    x = w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2
    y = w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2
    z = w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2
    return np.array([w, x, y, z]) / np.linalg.norm([w, x, y, z])

# quaternion to Euler
def quaternionToEuler(q, degrees=False):
    r = R.from_quat([q[1], q[2], q[3], q[0]]) # scipy has (x, y, z, w), returns yaw, pitch, roll
    return r.as_euler('zyx', degrees=degrees)

# Euler angles from tare position
def relativeEuler(tare_q, cur_q, degrees=True):
    rel_q = applyTare(tare_q, cur_q)
    yaw, pitch, roll = quaternionToEuler(rel_q, degrees=degrees)
    return yaw, pitch, roll


# ------------------------------------------ configuration Encoder AS5600
I2C_BUS = 2
BUS = smbsus.SMBus(I2C_BUS)
AS5600_I2C_ADDR = 0x36

AS5600_ANGLE_REG = 0x0E             # register for angle result (between 0-350grad)
AS5600_RAW_ANGLE_REG = 0x0C         # register for raw angle data (0-4095 steps = 0-360grad)
AS5600_STATUS_REG = 0x0B            # register with statusbits (if the magnet is placed correctly)
AS5600_CONF_REG = 0x07              # configuration adress (first byte from 2 for sensorsettings)
AS5600_CONF_BYTE1 = 0b00000000      # first configuratiebyte (filtersettings)
AS5600_CONF_BYTE2 = 0b00000001      # second configuratiebyte (activates continuous mode)

def configureEncoder():
    BUS.write_byte_data(AS5600_I2C_ADDR, AS5600_CONF_REG, AS5600_CONF_BYTE1)
    time.sleep(0.01)
    BUS.write_byte_data(AS5600_I2C_ADDR, AS5600_CONF_REG+1, AS5600_CONF_BYTE2)
    time.sleep(0.01)

def readAngle():
    try:
        byte1 = BUS.read_byte_data(AS5600_I2C_ADDR, AS5600_RAW_ANGLE_REG)
        byte2 = BUS.read_byte_data(AS5600_I2C_ADDR, AS5600_RAW_ANGLE_REG + 1)
        angle = ((byte1 << 8) | byte2) & 0x0FFF
        return angle * (360/4096) # in degrees -> 360/4096 = 0.087890625
    except OSError:
        return None
    
def checkMagnet():
    try:
        status = BUS.read_byte_data(AS5600_I2C_ADDR, AS5600_STATUS_REG)
        return (status & 0x20) == 0x20 # magnet is correctly placed
    except OSError:
        return False
    

# ---------------------------------------------- tare functionality
configureEncoder()
elbow_angle_tare = readAngle()
print(f"Elbow angle tared at: {elbow_angle_tare:.2f} degrees ")
tareCommand = input("Do you want to tare the IMU orientation? (y/n)")
if tareCommand.lower() == 'y':
    print("Taring IMU orientation ...")
    quat_i, quat_j, quat_k, quat_real = bno.game_quaternion
    imu_tare_q = tareQuat(quat_real, quat_i, quat_j, quat_k)
else:
    imu_tare_q = np.arary([1, 0, 0, 0]) # identity quaternion
