from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import numpy as np

app = Flask(__name__)
CORS(app)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/simulate', methods=['POST'])
def simulate():
    try:
        data = request.json
        
        # -------- USER INPUT --------
        m0 = float(data.get('mass', 50000))
        burn_time = float(data.get('burnTime', 5))
        h = float(data.get('altitude', 10000))
        v = float(data.get('velocity', 500))
        Cd0 = float(data.get('cd', 0.3))
        Cl = float(data.get('cl', 0.0))
        A = float(data.get('area', 10))
        gamma_deg = float(data.get('flightAngle', 60))
        gamma_angle = np.radians(gamma_deg)
        
        # -------- ENGINE INPUT --------
        At = float(data.get('throatArea', 0.8))
        Pt = float(data.get('chamberPressure', 3.5e6))
        Tt = float(data.get('chamberTemperature', 3500))
        gamma = float(data.get('gamma', 1.22))
        R = float(data.get('gasConstant', 415700))
        
        a_req = float(data.get('desiredAccel', 5))
        q_max = float(data.get('maxQLimit', 35000))
        
        # -------- CONSTANTS --------
        rho0 = 1.225
        H = 8500
        g0 = 9.81
        Re = 6371000
        
        # -------- SAFETY LIMITS --------
        v_current = max(v, 0.1)
        m0 = max(m0, 1)
        A = max(A, 0.1)
        
        # -------- ATMOSPHERE --------
        rho = rho0 * np.exp(-h/H)
        g = g0 * (Re/(Re+h))**2
        
        if h < 11000:
            T_air = 288 - 0.0065 * h
        else:
            T_air = 216
        
        a_sound = np.sqrt(1.4 * 287 * T_air)
        
        # -------- MACH + Cd --------
        M = v_current / a_sound
        
        if M < 0.8:
            Cd = Cd0
        elif M < 1.2:
            Cd = Cd0 + 0.3 * np.sin(np.pi * (M - 0.8) / 0.4)
        else:
            Cd = Cd0 * np.exp(-0.5 * (M - 1.2)) + 0.2
            
        # -------- ENGINE MODEL --------
        m_dot_engine = At * Pt * np.sqrt(gamma / (R * Tt)) * \
                       (2 / (gamma + 1)) ** ((gamma + 1) / (2 * (gamma - 1)))
        
        ve = np.sqrt(gamma * R * Tt)
        
        # -------- MASS --------
        m_current = m0
        
        # -------- FORCES --------
        D = 0.5 * rho * v_current**2 * Cd * A
        L = 0.5 * rho * v_current**2 * Cl * A
        
        # -------- REQUIRED THRUST --------
        T_required = D + m_current * g * np.cos(gamma_angle) - L * np.sin(gamma_angle) + m_current * a_req
        
        # -------- MAX-Q --------
        q = 0.5 * rho * v_current**2
        q_ratio = q / q_max
        
        # -------- THROTTLE CONTROL --------
        throttle = 1.0
        if q > q_max:
            throttle = q_max / q
        elif q_ratio > 0.9:
            throttle = 0.9
            
        # -------- ENGINE THRUST --------
        T_engine = m_dot_engine * ve * throttle
        T = T_engine
        
        # -------- SAFETY CHECK --------
        if T < m_current * g * np.cos(gamma_angle):
            v_safe = np.sqrt((2 * q_max) / max(rho, 1e-6))
            v_current = max(v_safe, 0.1)
            # recompute
            D = 0.5 * rho * v_current**2 * Cd * A
            L = 0.5 * rho * v_current**2 * Cl * A
            q = 0.5 * rho * v_current**2
            
        # -------- MASS FLOW --------
        m_dot = min(m_dot_engine, T / ve) if ve > 0 else 0
        
        # -------- FUEL --------
        fuel_used = m_dot * burn_time
        m_after = max(m_current - fuel_used, 0)
        
        # -------- POWER --------
        power = T * v_current
        
        # -------- ANALYSIS MODULE --------
        
        # --- SPEED ---
        if M < 0.3:
            mach_status = "Low speed"
        elif M < 1:
            mach_status = "Subsonic"
        elif M < 2:
            mach_status = "Supersonic"
        else:
            mach_status = "Hypersonic"
            
        # --- MAX-Q ---
        new_q_ratio = q / q_max
        if new_q_ratio > 1:
            q_status = "Exceeded"
        elif new_q_ratio > 0.9:
            q_status = "Near Max-Q"
        elif new_q_ratio > 0.5:
            q_status = "Approaching Max-Q"
        else:
            q_status = "Safe"
            
        # --- FUEL ---
        burn_ratio = T_required / (T_engine + 1e-6)
        if burn_ratio < 0.3:
            fuel_status = "Engine under-utilized"
        elif burn_ratio < 0.9:
            fuel_status = "Nominal"
        else:
            fuel_status = "Maximum capacity"
            
        # --- THRUST ---
        TWR = T_engine / (m_current * g)
        if TWR < 1.0:
            twr_status = "Insufficient Thrust"
        elif TWR < 1.5:
            twr_status = "Weak thrust"
        elif TWR < 3:
            twr_status = "Nominal"
        else:
            twr_status = "High thrust"
            
        # --- EFFICIENCY ---
        eff = v_current / (fuel_used + 1e-6)
        if eff < 0.2:
            eff_status = "Sub-optimal"
        elif eff < 1:
            eff_status = "Moderate efficiency"
        else:
            eff_status = "Optimal"
            
        # Chart dummy projection (using new acceleration)
        velocity_curve = []
        sim_v = v_current
        sim_m = m_current
        for t in range(0, 30):
            sim_a = (T - D - (sim_m * g * np.cos(gamma_angle))) / sim_m
            sim_v += sim_a * 5
            sim_m -= m_dot * 5
            if sim_v < 0: sim_v = 0
            if sim_m < 0: sim_m = 0
            velocity_curve.append(round(sim_v, 2))

        # Format output
        response = {
            "performance": {
                "velocity": round(v_current, 2),
                "thrust": round(T / 1000, 2), # kN
                "power": round(power / 1000000, 2), # MW
                "dynamicPressure": round(q, 2), # Pa
                "drag": round(D / 1000, 2) # kN
            },
            "fuel": {
                "fuelUsed": round(fuel_used, 2),
                "remainingMass": round(m_after, 2),
                "massFlowRate": round(m_dot, 2)
            },
            "engine": {
                "maxFlowRate": round(m_dot_engine, 2),
                "throttlePercentage": round(throttle * 100, 1),
                "twr": round(TWR, 2)
            },
            "analysis": {
                "machStatus": mach_status,
                "qStatus": q_status,
                "fuelStatus": fuel_status,
                "twrCondition": twr_status,
                "efficiency": eff_status
            },
            "chartData": velocity_curve
        }
        
        return jsonify(response)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 400

if __name__ == '__main__':
    app.run(debug=True, port=5000)
