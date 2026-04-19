"""
percep_4node_ui.py - v2
4-node perceptive breadboard UI
"""
import tkinter as tk
from tkinter import scrolledtext
import serial
import threading
import anthropic

ANTHROPIC_API_KEY = ""  # paste your key here
TEACHER_SYSTEM = """You are a concise electronics teacher. The student shows you auto-detected components on a breadboard.
Node 1=VCC(D8), Node 2=mid(D7), Node 3=GND series(D6), Node 4=GND parallel(D5).
Respond in ONE sentence only. Be direct and practical. If more than one sentence, the additional sentences are to summarise all previous changes the board has experienced to justify the recommendation.
"""

PORT    = "/dev/tty.usbmodem3101"
BAUD    = 115200
VCC     = 5.0
R_KNOWN = 10000.0
KNOWN_R = [2200, 10000, 100000]
KNOWN_C = [1e-6, 4.7e-6, 220e-6]

NODE_LABELS = {1:"D8 (VCC)", 2:"D7", 3:"D6 (GND)", 4:"D5 (GND)"}
NODE_X = {1:150, 2:380, 3:600, 4:380}
NODE_Y = {1:220, 2:220, 3:220, 4:420}

PROBE_NODES  = {1:(1,2), 2:(2,3), 3:(1,3), 4:(1,4)}
PROBE_LABELS = {1:"X (series)", 2:"Y (series)", 3:"X+Y verify", 4:"X2 (parallel)"}

def snap_R(R):
    best = min(KNOWN_R, key=lambda r: abs(r-R))
    return best if abs(best-R)/best < 0.30 else None

def snap_C(C):
    best = min(KNOWN_C, key=lambda c: abs(c-C))
    return best if abs(best-C)/best < 0.50 else None

def fmt_R(R): return f"{R/1000:.1f}kΩ" if R>=1000 else f"{R:.0f}Ω"
def fmt_C(C): return f"{C*1e6:.2f}µF" if C>=1e-6 else f"{C*1e9:.1f}nF"

def classify(V_fwd, V_rev, ct, cv):
    ratio = V_fwd/(V_rev+0.001)
    t63 = None
    if cv and cv[0] < 0.5:
        for i in range(1, len(cv)):
            if cv[i] >= 0.63*VCC:
                v0,v1,t0,t1 = cv[i-1],cv[i],ct[i-1],ct[i]
                t63 = (t0+(0.63*VCC-v0)/(v1-v0)*(t1-t0))/1000.0 if v1!=v0 else t1/1000.0
                break
    if t63:
        C=t63/R_KNOWN; Cs=snap_C(C)
        return ("C", fmt_C(Cs) if Cs else fmt_C(C), f"t63={t63*1000:.0f}ms")
    if V_fwd>4.7 and V_rev<0.05: return ("OPEN","","")
    if ratio>500 and 1.8<=V_fwd<=3.4:
        color="RED" if V_fwd<2.2 else ("GRN/BLU" if V_fwd<2.7 else "BLU/WHT")
        return ("LED", color, f"Vf={V_fwd:.2f}V")
    if ratio>200 and 0.4<=V_fwd<0.9:
        return ("D", f"Vf={V_fwd:.2f}V","")
    if 3.5<=V_fwd<=4.7 and V_rev<0.005:
        R=R_KNOWN*V_fwd/(VCC-V_fwd); Rs=snap_R(R)
        return ("R", fmt_R(Rs) if Rs else fmt_R(R),"")
    if V_rev>0.005 and ratio<500 and V_fwd>0.05:
        R=R_KNOWN*V_fwd/(VCC-V_fwd); Rs=snap_R(R)
        return ("R", fmt_R(Rs) if Rs else fmt_R(R),"")
    if V_fwd<0.05: return ("SHORT","","")
    if 0.05<V_fwd<4.9:
        return ("?", f"V={V_fwd:.2f}V Reff={fmt_R(R_KNOWN*V_fwd/(VCC-V_fwd))}", "")
    return ("?", f"V={V_fwd:.2f}V","")

# component colours
CCOLORS = {"R":"#00ff88","C":"#00ccff","LED":"#ffff00","D":"#ff8800",
           "OPEN":"#444444","SHORT":"#ff4444","?":"#666666"}

