# SDR-specific overlays for Python packages
# This file contains overrides for Python packages that need special handling
# for SDR applications, particularly those with C extensions.

final: prev: {
  # SoapySDR Python bindings with enhanced C library support
  soapysdr = prev.soapysdr.overrideAttrs (old: {
    buildInputs = (old.buildInputs or []) ++ (with final.pkgs; [
      soapysdr
      libusb1
      fftw
    ]);
    
    nativeBuildInputs = (old.nativeBuildInputs or []) ++ (with final.pkgs; [
      pkg-config
      cmake
      swig
    ]);
    
    # Ensure proper linking to system SoapySDR
    env = (old.env or {}) // {
      SOAPY_SDR_ROOT = final.pkgs.soapysdr;
    };
    
    # Custom build flags for better performance
    preBuild = (old.preBuild or "") + ''
      export CFLAGS="$CFLAGS -O3 -march=native"
      export CXXFLAGS="$CXXFLAGS -O3 -march=native"
    '';
  });

  # NumPy with optimized BLAS/LAPACK for SDR computations
  numpy = prev.numpy.overrideAttrs (old: {
    buildInputs = (old.buildInputs or []) ++ (with final.pkgs; [
      openblas
      lapack
    ]);
    
    # Configure NumPy to use OpenBLAS
    preConfigure = (old.preConfigure or "") + ''
      cat > site.cfg <<EOF
      [openblas]
      libraries = openblas
      library_dirs = ${final.pkgs.openblas}/lib
      include_dirs = ${final.pkgs.openblas}/include
      EOF
    '';
    
    env = (old.env or {}) // {
      NPY_NUM_BUILD_JOBS = toString (builtins.min 16 8);
      ATLAS = "None";
      BLAS = "${final.pkgs.openblas}/lib/libopenblas.so";
      LAPACK = "${final.pkgs.openblas}/lib/libopenblas.so";
    };
  });

  # SciPy with enhanced BLAS support
  scipy = prev.scipy.overrideAttrs (old: {
    buildInputs = (old.buildInputs or []) ++ (with final.pkgs; [
      openblas
      lapack
      fftw
    ]);
    
    env = (old.env or {}) // {
      BLAS = "${final.pkgs.openblas}/lib/libopenblas.so";
      LAPACK = "${final.pkgs.openblas}/lib/libopenblas.so";
    };
  });

  # Matplotlib with better backend support for SDR visualization
  matplotlib = prev.matplotlib.overrideAttrs (old: {
    buildInputs = (old.buildInputs or []) ++ (with final.pkgs; [
      freetype
      fontconfig
      libpng
      tk
      tcl
      qhull
      # X11 support for interactive plots
      xorg.libX11
      xorg.libXext
      xorg.libXrender
      xorg.libXt
    ]);
    
    nativeBuildInputs = (old.nativeBuildInputs or []) ++ (with final.pkgs; [
      pkg-config
    ]);
    
    # Enable more backends
    env = (old.env or {}) // {
      MPLBACKEND = "TkAgg";
    };
  });

  # Custom RTL-SDR Python bindings if needed
  pyrtlsdr = prev.pyrtlsdr.overrideAttrs (old: {
    buildInputs = (old.buildInputs or []) ++ (with final.pkgs; [
      rtl-sdr
      libusb1
    ]);
    
    nativeBuildInputs = (old.nativeBuildInputs or []) ++ (with final.pkgs; [
      pkg-config
    ]);
    
    preBuild = (old.preBuild or "") + ''
      export RTLSDR_LIBPATH=${final.pkgs.rtl-sdr}/lib
      export RTLSDR_INCPATH=${final.pkgs.rtl-sdr}/include
    '';
  });

  # GNU Radio Python bindings (if available)
  gnuradio = prev.gnuradio or (final.callPackage ({
    buildPythonPackage,
    fetchPyPI,
    numpy,
    scipy,
    ...
  }: buildPythonPackage rec {
    pname = "gnuradio";
    version = "3.10.0";
    
    src = fetchPyPI {
      inherit pname version;
      sha256 = ""; # Add appropriate hash
    };
    
    buildInputs = with final.pkgs; [
      gnuradio
      boost
      fftw
      gsl
    ];
    
    propagatedBuildInputs = [
      numpy
      scipy
    ];
    
    # Skip if gnuradio package doesn't exist in nixpkgs
    meta.broken = !final.pkgs ? gnuradio;
  }) {});

  # UHD Python bindings for USRP support
  pyuhd = prev.pyuhd or (final.callPackage ({
    buildPythonPackage,
    fetchPyPI,
    numpy,
    ...
  }: buildPythonPackage rec {
    pname = "pyuhd";
    version = "4.4.0.0";
    
    src = fetchPyPI {
      inherit pname version;
      sha256 = ""; # Add appropriate hash
    };
    
    buildInputs = with final.pkgs; [
      uhd
      boost
    ];
    
    nativeBuildInputs = with final.pkgs; [
      cmake
      pkg-config
    ];
    
    propagatedBuildInputs = [
      numpy
    ];
    
    # Skip if uhd package doesn't exist in nixpkgs
    meta.broken = !final.pkgs ? uhd;
  }) {});

  # Custom DSP packages can be added here
  # Example:
  # my-dsp-package = final.callPackage ../packages/my-dsp-package.nix {};
} 