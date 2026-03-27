document.addEventListener('DOMContentLoaded', () => {
    // --- Initial Setup & Event Listeners ---
    
    // Bind Range Sliders to Value Displays
    const bindSlider = (sliderId, textId) => {
        const slider = document.getElementById(sliderId);
        const text = document.getElementById(textId);
        if(slider && text) {
            slider.addEventListener('input', (e) => {
                text.textContent = parseInt(e.target.value).toLocaleString();
            });
        }
    };

    bindSlider('param-alt', 'val-alt');
    bindSlider('param-vel', 'val-vel');

    // Scroll mapping and Hero Animation
    const startBtn = document.getElementById('start-btn');
    const rocketVisual = document.querySelector('.rocket-animation-container');
    const aboutSec = document.getElementById('about');
    const dashSec = document.getElementById('dashboard');

    if (startBtn) {
        startBtn.addEventListener('click', () => {
            // Play subtle sound if allowed by browser policies
            const sound = document.getElementById('launch-sound');
            if(sound) {
                sound.volume = 0.5;
                sound.play().catch(e => console.log('Audio autoplay prevented'));
            }

            rocketVisual.classList.add('launch');
            
            setTimeout(() => {
                aboutSec.classList.remove('hidden-section');
                dashSec.classList.remove('hidden-section');
                
                // Add fade in
                aboutSec.classList.add('fade-in');
                dashSec.classList.add('fade-in');

                aboutSec.scrollIntoView({ behavior: 'smooth' });
            }, 1000); // Wait for launch animation
        });
    }

    // Chart.js Setup
    const ctx = document.getElementById('velocityChart').getContext('2d');
    let velocityChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: Array.from({length: 30}, (_, i) => i * 5 + 's'),
            datasets: [{
                label: 'Projected Velocity (m/s)',
                data: Array(30).fill(0),
                borderColor: '#00f3ff',
                backgroundColor: 'rgba(0, 243, 255, 0.1)',
                borderWidth: 2,
                pointRadius: 0,
                fill: true,
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    grid: { color: 'rgba(255,255,255,0.05)' },
                    ticks: { color: '#8892b0' }
                },
                x: {
                    grid: { color: 'rgba(255,255,255,0.05)' },
                    ticks: { color: '#8892b0' }
                }
            },
            plugins: {
                legend: { labels: { color: '#e0e6ed', font: { family: 'Orbitron' } } }
            }
        }
    });

    // Form Submission
    const form = document.getElementById('sim-form');
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        // Show loading state
        const btn = document.getElementById('run-sim-btn');
        const spinner = document.getElementById('loading');
        btn.classList.add('hidden');
        spinner.classList.remove('hidden');

        // Gather data
        const payload = {
            altitude: parseFloat(document.getElementById('param-alt').value),
            velocity: parseFloat(document.getElementById('param-vel').value),
            mass: parseFloat(document.getElementById('param-mass').value),
            flightAngle: parseFloat(document.getElementById('param-angle').value),
            throatArea: parseFloat(document.getElementById('param-throat').value),
            chamberPressure: parseFloat(document.getElementById('param-pressure').value),
            chamberTemperature: parseFloat(document.getElementById('param-temp').value),
            cd: parseFloat(document.getElementById('param-cd').value),
            area: parseFloat(document.getElementById('param-area').value),
            desiredAccel: parseFloat(document.getElementById('param-accel').value),
            maxQLimit: parseFloat(document.getElementById('param-maxq').value)
        };

        try {
            const response = await fetch('http://127.0.0.1:5000/simulate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (!response.ok) throw new Error('Simulation failed');

            const result = await response.json();
            updateDashboard(result, payload.mass);

        } catch (error) {
            console.error(error);
            alert("Error connecting to simulation server. Ensure Flask is running.");
        } finally {
            spinner.classList.add('hidden');
            btn.classList.remove('hidden');
        }
    });

    // Dashboard Update Logic
    function updateDashboard(data, initialMass) {
        // Animate performance numbers
        animateValue('out-velocity', data.performance.velocity);
        animateValue('out-thrust', data.performance.thrust);
        animateValue('out-q', data.performance.dynamicPressure);
        
        // Animate fuel numbers
        animateValue('out-flow', data.fuel.massFlowRate);
        animateValue('out-mass', data.fuel.remainingMass);

        // Update Fuel Bar
        const fuelPercent = (data.fuel.remainingMass / initialMass) * 100;
        const fuelBar = document.getElementById('fuel-bar');
        fuelBar.style.width = Math.max(0, fuelPercent) + '%';
        if (fuelPercent < 20) fuelBar.style.background = 'linear-gradient(90deg, #ffaa00, #ff3333)';
        else fuelBar.style.background = 'linear-gradient(90deg, #00f3ff, #00ffaa)';

        // Update Throttle Gauge
        const throttlePrc = data.engine.throttlePercentage;
        animateValue('out-throttle', throttlePrc);
        const circle = document.getElementById('throttle-circle');
        circle.style.strokeDasharray = `${throttlePrc}, 100`;
        
        if(throttlePrc > 90) circle.style.stroke = '#ff3333';
        else if (throttlePrc > 70) circle.style.stroke = '#ffaa00';
        else circle.style.stroke = '#00f3ff';

        // Update Chart
        if (data.chartData) {
            velocityChart.data.datasets[0].data = data.chartData;
            velocityChart.update();
        }

        // Update Analysis List
        updateAnalysis(data.analysis);
    }

    function updateAnalysis(analysisData) {
        const list = document.getElementById('analysis-list');
        list.innerHTML = ''; // Clear existing

        const createItem = (text, iconClass, typeClass) => {
            return `<li class="status-item ${typeClass}">
                        <i class="${iconClass}"></i>
                        <span>${text}</span>
                    </li>`;
        };

        // Determine Mach
        let machHtml = createItem(`Speed Region: ${analysisData.machStatus}`, 'fa-solid fa-gauge-high', 'info');
        
        // Dynamic Q
        let qStatus = analysisData.qStatus;
        let qHtml = '';
        if (qStatus === "Safe") qHtml = createItem('Aerodynamic Stress: Nominal', 'fa-solid fa-shield-halved', 'safe');
        else if (qStatus === "Near Max-Q") qHtml = createItem('Approaching Max-Q. Throttling down engines.', 'fa-solid fa-triangle-exclamation', 'warning');
        else qHtml = createItem('WARNING: Exceeded Structural Max-Q Limit!', 'fa-solid fa-radiation', 'danger');

        // Fuel
        let fHtml = analysisData.fuelStatus === "Nominal" 
            ? createItem('Fuel Reserves: Nominal', 'fa-solid fa-gas-pump', 'safe')
            : createItem('WARNING: Low Fuel Condition', 'fa-solid fa-gas-pump', 'danger');
            
        // TWR
        let tHtml = '';
        if (analysisData.twrCondition === "Nominal") tHtml = createItem('Thrust-to-Weight Ratio: Optimal', 'fa-solid fa-weight-scale', 'safe');
        else if (analysisData.twrCondition === "Insufficient Thrust") tHtml = createItem('ALERT: TWR < 1.0 (Unable to lift off)', 'fa-solid fa-arrow-down', 'danger');
        else tHtml = createItem('High G-Force Stress Detected', 'fa-solid fa-meteor', 'warning');

        list.innerHTML = machHtml + qHtml + fHtml + tHtml;
    }

    // Number Counter Animation
    function animateValue(id, end, duration = 1000) {
        let obj = document.getElementById(id);
        let start = parseFloat(obj.innerText.replace(/,/g, '')) || 0;
        let range = end - start;
        let current = start;
        let increment = end > start ? 1 : -1;
        let stepTime = Math.abs(Math.floor(duration / (Math.abs(range) || 1)));
        if (stepTime < 20) stepTime = 20; // 50fps max

        // Calculate precision based on end value
        let isInt = end % 1 === 0 && start % 1 === 0;

        let steps = duration / stepTime;
        let currentStep = 0;

        let timer = setInterval(function() {
            currentStep++;
            let progress = currentStep / steps;
            
            // Ease out quad
            let easedProgress = progress * (2 - progress);
            current = start + (range * easedProgress);
            
            if (currentStep >= steps) {
                current = end;
                clearInterval(timer);
            }
            
            obj.innerHTML = isInt ? Math.round(current).toLocaleString() : current.toFixed(2).toLocaleString();
        }, stepTime);
    }
});
