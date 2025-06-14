{
  description = "SDR Python Development Environment (Simple)";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs = { self, nixpkgs, ... }: {
    devShells = {
      x86_64-linux.default = 
        let
          pkgs = nixpkgs.legacyPackages.x86_64-linux;
          
          # Create Python environment with SDR packages
          pythonEnv = pkgs.python312.withPackages (ps: with ps; [
            soapysdr
            numpy
            matplotlib
            scipy
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
            (pkgs.writeScriptBin "sdr-ptp-sync" ''
              #!${pkgs.bash}/bin/bash
              ${pythonEnv}/bin/python -m sdr_experiments.tools.ptp_sync "$@"
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
            echo ""
            echo "Ready to run:"
            echo "  sdr-verify-ptp --help"
            echo "  sdr-waterfall --help"  
            echo "  sdr-measure-delay --help"
            echo "  sdr-kitty-test"
            echo "  sdr-ptp-sync --help"
            echo ""
            
            # Unset PYTHONPATH to avoid conflicts
            unset PYTHONPATH
            export PYTHONPATH="$PWD/src:$PYTHONPATH"
          '';
        };

      aarch64-linux.default = 
        let
          pkgs = nixpkgs.legacyPackages.aarch64-linux;
          
          # Create Python environment with SDR packages
          pythonEnv = pkgs.python312.withPackages (ps: with ps; [
            soapysdr
            numpy
            matplotlib
            scipy
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
            (pkgs.writeScriptBin "sdr-ptp-sync" ''
              #!${pkgs.bash}/bin/bash
              ${pythonEnv}/bin/python -m sdr_experiments.tools.ptp_sync "$@"
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
            echo ""
            echo "Ready to run:"
            echo "  sdr-verify-ptp --help"
            echo "  sdr-waterfall --help"  
            echo "  sdr-measure-delay --help"
            echo "  sdr-kitty-test"
            echo "  sdr-ptp-sync --help"
            echo ""
            
            # Unset PYTHONPATH to avoid conflicts
            unset PYTHONPATH
            export PYTHONPATH="$PWD/src:$PYTHONPATH"
          '';
        };
    };
  };
} 