def draw_resistor(canvas, x1, y1, x2, y2, color):
    mx = (x1+x2)//2
    canvas.create_line(x1,y1,mx-35,y1, fill=color, width=2)
    zz=[(mx-35,y1),(mx-26,y1-12),(mx-17,y1+12),(mx-8,y1-12),(mx+1,y1+12),(mx+10,y1-12),(mx+19,y1+12),(mx+28,y1-12),(mx+35,y1)]
    canvas.create_line(zz, fill=color, width=2)
    canvas.create_line(mx+35,y1,x2,y2, fill=color, width=2)

def draw_capacitor(canvas, x1, y1, x2, y2, color):
    mx = (x1+x2)//2
    canvas.create_line(x1,y1,mx-10,y1, fill=color, width=2)
    canvas.create_line(mx-10,y1-20,mx-10,y1+20, fill=color, width=3)
    canvas.create_line(mx+10,y1-20,mx+10,y1+20, fill=color, width=3)
    canvas.create_line(mx+10,y1,x2,y2, fill=color, width=2)

def draw_led(canvas, x1, y1, x2, y2, color):
    mx = (x1+x2)//2
    canvas.create_line(x1,y1,mx-18,y1, fill=color, width=2)
    canvas.create_polygon(mx-18,y1-18,mx-18,y1+18,mx+18,y1,fill="",outline=color,width=2)
    canvas.create_line(mx+18,y1-18,mx+18,y1+18, fill=color, width=3)
    canvas.create_line(mx+6,y1-24,mx+22,y1-36,arrow=tk.LAST,fill=color,width=1)
    canvas.create_line(mx+12,y1-16,mx+28,y1-28,arrow=tk.LAST,fill=color,width=1)
    canvas.create_line(mx+18,y1,x2,y2, fill=color, width=2)

def draw_diode(canvas, x1, y1, x2, y2, color):
    mx = (x1+x2)//2
    canvas.create_line(x1,y1,mx-18,y1, fill=color, width=2)
    canvas.create_polygon(mx-18,y1-18,mx-18,y1+18,mx+18,y1,fill="",outline=color,width=2)
    canvas.create_line(mx+18,y1-18,mx+18,y1+18, fill=color, width=3)
    canvas.create_line(mx+18,y1,x2,y2, fill=color, width=2)

def draw_wire(canvas, x1, y1, x2, y2, color, dash=None):
    if dash:
        canvas.create_line(x1,y1,x2,y2, fill=color, width=2, dash=dash)
    else:
        canvas.create_line(x1,y1,x2,y2, fill=color, width=2)

def draw_component(canvas, ctype, x1, y1, x2, y2):
    color = CCOLORS.get(ctype, "#666666")
    if ctype=="R":   draw_resistor(canvas,x1,y1,x2,y2,color)
    elif ctype=="C": draw_capacitor(canvas,x1,y1,x2,y2,color)
    elif ctype=="LED": draw_led(canvas,x1,y1,x2,y2,color)
    elif ctype=="D": draw_diode(canvas,x1,y1,x2,y2,color)
    elif ctype=="SHORT": draw_wire(canvas,x1,y1,x2,y2,"#ff4444")
    elif ctype=="OPEN": draw_wire(canvas,x1,y1,x2,y2,"#333333",dash=(4,6))
    else: draw_wire(canvas,x1,y1,x2,y2,"#555555",dash=(2,4))


class PercepUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Perceptive Breadboard — 4 Node POC")
        self.root.configure(bg="#0a0a0a")
        self.root.geometry("760x700")

        self.components = {}
        self.current_probe = None
        self.ct = {1:[],2:[],3:[],4:[]}
        self.cv = {1:[],2:[],3:[],4:[]}

        tk.Label(root, text="PERCEPTIVE BREADBOARD", bg="#0a0a0a", fg="#00ff88",
                 font=("Courier", 22, "bold")).pack(pady=(18,0))
        tk.Label(root, text="4-node POC  ·  real-time detection",
                 bg="#0a0a0a", fg="#446644", font=("Courier", 13)).pack()

        self.canvas = tk.Canvas(root, width=720, height=460,
                                bg="#0d0d0d", highlightthickness=1,
                                highlightbackground="#1a3a1a")
        self.canvas.pack(padx=20, pady=12)

        self.status_var = tk.StringVar(value="Waiting for Arduino...")
        tk.Label(root, textvariable=self.status_var, bg="#0a0a0a", fg="#00ff88",
                 font=("Courier", 13)).pack()

        self.log = tk.Text(root, height=5, bg="#060606", fg="#00cc66",
                           font=("Courier", 22), relief=tk.FLAT, state=tk.DISABLED)
        self.log.pack(fill=tk.X, padx=20, pady=(4,10))

        # --- VCC / GND config bar ---
        config_bar = tk.Frame(root, bg="#0a0a0a")
        config_bar.pack(fill=tk.X, padx=20, pady=(0,4))

        tk.Label(config_bar, text="VCC:", bg="#0a0a0a", fg="#00ff88",
                 font=("Courier",22)).pack(side=tk.LEFT)
        self.vcc_var = tk.StringVar(value="D8 (node 1)")
        vcc_opts = ["D8 (node 1)", "D7 (node 2)", "D6 (node 3)", "D5 (node 4)"]
        tk.OptionMenu(config_bar, self.vcc_var, *vcc_opts,
                      command=lambda _: self.update_node_roles()).pack(side=tk.LEFT, padx=(2,16))

        tk.Label(config_bar, text="GND:", bg="#0a0a0a", fg="#ff4444",
                 font=("Courier",22)).pack(side=tk.LEFT)
        self.gnd_var1 = tk.StringVar(value="D6 (node 3)")
        self.gnd_var2 = tk.StringVar(value="D5 (node 4)")
        gnd_opts = ["D8 (node 1)", "D7 (node 2)", "D6 (node 3)", "D5 (node 4)", "(none)"]
        tk.OptionMenu(config_bar, self.gnd_var1, *gnd_opts,
                      command=lambda _: self.update_node_roles()).pack(side=tk.LEFT, padx=2)
        tk.Label(config_bar, text="&", bg="#0a0a0a", fg="#ff4444",
                 font=("Courier",22)).pack(side=tk.LEFT, padx=2)
        tk.OptionMenu(config_bar, self.gnd_var2, *gnd_opts,
                      command=lambda _: self.update_node_roles()).pack(side=tk.LEFT, padx=2)

        self.draw_static()
        self.start_serial()

    def update_node_roles(self):
        """Rebuild NODE_LABELS based on VCC/GND dropdown selections."""
        vcc_node = int(self.vcc_var.get().split("node ")[-1].replace(")",""))
        gnd_nodes = []
        for v in [self.gnd_var1, self.gnd_var2]:
            s = v.get()
            if "(none)" not in s:
                gnd_nodes.append(int(s.split("node ")[-1].replace(")","")))
        pin_names = {1:"D8", 2:"D7", 3:"D6", 4:"D5"}
        for n in range(1,5):
            name = pin_names[n]
            if n == vcc_node:
                NODE_LABELS[n] = f"{name} (VCC)"
            elif n in gnd_nodes:
                NODE_LABELS[n] = f"{name} (GND)"
            else:
                NODE_LABELS[n] = name
        self.draw_static()

    def log_msg(self, msg):
        print(msg)  # also print to terminal
        self.log.config(state=tk.NORMAL)
        self.log.insert(tk.END, msg + "\n")
        self.log.see(tk.END)
        self.log.config(state=tk.DISABLED)

    def draw_static(self):
        self.canvas.delete("all")
        # grid dots
        for x in range(40,700,40):
            for y in range(30,440,40):
                self.canvas.create_oval(x-1,y-1,x+1,y+1,fill="#1a2a1a",outline="")

        # draw detected components (skip verify node 3 and OPEN)
        for probe_num,(ctype,val,extra) in self.components.items():
            if probe_num==3: continue
            if ctype=="OPEN": continue
            n1,n2 = PROBE_NODES[probe_num]
            x1,y1 = NODE_X[n1],NODE_Y[n1]
            x2,y2 = NODE_X[n2],NODE_Y[n2]
            
            # For probe 4 (diagonal), route via waypoint
            if probe_num==4:
                # draw wire down from node1, then component across to node4
                mid_y = y2  # drop to node4's y level first
                self.canvas.create_line(x1, y1+14, x1, mid_y, fill=CCOLORS.get(ctype,"#666666"), width=2)
                draw_component(self.canvas, ctype, x1, mid_y, x2-14, mid_y)
                mx = (x1+x2)//2
                color = CCOLORS.get(ctype,"#666666")
                self.canvas.create_text(mx, mid_y-30, text=f"{ctype}: {val}",
                                        fill=color, font=("Courier",13,"bold"))
                if extra:
                    self.canvas.create_text(mx, mid_y-14, text=extra,
                                            fill=color, font=("Courier",20))
                continue

            # Probes 1, 2 — horizontal component between nodes
            color = CCOLORS.get(ctype,"#666666")
            draw_component(self.canvas, ctype, x1+14, y1, x2-14, y2)
            mx, my = (x1+x2)//2, min(y1,y2)-30
            self.canvas.create_text(mx, my, text=f"{ctype}: {val}",
                                    fill=color, font=("Courier",13,"bold"))
            if extra:
                self.canvas.create_text(mx, my+18, text=extra,
                                        fill=color, font=("Courier",11))

        # probing indicator
        if self.current_probe and self.current_probe in PROBE_NODES:
            n1,n2 = PROBE_NODES[self.current_probe]
            x1,y1 = NODE_X[n1],NODE_Y[n1]
            x2,y2 = NODE_X[n2],NODE_Y[n2]
            print("Node coords 1",x1,y1)
            print("Node coords 2",x2,y2)
            self.canvas.create_line(x1,y1,x2,y2,fill="#334433",width=1,dash=(3,8))
            mx,my = (x1+x2)//2,(y1+y2)//2
            self.canvas.create_text(mx,my+20,
                text=f"probing {PROBE_LABELS.get(self.current_probe,'')}...",
                fill="#335533",font=("Courier",22))

        # draw nodes on top
        for n,lbl in NODE_LABELS.items():
            x,y = NODE_X[n],NODE_Y[n]
            color = "#00ff88" if "VCC" in lbl else ("#ff4444" if "GND" in lbl else "#aaaaaa")
            self.canvas.create_oval(x-14,y-14,x+14,y+14,fill="#0a0a0a",outline=color,width=2)
            self.canvas.create_text(x,y,text=str(n),fill=color,font=("Courier",13,"bold"))
            self.canvas.create_text(x,y+28,text=lbl,fill=color,font=("Courier",22))

    def update_component(self, probe_num, result):
        self.components[probe_num] = result
        ctype,val,extra = result
        lbl = PROBE_LABELS.get(probe_num,f"node{probe_num}")
        msg = f"{lbl}: [{ctype}] {val} {extra}".strip()
        self.log_msg(msg)
        self.status_var.set(f"Detected: {msg}")
        self.current_probe = None
        self.draw_static()

    def serial_loop(self):
        try:
            ser = serial.Serial(PORT, BAUD, timeout=2)
            ser.reset_input_buffer()
            self.root.after(0, lambda: self.status_var.set("Connected to Arduino"))
        except Exception as e:
            err = str(e)
            self.root.after(0, lambda err=err: self.status_var.set(f"Serial error: {err}"))
            return

        while True:
            try:
                line = ser.readline().decode(errors='ignore').strip()
            except:
                break
            if not line: continue

            if line.startswith("PROBING:"):
                parts = line.split(":")
                try:
                    n = int(parts[1])
                    self.current_probe = n
                    lbl = PROBE_LABELS.get(n,"")
                    self.root.after(0, lambda l=lbl: self.status_var.set(f"Probing: {l}..."))
                    self.root.after(0, self.draw_static)
                except: pass
                continue

            if line.startswith("BLEED_TIMEOUT"):
                try:
                    n = int(line.split(":")[1])
                    self.ct[n],self.cv[n]=[],[]
                except: pass
                continue

            if line.startswith("CHARGE:"):
                try:
                    parts=line.split(":",2); n=int(parts[1])
                    self.ct[n],self.cv[n]=[],[]
                    for p in parts[2].split(";"):
                        if "," not in p: continue
                        t,v=p.split(",")
                        self.ct[n].append(float(t)); self.cv[n].append(float(v))
                except: pass
                continue

            if line.startswith("FWD:"):
                print(f"RAW FWD: {line}")  # ADD THIS
                try:
                    rest=line[4:]; n_str,rem=rest.split(":",1)
                    n=int(n_str); fwd,rev=rem.split("|")
                    V_fwd=float(fwd); V_rev=float(rev.split(":")[1])
                except: continue
                result=classify(V_fwd,V_rev,self.ct[n],self.cv[n])
                self.ct[n],self.cv[n]=[],[]
                self.root.after(0,lambda r=result,nn=n: self.update_component(nn,r))
                continue

    def start_serial(self):
        threading.Thread(target=self.serial_loop, daemon=True).start()


