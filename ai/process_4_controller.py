import subprocess
import sys
import os
import re

# Constants
WAPE_THRESHOLD_DM = 33
WAPE_THRESHOLD_IMPUTED = 35

# Robustly determine the project root (The directory this script resides in)
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
PYTHON_EXEC = sys.executable

# Environment setup to handle imports
ENV = os.environ.copy()
ENV["PYTHONPATH"] = PROJECT_ROOT + os.pathsep + ENV.get("PYTHONPATH", "")

def run_command(command, description, capture=False):
    print(f"\n--- {description} ---")
    print(f"Command: {command}")
    try:
        # Run from DemandForecasting subdirectory (PROJECT_ROOT) to ensure relative paths work
        # If capture is True, we capture stdout/stderr.
        # If capture is False, we let them flow to the console (None).
        if capture:
            stdout_setting = subprocess.PIPE
            stderr_setting = subprocess.PIPE
        else:
            stdout_setting = None
            stderr_setting = None

        result = subprocess.run(
            command, # Command is now a string or list
            cwd=PROJECT_ROOT, 
            shell=True, # Use shell=True for simpler string command handling on Windows
            env=ENV,
            check=True,
            stdout=stdout_setting,
            stderr=stderr_setting,
            text=True
        )
        
        if capture:
            print(result.stdout)
            if result.stderr:
                print("STDERR:", result.stderr)
            return result.stdout
        else:
            return "" # Nothing captured
            
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {e}")
        if capture:
            print("STDOUT:", e.stdout)
            print("STDERR:", e.stderr)
        raise

def run_test_and_get_wape():
    """Runs the test script and parses WAPE."""
    # Script path relative to DemandForecasting folder
    script_path = os.path.join("demand_forecasting", "test_wape.py")
    # We need to capture output to parse WAPE
    output = run_command(f'"{PYTHON_EXEC}" "{script_path}"', "Measuring WAPE", capture=True)
    
    # Regex to find WAPE_RESULT: <float>
    match = re.search(r"WAPE_RESULT:\s*([\d\.]+)", output)
    if match:
        wape = float(match.group(1))
        print(f"Detected WAPE: {wape}")
        return wape
    else:
        print("Could not parse WAPE from output.")
        return 999.0

def run_process_2():
    """Retrain Demand Forecasting Model (and Impute before that)."""
    print("\n[PROCESS 2] Retraining Forecast Model...")
    
    # Paths relative to DemandForecasting folder
    impute_script = os.path.join("latent_demand_recovery", "impute.py")
    run_command(f'"{PYTHON_EXEC}" "{impute_script}"', "Running Imputation", capture=False)

    train_script = os.path.join("demand_forecasting", "exp", "exp_dlinear.py")
    run_command(f'"{PYTHON_EXEC}" "{train_script}" --data_type imputed --use_decoder', "Retraining Forecast Model (DLinear)", capture=False)

def run_process_1():
    """Retrain Entire System (Process 1 + Process 2)."""
    print("\n[PROCESS 1] Retraining Entire System...")
    
    # Paths relative to DemandForecasting folder
    process_script = os.path.join("data_utils", "process_data.py")
    run_command(f'"{PYTHON_EXEC}" "{process_script}"', "Processing Data", capture=False)
    
    timesnet_script = os.path.join("latent_demand_recovery", "exp", "timesnet.py")
    run_command(f'"{PYTHON_EXEC}" "{timesnet_script}"', "Retraining Imputer (TimesNet)", capture=False)
    
    # 3. Call Process 2
    run_process_2()

def main():
    print("Starting Process 4 (Adaptive Retraining Controller)...")
    
    # Step 1: Check initial WAPE
    current_wape = run_test_and_get_wape()
    
    if current_wape > WAPE_THRESHOLD_DM:
        print(f"WAPE ({current_wape}) > Threshold DM ({WAPE_THRESHOLD_DM}). Initiating Process 2...")
        run_process_2()
        
        # Test again
        current_wape = run_test_and_get_wape()
        
        if current_wape > WAPE_THRESHOLD_IMPUTED:
            print(f"WAPE ({current_wape}) > Threshold Imputed ({WAPE_THRESHOLD_IMPUTED}). Initiating Process 1...")
            run_process_1()
            
            # Final Test
            current_wape = run_test_and_get_wape()
        else:
            print(f"WAPE ({current_wape}) is acceptable (<= {WAPE_THRESHOLD_IMPUTED}).")
    else:
        print(f"WAPE ({current_wape}) is good (<= {WAPE_THRESHOLD_DM}). No action needed.")

    # Final Report / Inference
    print("\nRunning Final Inference/Reporting...")
    print(f"Final WAPE: {current_wape}")

if __name__ == "__main__":
    main()
