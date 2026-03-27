import numpy as np

print("\n===== INTELLIGENT ROCKET CONTROL SYSTEM =====")

# -------- SAFE INPUT --------
def safe_input(prompt, default):
    try:
        val = input(prompt)
        return float(val) if val.strip() != "" else default
    except:
        print("⚠ Invalid input → using default:", default)
        return default

# -------- USER INPUT --------
m0 = safe_input("Initial mass (kg): ", 50000)
burn_time = safe_input("Burn time (s): ", 5)

h = safe_input("Altitude (m): ", 10000)
v = safe_input("Velocity (m/s): ", 500)

Cd0 = safe_input("Base Cd: ", 0.3)
Cl = safe_input("Lift coefficient: ", 0.0)
A = safe_input("Area (m^2): ", 10)

gamma_deg = safe_input("Flight angle (deg): ", 60)  # FIXED
gamma_angle = np.radians(gamma_deg)

# -------- ENGINE INPUT --------
At = safe_input("Throat area (m^2): ", 0.8)
Pt = safe_input("Chamber pressure (Pa): ", 3.5e6)
Tt = safe_input("Chamber temperature (K): ", 3500)
gamma = safe_input("Gamma: ", 1.22)
R = safe_input("Gas constant (J/kg·K): ", 415700)

a_req = safe_input("Desired acceleration (m/s^2): ", 5)
q_max = safe_input("Max-Q limit (Pa): ", 35000)

# -------- CONSTANTS --------
rho0 = 1.225
H = 8500
g0 = 9.81
Re = 6371000

# -------- SAFETY LIMITS --------
v = max(v, 0.1)
m0 = max(m0, 1)
A = max(A, 0.1)

# -------- ATMOSPHERE --------
rho = rho0 * np.exp(-h/H)
g = g0 * (Re/(Re+h))**2
a_sound = 340

# -------- MACH + Cd --------
M = v / a_sound

if M < 0.8:
    Cd = Cd0
elif M < 1.2:
    Cd = Cd0 + 0.3*np.sin(np.pi*(M-0.8)/0.4)
else:
    Cd = Cd0*np.exp(-0.5*(M-1.2)) + 0.2

# -------- ENGINE MODEL --------
m_dot_engine = At * Pt * np.sqrt(gamma / (R * Tt)) * \
               (2/(gamma+1))**((gamma+1)/(2*(gamma-1)))

ve = np.sqrt(gamma * R * Tt)

# -------- MASS --------
m_current = m0

# -------- FORCES --------
D = 0.5 * rho * v**2 * Cd * A
L = 0.5 * rho * v**2 * Cl * A

# -------- REQUIRED THRUST --------
T_required = D + m_current*g*np.cos(gamma_angle) - L*np.sin(gamma_angle) + m_current*a_req

# -------- MAX-Q --------
q = 0.5 * rho * v**2
q_ratio = q / q_max

# -------- THROTTLE CONTROL --------
if q > q_max:
    throttle = q_max / q
    print("\n⚠ Max-Q exceeded → throttling down")
elif q_ratio > 0.9:
    throttle = 0.9
    print("\n⚠ Near Max-Q → reducing throttle slightly")
else:
    throttle = 1.0

# -------- ENGINE THRUST --------
T_engine = m_dot_engine * ve * throttle

# -------- FINAL THRUST (FIXED) --------
T = T_engine

# -------- SAFETY CHECK --------
if T < m_current*g*np.cos(gamma_angle):
    print("\n🚨 Thrust insufficient → applying velocity safety")

    v_safe = np.sqrt((2*q_max)/max(rho,1e-6))
    v = max(v_safe, 0.1)

    # recompute forces + q (FIXED)
    D = 0.5 * rho * v**2 * Cd * A
    L = 0.5 * rho * v**2 * Cl * A
    q = 0.5 * rho * v**2

# -------- MASS FLOW --------
m_dot = min(m_dot_engine, T/ve)

# -------- FUEL --------
fuel_used = m_dot * burn_time
m_after = max(m_current - fuel_used, 0)

# -------- POWER --------
power = T * v

# -------- OUTPUT --------
print("\n===== ENGINE =====")
print(f"Max engine flow rate: {m_dot_engine:.2f} kg/s")

print("\n===== MASS =====")
print(f"Initial mass: {m0:.2f} kg")
print(f"Fuel used: {fuel_used:.2f} kg")
print(f"Remaining mass: {m_after:.2f} kg")

print("\n===== PERFORMANCE =====")
print(f"Velocity: {v:.2f} m/s")
print(f"Throttle: {throttle:.2f}")
print(f"Thrust: {T:.2f} N")
print(f"dm/dt: {m_dot:.2f} kg/s")
print(f"Power: {power/1e6:.2f} MW")
print(f"Dynamic Pressure: {q:.2f} Pa")

# -------- ANALYSIS --------
print("\n===== FLIGHT ANALYSIS =====")

# --- REAL SPEED OF SOUND ---
if h < 11000:
    T_air = 288 - 0.0065*h
else:
    T_air = 216

a_sound = np.sqrt(1.4 * 287 * T_air)
mach = v / a_sound

# --- SPEED ---
if mach < 0.3:
    print("🐢 Low speed → inefficient climb")
elif mach < 1:
    print("🚀 Subsonic → optimal ascent")
elif mach < 2:
    print("⚡ Supersonic → increasing stress")
else:
    print("🔥 Hypersonic → extreme conditions")

# --- MAX-Q ---
q_ratio = q / q_max

if q_ratio > 1:
    print("❌ Max-Q exceeded")
elif q_ratio > 0.9:
    print("🚨 Near Max-Q → reduce velocity")
elif q_ratio > 0.5:
    print("⚠ Approaching Max-Q")
else:
    print("✅ Safe aerodynamic region")

# --- FUEL ---
burn_ratio = T_required / (T_engine + 1e-6)

if burn_ratio < 0.3:
    print("⛽ Engine under-utilized")
elif burn_ratio < 0.9:
    print("🔥 Normal fuel usage")
else:
    print("🚨 Engine at maximum capacity")

# --- THRUST ---
TWR = T_engine / (m_current * g)

if TWR < 1:
    print("❌ Cannot lift")
elif TWR < 1.5:
    print("⚠ Weak thrust")
elif TWR < 3:
    print("✅ Good thrust")
else:
    print("🚀 High thrust")

# --- EFFICIENCY ---
eff = v / (fuel_used + 1e-6)

if eff < 0.2:
    print("❌ Very poor efficiency")
elif eff < 1:
    print("⚠ Moderate efficiency")
else:
    print("✅ High efficiency")