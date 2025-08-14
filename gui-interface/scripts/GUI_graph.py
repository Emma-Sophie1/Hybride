# in deze code staat het script voor het volgen van de stip etc
# inc de grafiek met live data
import tkinter as tk
import time
from tkinter import ttk, messagebox
import matplotlib.patches as patches
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from ClassSensorDataProducerE import SensorDataProducer

class MovementMeasure:
    def __init__(self, root):
        self.root = root
        root.tile("LIVE movement measure with Reference Speed")

        self.sensor = SensorDataProducer(i2c_bus_number=2)

        # min and max q_elevation, voor nu handmatig invullen
        self.qe_min, self.qe_max = [], []
        self.qh_min, self.qh_max = [], []
        
        # present qh targets
        preset = [
            self.qe_min,
            self.qe_max,
            0,
            30,
            45,
            60
        ]
        preset_strs = [f"{p:.1f}" for p in preset]

        # interface frame of the graph
        frm = ttk.frame(root, padding=10)
        frm.grid(row=0, column=0, sticky='nw')

        # measurement title
        ttk.Label(frm, text="Measurement title:").grid(row=0, column=0, sticky="e")
        self.title_var = tk.StringVar(value='Run1')
        ttk.Entry(frm, textvariable=self.title_var, width=20).grid(row=20, column=1, sticky='w')

        # preset q_horizontal_rotation target
        ttk.Label(frm, text="Preset qh target (degree) : ").grid(row=1, column=0, sticky='e')
        self.preset_var = tk.StringVar(value=preset_strs[3]) # default is 0
        combo = ttk.Combobox(frm, textvariable=preset_strs, values=preset_strs, state="readonly", width=10)
        combo.grid(row=1, column=1, sitcky='w')

        # Manual q1 Entry
        ttk.Label(frm, text="Or custom qh (°):").grid(row=2, column=0, sticky="e")
        self.manual_var = tk.StringVar()
        ttk.Entry(frm, textvariable=self.manual_var, width=10).grid(row=2, column=1, sticky="w")

        # Reference Speed Entry
        ttk.Label(frm, text="Reference speed (°/s):").grid(row=3, column=0, sticky="e")
        self.speed_var = tk.DoubleVar(value=5.0)
        ttk.Entry(frm, textvariable=self.speed_var, width=10).grid(row=3, column=1, sticky="w")

        # Start/Stop Buttons
        self.btn_start = ttk.Button(frm, text="Start Measurement", command=self.start)
        self.btn_start.grid(row=4, column=0, pady=8)
        self.btn_stop = ttk.Button(frm, text="Stop & Save", command=self.stop, state="disabled")
        self.btn_stop.grid(row=4, column=1, pady=8)

        # graph figure, matplotlib
        self.fig = Figure(figsize=(12,12))
        self.ax = self.fig.add_subplot(111)
        self.ax.set_xlim(self.qe_min - 10, self.qe_max + 10)
        self.ax.set_ylim(self.qh_min - 10, self.qh_max + 10)
        self.ax.set_xlabel("yaw in degrees")
        self.ax.set_ylabel("pitch in degrees")
        self.canvas = FigureCanvasTkAgg(self.fig, master=root)
        self.canvas.get_tk_widget().grid(row=0, column=1, padx=10, pady=10)
        
        # measuring
        self.running = False
        self.dt_ms = 50 # 20 Hz

        def start(self):
            self.btn_start.config(state="disabled")
            self.btn_stop.config(state="enabled")

        # Read UI inputs
            self.label = self.title_var.get().strip() or "Run"
            manual = self.manual_var.get().strip()
            if manual:
                try:
                    self.target = float(manual)
                except ValueError:
                    messagebox.showerror("Invalid value", "Custom qh must be a number.")
                    self.btn_start.config(state="enabled")
                    self.btn_stop.config(state="disabled")
                    return
            else:
                self.target = float(self.preset_var.get())

        try:
            self.ref_speed = float(self.speed_var.get())
        except ValueError:
            messagebox.showerror("Invalid value", "Reference speed must be a number.")
            self.btn_start.config(state="enabled")
            self.btn_stop.config(state="disabled")
            return       

        # Prepare data lists
        self.xs, self.ys, self.zs, self.q4s = [], [], [], []
        self.qh_ref_vals, self.qe_ref_vals = [], []

        # Clear & redraw axes
        self.ax.cla()
        self.ax.set_xlim(self.q1_min - 10, self.q1_max + 10)
        self.ax.set_ylim(self.q2_min - 10, self.q2_max + 10)
        self.ax.set_title(f"{self.label} – qh target ≈ {self.target:.1f}°, speed={self.ref_speed:.1f}°/s")
        self.ax.set_xlabel("Yaw (°)")
        self.ax.set_ylabel("Pitch (°)")

        # Shaded band
        w = 5
        self.band = patches.Rectangle(
            (self.target - w, self.q2_min),
            2*w,
            self.q2_max - self.q2_min,
            facecolor="orange",
            alpha=0.3
        )
        self.ax.add_patch(self.band)         

        # scatter, trail and reference point (alvast op startpositie zodat testpersoon in juiste positie kan komen)
        self.scat = self.ax.scatter([], [], s=50, c='red', label = "eigen beweging") # stip die eigen beweging nabootst
        self.trail, = self.ax.plot([], [], "-", c="pink") # lijn achter eigen stip die beweging laat zien die is geweest
        # start de referentie stip direct op [target, q2_min]
        self.ref_scat = self.ax.scatter(
            [self.target], [self.q2_min],
            s=50, c="blue", label="referentie"
        ) # referentie stip
        self.ax.legend(loc="upper right")


        #self.canvas.draw()
        # teken de initiele positie
        self.canvas.draw()

        self.start_time = time.time()
        self.running = True
        self.root.after(self.dt_ms, self.loop)

    def loop(self):
        if not self.running:
            return
        
        # read data from IMU
        try:
            data = self.sensor.read()
        except Exception as e:
            print("Sensor read error:", e)
            self.root.after(self.dt_ms, self.loop)
            return
        
        # nog even kijken of dit niet q1, q2, q3, q4 moet worden
        qe = float(data.get("Elevation", 0.0))
        qh = float(data.get("Horizontal Rotation", 0.0))
        qa = float(data.get("Axial Rotation", 0.0))
        qr = float(data.get("elbow_angle")) # elbow rotation, kan ook 0 zijn ?

        t = time.time() - self.start_time
        qe_ref = min(self.qe_min + self.ref_speed * t, self.qe_max)
        qh_ref = self.target

        # safe data
        self.xs.append(qe); self.ys.append(qh); self.zs.append(qa); self.q4s.append(qr)
        self.qe_ref_vals.append(qe_ref); self.qh_ref_vals(qh_ref)

        # update plot
        self.scat.set_offsets(list(zip(self.xs, self.ys)))
        self.trail.set_data(self.xs, self.ys)
    # - blauwe stip: referentie
        self.ref_scat.set_offsets([[qe_ref, qh_ref]])

        self.canvas.draw()
        self.root.after(self.dt_ms, self.loop)    

    def stop(self):
        self.running = False
        self.btn_stop.config(state="disabled")
        self.btn_start.config(state="enabled")   

if __name__ == "__main__":
    root = tk.Tk()
    app = MovementMeasure(root)
    root.mainloop()
 