{
  description = "SDR Python Development Environment (Simple)";

  ########################################################################
  # Binary cache: cuda‑maintainers (pre‑built CUDA & PyTorch derivations)
  ########################################################################
  nixConfig = {
    # where to download substitutes from
    extra-substituters = [
      "https://cuda-maintainers.cachix.org"
    ];

    # signature that binaries from the cache are signed with
    extra-trusted-public-keys = [
      "cuda-maintainers.cachix.org-1:0dq3bujKpuEPMCX6U4WylrUDZ9JyUG0VpVZa7CNfq5E="
    ];
  };

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs = { self, nixpkgs, ... }: {
    devShells = {
      x86_64-linux.default = 
        let
          pkgs = import nixpkgs { 
            system = "x86_64-linux"; 
            config.allowUnfree = true; 
            config.cudaSupport = true;
          };
          
          # Create Python environment with SDR packages
          pythonEnv = pkgs.python312.withPackages (ps: with ps; [
            soapysdr
            numpy
            matplotlib
            scipy
            # LLM dependencies
            torch
            transformers
            tokenizers
            accelerate
            datasets
            bitsandbytes
          ]);
          
        in pkgs.mkShell {
          name = "sdr-dev-shell";
          
          packages = with pkgs; [
            pythonEnv
            uv
            # SDR tools
            soapysdr-with-plugins
            soapyremote
            hackrf
            rtl-sdr
            uhd
            # Development tools
            git
            # Graphics support
            kitty

            # ptp
            linuxptp

            # Create wrapper scripts for our tools
            (pkgs.writeScriptBin "sdr-verify-ptp" ''
              #!${pkgs.bash}/bin/bash
              ${pythonEnv}/bin/python -m sdr_experiments.tools.verify_ptp "$@"
            '')
            (pkgs.writeScriptBin "sdr-waterfall" ''
              #!${pkgs.bash}/bin/bash
              ${pythonEnv}/bin/python -m sdr_experiments.tools.waterfall_tool "$@"
            '')
            (pkgs.writeScriptBin "sdr-measure-delay" ''
              #!${pkgs.bash}/bin/bash
              ${pythonEnv}/bin/python -m sdr_experiments.tools.measure_delay "$@"
            '')
            (pkgs.writeScriptBin "sdr-kitty-test" ''
              #!${pkgs.bash}/bin/bash
              ${pythonEnv}/bin/python -m kitty_graphics.test "$@"
            '')
            (pkgs.writeScriptBin "sdr-timed-capture" ''
              #!${pkgs.bash}/bin/bash
              ${pythonEnv}/bin/python -m sdr_experiments.tools.timed_capture "$@"
            '')
            (pkgs.writeScriptBin "sdr-ptp-sync" ''
              #!${pkgs.bash}/bin/bash
              set -e

              # These arguments require root privileges.
              NEEDS_ROOT=0
              for arg in "$@"; do
                if [[ "$arg" == "--start-master" || "$arg" == "--start-slave" || "$arg" == "--stop" || "$arg" == "--check" ]]; then
                  NEEDS_ROOT=1
                  break
                fi
              done
              
              # If we need root and don't have it, re-execute with sudo.
              if [[ "$NEEDS_ROOT" -eq 1 && "$EUID" -ne 0 ]]; then
                echo "This command requires root privileges. Re-running with sudo..."
                # Execute the script again with sudo, ensuring the PATH is preserved.
                # "$0" is the full path to this script in the Nix store.
                exec sudo -E --preserve-env=PATH "$0" "$@"
              fi
              
              # Execute the python script.
              # We must use an absolute path to the script in case sudo changes the CWD.
              # This assumes the command is run from the project root.
              PYTHON_SCRIPT_PATH="$PWD/src/sdr_experiments/tools/ptp_sync.py"

              if [ ! -f "$PYTHON_SCRIPT_PATH" ]; then
                  echo "Error: Python script not found at $PYTHON_SCRIPT_PATH" >&2
                  echo "Please ensure you are running this command from the root of the project directory." >&2
                  exit 1
              fi
              
              ${pythonEnv}/bin/python "$PYTHON_SCRIPT_PATH" "$@"
            '')
            (pkgs.writeScriptBin "llm-query" ''
              #!${pkgs.bash}/bin/bash
              ${pythonEnv}/bin/python -m llm_sidechannel.tools.query "$@"
            '')
            (pkgs.writeScriptBin "llm-analyze-moe" ''
              #!${pkgs.bash}/bin/bash
              ${pythonEnv}/bin/python -m llm_sidechannel.tools.analyze_moe "$@"
            '')
          ];

          env = {
            # UV configuration
            UV_PYTHON_DOWNLOADS = "never";
            UV_PYTHON = "${pythonEnv}/bin/python";
            
            # SDR library paths
            SOAPY_SDR_PLUGIN_PATH = "${pkgs.soapysdr-with-plugins}/lib/SoapySDR/modules0.8-3";
            
            # Terminal support
            TERM = "xterm-kitty";
          };

          shellHook = ''
            echo "🔬 SDR Development Environment (Simple)"
            echo "Python: ${pythonEnv}/bin/python"
            echo ""
            echo "Testing packages:"
            echo "  - SoapySDR: $(python -c "import SoapySDR; print('✓')" 2>/dev/null || echo "✗")"
            echo "  - NumPy: $(python -c "import numpy; print('✓')" 2>/dev/null || echo "✗")"
            echo "  - Matplotlib: $(python -c "import matplotlib; print('✓')" 2>/dev/null || echo "✗")"
            echo ""
            echo "Available packages (src/):"
            echo "  - sdr_experiments (main SDR tools)"
            echo "  - kitty_graphics (terminal graphics)"
            echo "  - llm_sidechannel (LLM MoE analysis)"
            echo ""
            echo "Ready to run:"
            echo "  sdr-verify-ptp --help"
            echo "  sdr-waterfall --help"  
            echo "  sdr-measure-delay --help"
            echo "  sdr-kitty-test"
            echo "  sdr-timed-capture --help"
            echo "  sdr-ptp-sync --help"
            echo "  llm-query --help"
            echo "  llm-analyze-moe --help"
            echo ""
            
            # Unset PYTHONPATH to avoid conflicts
            unset PYTHONPATH
            export PYTHONPATH="$PWD/src:$PYTHONPATH"
          '';
        };

      aarch64-linux.default = 
        let
          pkgs = import nixpkgs { 
            system = "aarch64-linux"; 
            config.allowUnfree = true; 
          };
          
          # Create Python environment with SDR packages
          pythonEnv = pkgs.python312.withPackages (ps: with ps; [
            soapysdr
            numpy
            matplotlib
            scipy
            # LLM dependencies
            torch
            transformers
            tokenizers
            accelerate
            datasets
            bitsandbytes
          ]);
          
        in pkgs.mkShell {
          name = "sdr-dev-shell";
          
          packages = with pkgs; [
            pythonEnv
            uv
            # SDR tools
            soapysdr-with-plugins
            soapyremote
            rtl-sdr
            # Development tools
            git
            # Graphics support
            kitty

            # ptp
            linuxptp

            # Create wrapper scripts for our tools
            (pkgs.writeScriptBin "sdr-verify-ptp" ''
              #!${pkgs.bash}/bin/bash
              ${pythonEnv}/bin/python -m sdr_experiments.tools.verify_ptp "$@"
            '')
            (pkgs.writeScriptBin "sdr-waterfall" ''
              #!${pkgs.bash}/bin/bash
              ${pythonEnv}/bin/python -m sdr_experiments.tools.waterfall_tool "$@"
            '')
            (pkgs.writeScriptBin "sdr-measure-delay" ''
              #!${pkgs.bash}/bin/bash
              ${pythonEnv}/bin/python -m sdr_experiments.tools.measure_delay "$@"
            '')
            (pkgs.writeScriptBin "sdr-kitty-test" ''
              #!${pkgs.bash}/bin/bash
              ${pythonEnv}/bin/python -m kitty_graphics.test "$@"
            '')
            (pkgs.writeScriptBin "sdr-timed-capture" ''
              #!${pkgs.bash}/bin/bash
              ${pythonEnv}/bin/python -m sdr_experiments.tools.timed_capture "$@"
            '')
            (pkgs.writeScriptBin "sdr-ptp-sync" ''
              #!${pkgs.bash}/bin/bash
              set -e

              # These arguments require root privileges.
              NEEDS_ROOT=0
              for arg in "$@"; do
                if [[ "$arg" == "--start-master" || "$arg" == "--start-slave" || "$arg" == "--stop" || "$arg" == "--check" ]]; then
                  NEEDS_ROOT=1
                  break
                fi
              done
              
              # If we need root and don't have it, re-execute with sudo.
              if [[ "$NEEDS_ROOT" -eq 1 && "$EUID" -ne 0 ]]; then
                echo "This command requires root privileges. Re-running with sudo..."
                # Execute the script again with sudo, ensuring the PATH is preserved.
                # "$0" is the full path to this script in the Nix store.
                exec sudo -E --preserve-env=PATH "$0" "$@"
              fi
              
              # Execute the python script.
              # We must use an absolute path to the script in case sudo changes the CWD.
              # This assumes the command is run from the project root.
              PYTHON_SCRIPT_PATH="$PWD/src/sdr_experiments/tools/ptp_sync.py"

              if [ ! -f "$PYTHON_SCRIPT_PATH" ]; then
                  echo "Error: Python script not found at $PYTHON_SCRIPT_PATH" >&2
                  echo "Please ensure you are running this command from the root of the project directory." >&2
                  exit 1
              fi
              
              ${pythonEnv}/bin/python "$PYTHON_SCRIPT_PATH" "$@"
            '')
            (pkgs.writeScriptBin "llm-query" ''
              #!${pkgs.bash}/bin/bash
              ${pythonEnv}/bin/python -m llm_sidechannel.tools.query "$@"
            '')
            (pkgs.writeScriptBin "llm-analyze-moe" ''
              #!${pkgs.bash}/bin/bash
              ${pythonEnv}/bin/python -m llm_sidechannel.tools.analyze_moe "$@"
            '')
          ];

          env = {
            # UV configuration
            UV_PYTHON_DOWNLOADS = "never";
            UV_PYTHON = "${pythonEnv}/bin/python";
            
            # SDR library paths
            SOAPY_SDR_PLUGIN_PATH = "${pkgs.soapysdr-with-plugins}/lib/SoapySDR/modules0.8-3";
            
            # Terminal support
            TERM = "xterm-kitty";
          };

          shellHook = ''
            echo "🔬 SDR Development Environment (Simple) - Raspberry Pi"
            echo "Python: ${pythonEnv}/bin/python"
            echo ""
            echo "Testing packages:"
            echo "  - SoapySDR: $(python -c "import SoapySDR; print('✓')" 2>/dev/null || echo "✗")"
            echo "  - NumPy: $(python -c "import numpy; print('✓')" 2>/dev/null || echo "✗")"
            echo "  - Matplotlib: $(python -c "import matplotlib; print('✓')" 2>/dev/null || echo "✗")"
            echo ""
            echo "Available packages (src/):"
            echo "  - sdr_experiments (main SDR tools)"
            echo "  - kitty_graphics (terminal graphics)"
            echo "  - llm_sidechannel (LLM MoE analysis)"
            echo ""
            echo "Ready to run:"
            echo "  sdr-verify-ptp --help"
            echo "  sdr-waterfall --help"  
            echo "  sdr-measure-delay --help"
            echo "  sdr-kitty-test"
            echo "  sdr-timed-capture --help"
            echo "  sdr-ptp-sync --help"
            echo "  llm-query --help"
            echo "  llm-analyze-moe --help"
            echo ""
            
            # Unset PYTHONPATH to avoid conflicts
            unset PYTHONPATH
            export PYTHONPATH="$PWD/src:$PYTHONPATH"
          '';
        };

      aarch64-darwin.default = 
        let
          pkgs = import nixpkgs { 
            system = "aarch64-darwin"; 
            config.allowUnfree = true; 
          };
          
          # Create Python environment with SDR packages
          pythonEnv = pkgs.python312.withPackages (ps: with ps; [
            soapysdr
            numpy
            matplotlib
            scipy
            # LLM dependencies
            torch
            transformers
            tokenizers
            accelerate
            datasets
            bitsandbytes
          ]);
          
        in pkgs.mkShell {
          name = "sdr-dev-shell";
          
          packages = with pkgs; [
            pythonEnv
            uv
            # SDR tools
            soapysdr-with-plugins
            soapyremote
            rtl-sdr
            gqrx
            # Development tools
            git
            # Graphics support
            kitty

            # Create wrapper scripts for our tools
            (pkgs.writeScriptBin "sdr-verify-ptp" ''
              #!${pkgs.bash}/bin/bash
              ${pythonEnv}/bin/python -m sdr_experiments.tools.verify_ptp "$@"
            '')
            (pkgs.writeScriptBin "sdr-waterfall" ''
              #!${pkgs.bash}/bin/bash
              ${pythonEnv}/bin/python -m sdr_experiments.tools.waterfall_tool "$@"
            '')
            (pkgs.writeScriptBin "sdr-measure-delay" ''
              #!${pkgs.bash}/bin/bash
              ${pythonEnv}/bin/python -m sdr_experiments.tools.measure_delay "$@"
            '')
            (pkgs.writeScriptBin "sdr-kitty-test" ''
              #!${pkgs.bash}/bin/bash
              ${pythonEnv}/bin/python -m kitty_graphics.test "$@"
            '')
            (pkgs.writeScriptBin "sdr-timed-capture" ''
              #!${pkgs.bash}/bin/bash
              ${pythonEnv}/bin/python -m sdr_experiments.tools.timed_capture "$@"
            '')
            (pkgs.writeScriptBin "sdr-ptp-sync" ''
              #!${pkgs.bash}/bin/bash
              set -e

              # These arguments require root privileges.
              NEEDS_ROOT=0
              for arg in "$@"; do
                if [[ "$arg" == "--start-master" || "$arg" == "--start-slave" || "$arg" == "--stop" || "$arg" == "--check" ]]; then
                  NEEDS_ROOT=1
                  break
                fi
              done
              
              # If we need root and don't have it, re-execute with sudo.
              if [[ "$NEEDS_ROOT" -eq 1 && "$EUID" -ne 0 ]]; then
                echo "This command requires root privileges. Re-running with sudo..."
                # Execute the script again with sudo, ensuring the PATH is preserved.
                # "$0" is the full path to this script in the Nix store.
                exec sudo -E --preserve-env=PATH "$0" "$@"
              fi
              
              # Execute the python script.
              # We must use an absolute path to the script in case sudo changes the CWD.
              # This assumes the command is run from the project root.
              PYTHON_SCRIPT_PATH="$PWD/src/sdr_experiments/tools/ptp_sync.py"

              if [ ! -f "$PYTHON_SCRIPT_PATH" ]; then
                  echo "Error: Python script not found at $PYTHON_SCRIPT_PATH" >&2
                  echo "Please ensure you are running this command from the root of the project directory." >&2
                  exit 1
              fi
              
              ${pythonEnv}/bin/python "$PYTHON_SCRIPT_PATH" "$@"
            '')
            (pkgs.writeScriptBin "llm-query" ''
              #!${pkgs.bash}/bin/bash
              ${pythonEnv}/bin/python -m llm_sidechannel.tools.query "$@"
            '')
            (pkgs.writeScriptBin "llm-analyze-moe" ''
              #!${pkgs.bash}/bin/bash
              ${pythonEnv}/bin/python -m llm_sidechannel.tools.analyze_moe "$@"
            '')
          ];

          env = {
            # UV configuration
            UV_PYTHON_DOWNLOADS = "never";
            UV_PYTHON = "${pythonEnv}/bin/python";
            
            # SDR library paths
            SOAPY_SDR_PLUGIN_PATH = "${pkgs.soapysdr-with-plugins}/lib/SoapySDR/modules0.8-3";
            
            # Terminal support
            TERM = "xterm-kitty";
          };

          shellHook = ''
            echo "🔬 SDR Development Environment (Simple) - macOS (Apple Silicon)"
            echo "Python: ${pythonEnv}/bin/python"
            echo ""
            echo "Testing packages:"
            echo "  - SoapySDR: $(python -c "import SoapySDR; print('✓')" 2>/dev/null || echo "✗")"
            echo "  - NumPy: $(python -c "import numpy; print('✓')" 2>/dev/null || echo "✗")"
            echo "  - Matplotlib: $(python -c "import matplotlib; print('✓')" 2>/dev/null || echo "✗")"
            echo ""
            echo "Available packages (src/):"
            echo "  - sdr_experiments (main SDR tools)"
            echo "  - kitty_graphics (terminal graphics)"
            echo "  - llm_sidechannel (LLM MoE analysis)"
            echo ""
            echo "Available GUI tools:"
            echo "  - gqrx (SDR receiver)"
            echo ""
            echo "Ready to run:"
            echo "  sdr-verify-ptp --help"
            echo "  sdr-waterfall --help"  
            echo "  sdr-measure-delay --help"
            echo "  sdr-kitty-test"
            echo "  sdr-timed-capture --help"
            echo "  sdr-ptp-sync --help"
            echo "  llm-query --help"
            echo "  llm-analyze-moe --help"
            echo "  gqrx"
            echo ""
            
            # Unset PYTHONPATH to avoid conflicts
            unset PYTHONPATH
            export PYTHONPATH="$PWD/src:$PYTHONPATH"
          '';
        };

      x86_64-darwin.default = 
        let
          pkgs = import nixpkgs { 
            system = "x86_64-darwin"; 
            config.allowUnfree = true; 
          };
          
          # Create Python environment with SDR packages
          pythonEnv = pkgs.python312.withPackages (ps: with ps; [
            soapysdr
            numpy
            matplotlib
            scipy
            # LLM dependencies
            torch
            transformers
            tokenizers
            accelerate
            datasets
            bitsandbytes
          ]);
          
        in pkgs.mkShell {
          name = "sdr-dev-shell";
          
          packages = with pkgs; [
            pythonEnv
            uv
            # SDR tools
            soapysdr-with-plugins
            soapyremote
            rtl-sdr
            gqrx
            # Development tools
            git
            # Graphics support
            kitty

            # Create wrapper scripts for our tools
            (pkgs.writeScriptBin "sdr-verify-ptp" ''
              #!${pkgs.bash}/bin/bash
              ${pythonEnv}/bin/python -m sdr_experiments.tools.verify_ptp "$@"
            '')
            (pkgs.writeScriptBin "sdr-waterfall" ''
              #!${pkgs.bash}/bin/bash
              ${pythonEnv}/bin/python -m sdr_experiments.tools.waterfall_tool "$@"
            '')
            (pkgs.writeScriptBin "sdr-measure-delay" ''
              #!${pkgs.bash}/bin/bash
              ${pythonEnv}/bin/python -m sdr_experiments.tools.measure_delay "$@"
            '')
            (pkgs.writeScriptBin "sdr-kitty-test" ''
              #!${pkgs.bash}/bin/bash
              ${pythonEnv}/bin/python -m kitty_graphics.test "$@"
            '')
            (pkgs.writeScriptBin "sdr-timed-capture" ''
              #!${pkgs.bash}/bin/bash
              ${pythonEnv}/bin/python -m sdr_experiments.tools.timed_capture "$@"
            '')
            (pkgs.writeScriptBin "sdr-ptp-sync" ''
              #!${pkgs.bash}/bin/bash
              set -e

              # These arguments require root privileges.
              NEEDS_ROOT=0
              for arg in "$@"; do
                if [[ "$arg" == "--start-master" || "$arg" == "--start-slave" || "$arg" == "--stop" || "$arg" == "--check" ]]; then
                  NEEDS_ROOT=1
                  break
                fi
              done
              
              # If we need root and don't have it, re-execute with sudo.
              if [[ "$NEEDS_ROOT" -eq 1 && "$EUID" -ne 0 ]]; then
                echo "This command requires root privileges. Re-running with sudo..."
                # Execute the script again with sudo, ensuring the PATH is preserved.
                # "$0" is the full path to this script in the Nix store.
                exec sudo -E --preserve-env=PATH "$0" "$@"
              fi
              
              # Execute the python script.
              # We must use an absolute path to the script in case sudo changes the CWD.
              # This assumes the command is run from the project root.
              PYTHON_SCRIPT_PATH="$PWD/src/sdr_experiments/tools/ptp_sync.py"

              if [ ! -f "$PYTHON_SCRIPT_PATH" ]; then
                  echo "Error: Python script not found at $PYTHON_SCRIPT_PATH" >&2
                  echo "Please ensure you are running this command from the root of the project directory." >&2
                  exit 1
              fi
              
              ${pythonEnv}/bin/python "$PYTHON_SCRIPT_PATH" "$@"
            '')
            (pkgs.writeScriptBin "llm-query" ''
              #!${pkgs.bash}/bin/bash
              ${pythonEnv}/bin/python -m llm_sidechannel.tools.query "$@"
            '')
            (pkgs.writeScriptBin "llm-analyze-moe" ''
              #!${pkgs.bash}/bin/bash
              ${pythonEnv}/bin/python -m llm_sidechannel.tools.analyze_moe "$@"
            '')
          ];

          env = {
            # UV configuration
            UV_PYTHON_DOWNLOADS = "never";
            UV_PYTHON = "${pythonEnv}/bin/python";
            
            # SDR library paths
            SOAPY_SDR_PLUGIN_PATH = "${pkgs.soapysdr-with-plugins}/lib/SoapySDR/modules0.8-3";
            
            # Terminal support
            TERM = "xterm-kitty";
          };

          shellHook = ''
            echo "🔬 SDR Development Environment (Simple) - macOS (Intel)"
            echo "Python: ${pythonEnv}/bin/python"
            echo ""
            echo "Testing packages:"
            echo "  - SoapySDR: $(python -c "import SoapySDR; print('✓')" 2>/dev/null || echo "✗")"
            echo "  - NumPy: $(python -c "import numpy; print('✓')" 2>/dev/null || echo "✗")"
            echo "  - Matplotlib: $(python -c "import matplotlib; print('✓')" 2>/dev/null || echo "✗")"
            echo ""
            echo "Available packages (src/):"
            echo "  - sdr_experiments (main SDR tools)"
            echo "  - kitty_graphics (terminal graphics)"
            echo "  - llm_sidechannel (LLM MoE analysis)"
            echo ""
            echo "Available GUI tools:"
            echo "  - gqrx (SDR receiver)"
            echo ""
            echo "Ready to run:"
            echo "  sdr-verify-ptp --help"
            echo "  sdr-waterfall --help"  
            echo "  sdr-measure-delay --help"
            echo "  sdr-kitty-test"
            echo "  sdr-timed-capture --help"
            echo "  sdr-ptp-sync --help"
            echo "  llm-query --help"
            echo "  llm-analyze-moe --help"
            echo "  gqrx"
            echo ""
            
            # Unset PYTHONPATH to avoid conflicts
            unset PYTHONPATH
            export PYTHONPATH="$PWD/src:$PYTHONPATH"
          '';
        };
    };
  };
} 