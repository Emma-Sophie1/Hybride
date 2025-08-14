# SensorDataProduce Emma using Class
# using classes to let the scripts communicate easily

import busio, board, time
import numpy as np
import smbus2 as smbus # dit moet veranderen naar smbus > geen 2 

from scipy.spatial.transform import Rotation as R

from adafruit_bno08x import BNO_REPORT_GAME_ROTATION_VECTOR
from adafruit_bno08x.i2c import BNO08X_I2C

class SensorDataProducer:
    def __init__(self, i2c_bus_number=2):
        # IMU setup
        self.i2c = busio.I2C(board.SCL, board.SDA)
        self.bno = BNO08X_I2C(self.i2c)
        self.bno.enable_feature(BNO_REPORT_GAME_ROTATION_VECTOR)

        # state
        self.running = False
        self.last_sample = {"yaw": 0.0, "pitch": 0.0, "roll": 0.0}
        self.last_tare_ts = None

        # encoder setup
        self.bus = smbus.SMBus(i2c_bus_number)
        self.AS5600_I2C_ADDR = 0x36
        self.ANGLE_REG = 0x0C
        self.STATUS_REG = 0x0B
        self._configure_encoder()        

        # taring default
        self.elbow_angle_tare = self.read_elbow_angle()
        self.imu_tare_q = np.array([1.0, 0.0, 0.0, 0.0]) # dit moet denk ik [0.5, 0.5, -0.5, 0.5], w,x ,y ,z

# control api
    def start(self):  # allow live updates to advance (GUI start)
        self.running = True

    def stop(self):  # freeze output at last_sample (GUI stop)
        self.running = False

    def is_running(self) -> bool:
        return self.running
    
    def tare(self, what: str = "all"):
        if what not in ("all", "imu", "elbow"):
            raise ValueError("tare: what must be 'all, 'imu', 'elbow'")
        
        if what in ("all", "imu"):
            qi, qj, qk, qr = self.bno.game_quaternion #  i, j, k, real
            self.imu_tare_q = np.array([qr, -qi, -qj, -qk]) # w, -x, -y, -z

        if what in ("all", "elbow"):
            self.elbow_angle_tare = self.read_elbow_angle()

        self.last_tare_ts = time.time()

    def last_tare_iso(self) -> str | None:
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.last_tare_ts)) if self.last_tare_ts else None

# hardware setup

    def configure_encoder(self):
        CONF_REG = 0x07
        CONF_BYTE1 = 0b00000000
        CONF_BYTE2 = 0b00000001
        self.bus.write_byte_data(self.AS5600_I2C_ADDR, CONF_REG, CONF_BYTE1)
        time.sleep(0.01)
        self.bus.write_byte_data(self.AS5600_I2C_ADDR, CONF_REG + 1, CONF_BYTE2)
        time.sleep(0.01)

    def read_elbow_angle(self):
        try:
            byte1 = self.bus.read_byte_data(self.AS5600_I2C_ADDR, self.ANGLE_REG)
            byte2 = self.bus.read_byte_data(self.AS5600_I2C_ADDR, self.ANGLE_REG + 1)
            raw_angle = ((byte1 << 8) | byte2) & 0x0FFF
            return raw_angle * (360 / 4096)
        except OSError:
            return None            

    def apply_tare(self, tare_q, q):
        # quaternion multiply: tare_q * q
        w1, x1, y1, z1 = tare_q
        w2, x2, y2, z2 = q
        w = w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2
        x = w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2
        y = w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2
        z = w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2
        return np.array([w, x, y, z]) / np.linalg.norm([w, x, y, z])                

    def quaternion_to_euler(self, q, degrees=True):
        r = R.from_quat([q[1], q[2], q[3], q[0]])  # scipy expects x, y, z, w
        return r.as_euler('zyx', degrees=degrees)  # yaw, pitch, roll

    def read(self):
        """Returns current readings as a dict: quaternion, yaw/pitch/roll, elbow angle"""
        if not self.running:
            return{
                "yaw": float(self.last_sample["yaw"]),
                "pitch": float(self.last_sample["pitch"]),
                "roll": float(self.last_sample["roll"]),
                "elbow_angle": None if self.elbow_angle_tare is None else 0.0,
                "running": False,
             }
        
        # IMU
        qi, qj, qk, qr = self.bno.game_quaternion  # i, j, k, real
        quat = np.array([qr, qi, qj, qk], dtype=float)  # w,x,y,z
        quat_rel = self.apply_tare(self.imu_tare_q, quat)
        yaw, pitch, roll = self.quaternion_to_euler(quat_rel, degrees=True)

        # Elbow (relative)
        elbow = self.read_elbow_angle()
        elbow_rel = (elbow - self.elbow_angle_tare) if (elbow is not None and self.elbow_angle_tare is not None) else None

        # Update cache and return
        self.last_sample = {"yaw": float(yaw), "pitch": float(pitch), "roll": float(roll)}
        return {
            "yaw": float(yaw),
            "pitch": float(pitch),
            "roll": float(roll),
            "elbow_angle": None if elbow_rel is None else float(elbow_rel),
            "running": True,
        }
