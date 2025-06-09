# Example custom SDR package
# This demonstrates how to package a custom C/C++ SDR library
# that can be used with Python bindings in the development environment

{ lib
, stdenv
, fetchFromGitHub
, cmake
, pkg-config
, python3
, soapysdr
, fftw
, numpy
}:

stdenv.mkDerivation rec {
  pname = "example-sdr-package";
  version = "1.0.0";

  # Example source (replace with actual source)
  src = fetchFromGitHub {
    owner = "example-org";
    repo = "example-sdr-lib";
    rev = "v${version}";
    sha256 = "0000000000000000000000000000000000000000000000000000";
  };

  nativeBuildInputs = [
    cmake
    pkg-config
    python3.pkgs.setuptools
    python3.pkgs.pybind11
  ];

  buildInputs = [
    soapysdr
    fftw
    python3
    python3.pkgs.numpy
  ];

  cmakeFlags = [
    "-DCMAKE_BUILD_TYPE=Release"
    "-DENABLE_PYTHON=ON"
    "-DPYTHON_EXECUTABLE=${python3.interpreter}"
    "-DENABLE_OPTIMIZATION=ON"
  ];

  # Build both C++ library and Python bindings
  configurePhase = ''
    runHook preConfigure
    
    # Configure C++ library
    cmake -B build-cpp -S . \
      $cmakeFlags \
      -DCMAKE_INSTALL_PREFIX=$out
    
    # Configure Python bindings
    mkdir -p build-python
    cd build-python
    ${python3.interpreter} ../python/setup.py configure \
      --include-dirs=${fftw.dev}/include:${soapysdr}/include \
      --library-dirs=${fftw}/lib:${soapysdr}/lib
    
    runHook postConfigure
  '';

  buildPhase = ''
    runHook preBuild
    
    # Build C++ library
    cmake --build build-cpp --parallel $NIX_BUILD_CORES
    
    # Build Python bindings
    cd build-python
    ${python3.interpreter} ../python/setup.py build_ext --inplace
    
    runHook postBuild
  '';

  installPhase = ''
    runHook preInstall
    
    # Install C++ library
    cmake --install build-cpp
    
    # Install Python package
    cd build-python
    ${python3.interpreter} ../python/setup.py install --prefix=$out
    
    runHook postInstall
  '';

  # Ensure proper linking
  postFixup = lib.optionalString stdenv.isLinux ''
    # Fix RPATH for the Python extension
    find $out -name "*.so" -exec patchelf --set-rpath "${lib.makeLibraryPath buildInputs}:$out/lib" {} \;
  '';

  meta = with lib; {
    description = "Example SDR library with Python bindings";
    longDescription = ''
      An example software-defined radio library demonstrating how to
      package C++ libraries with Python bindings for use in the
      Nix SDR development environment.
    '';
    homepage = "https://github.com/example-org/example-sdr-lib";
    license = licenses.mit;
    maintainers = with maintainers; [ /* your-github-username */ ];
    platforms = platforms.linux ++ platforms.darwin;
    
    # Mark as broken until we have real source
    broken = true;
  };
}

# Usage in flake.nix:
# 1. Add to buildInputs in systemDeps
# 2. Add Python bindings to Python package overrides:
#
# my-sdr-package = final.callPackage ./nix/packages/example-sdr-package.nix {
#   python3 = python;
# }; 