class TeacherWindow:
    def __init__(self, parent_app):
        self.app = parent_app
        self.win = tk.Toplevel()
        self.win.title("Electronics Teacher")
        self.win.configure(bg="#1e1e1e")
        self.win.geometry("620x500")
        self.history = []
        self.client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

        tk.Label(self.win, text="ELECTRONICS TEACHER", bg="#1e1e1e", fg="#98d98e",
                 font=("Courier", 16, "bold")).pack(pady=(12,0))

        tk.Button(self.win, text="↻ Refresh Circuit", bg="#334433", fg="black",
                  font=("Courier",20), relief=tk.FLAT, padx=8,
                  command=lambda: self._refresh_circuit()
                  ).pack(pady=(0,4))

        self.dialog = scrolledtext.ScrolledText(
            self.win, state=tk.DISABLED, wrap=tk.WORD,
            bg="#2d2d2d", fg="#e0e0e0", font=("Courier", 22),
            relief=tk.FLAT, padx=10, pady=10)
        self.dialog.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.dialog.tag_config("student_tag", foreground="#7ec8e3", font=("Courier",11,"bold"))
        self.dialog.tag_config("teacher_tag", foreground="#98d98e", font=("Courier",11,"bold"))
        self.dialog.tag_config("system_tag",  foreground="#aaaaaa", font=("Courier",10,"italic"))

        bottom = tk.Frame(self.win, bg="#1e1e1e")
        bottom.pack(fill=tk.X, padx=10, pady=(0,10))

        self.input = tk.Text(bottom, height=3, bg="#2d2d2d", fg="#e0e0e0",
                             font=("Courier", 22), relief=tk.FLAT,
                             insertbackground="white", padx=6, pady=4)
        self.input.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0,6))
        self.input.bind("<Return>", lambda e: (self.send(), "break")[1])
        self.input.bind("<Shift-Return>", lambda e: None)

        tk.Button(bottom, text="Ask", bg="#7b5ea7", fg="black",
                  font=("Helvetica",22), relief=tk.FLAT,
                  padx=10, command=self.send).pack(side=tk.RIGHT, anchor="n", pady=2)

        # Show current circuit on open
        self.append("System", self.circuit_summary())

    def _refresh_circuit(self):
        self.dialog.config(state=tk.NORMAL)
        self.dialog.delete("1.0", tk.END)
        self.dialog.config(state=tk.DISABLED)
        self.append("System", self.circuit_summary())
        for msg in self.history:
            speaker = "Student" if msg["role"]=="user" else "Teacher"
            text = msg["content"]
            if "\n\nStudent asks: " in text:
                text = text.split("\n\nStudent asks: ")[-1]
            self.append(speaker, text)

    def circuit_summary(self):
        comps = self.app.components
        if not comps:
            return "No components detected yet."
        lines = ["Current circuit:"]
        labels = {1:"X (nodes 1→2)", 2:"Y (nodes 2→3)", 3:"X+Y verify", 4:"X2 (nodes 1→4, parallel)"}
        for k,v in comps.items():
            ctype,val,extra = v
            lines.append(f"  {labels.get(k,f'probe{k}')}: {ctype} {val} {extra}".strip())
        return "\n".join(lines)

    def append(self, speaker, text):
        self.dialog.config(state=tk.NORMAL)
        if self.dialog.index("end-1c") != "1.0":
            self.dialog.insert(tk.END, "\n\n")
        tag = {"Student":"student_tag","Teacher":"teacher_tag"}.get(speaker,"system_tag")
        self.dialog.insert(tk.END, f"{speaker}:\n", tag)
        self.dialog.insert(tk.END, text)
        self.dialog.config(state=tk.DISABLED)
        self.dialog.see(tk.END)

    def send(self):
        text = self.input.get("1.0", tk.END).strip()
        if not text: return
        self.input.delete("1.0", tk.END)
        self.append("Student", text)

        circuit = self.circuit_summary()
        prompt = f"{circuit}\n\nStudent asks: {text}"
        self.history.append({"role":"user","content":prompt})

        def call_api():
            try:
                resp = self.client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=80,
                    system=TEACHER_SYSTEM,
                    messages=self.history
                )
                reply = resp.content[0].text
                self.history.append({"role":"assistant","content":reply})
                self.win.after(0, lambda r=reply: self.append("Teacher", r))
            except Exception as e:
                err = str(e)
                self.win.after(0, lambda e=err: self.append("Error", e))

        threading.Thread(target=call_api, daemon=True).start()


if __name__ == "__main__":
    root = tk.Tk()
    app = PercepUI(root)

    # Add Ask Teacher button to main window
    def open_teacher():
        TeacherWindow(app)

    tk.Button(root, text="Ask Teacher", bg="#7b5ea7", fg="black",
              font=("Courier", 12, "bold"), relief=tk.FLAT,
              padx=12, pady=4, command=open_teacher).pack(pady=(0,10))

    root.mainloop()