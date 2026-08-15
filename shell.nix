# Dev environment for building qemu-eos + Magic Lantern for the Canon 6D Mark II.
#
#   nix-shell            # from this directory
#
# Deliberately NOT in /etc/nixos: these deps are project-only, and a shell.nix
# is undone by deleting this file rather than by a system rebuild.
#
# inputsFrom = [ pkgs.qemu ] inherits every build dependency nixpkgs uses for
# QEMU itself (glib, pixman, gtk3, pkg-config, zlib, ...), which covers the
# configure line in qemu-eos/magiclantern/README.md:
#   ../qemu-eos/configure --target-list=arm-softmmu --enable-plugins \
#       --disable-docs --enable-vnc --enable-gtk --disable-vte

{ pkgs ? import <nixpkgs> { } }:

let
  # qemu-eos is forked from QEMU 4.2.1 (2019). GCC 14 turned several then-legal C
  # patterns into hard errors (implicit-function-declaration, int-conversion),
  # and this system's default is GCC 15.2 — old QEMU will not build with it.
  # GCC 13.4 is the oldest stdenv still in nixpkgs 26.05 (gcc11Stdenv/gcc12Stdenv
  # were removed as unmaintained), so that is the floor available without pinning
  # an older nixpkgs. If 13 still rejects the sources, the next move is pinning
  # nixpkgs via fetchTarball rather than patching QEMU.
  buildStdenv = pkgs.gcc13Stdenv;
in

pkgs.mkShell.override { stdenv = buildStdenv; } {
  inputsFrom = [ pkgs.qemu ];

  packages = [
    # arm-none-eabi-gcc — cross-compiles ML itself (platform/6D2.111)
    pkgs.gcc-arm-embedded

    # platform/Makefile's final packaging step shells out to `zip`
    pkgs.zip

    # `make disk_image` (platform/create_disk_image_from_zip.py) copies the
    # build into sd.qcow2 via guestmount/guestunmount. The -with-appliance
    # variant is required; bare libguestfs has no supermin appliance and
    # fails at runtime. Large closure, but it's the repo's supported path.
    pkgs.libguestfs-with-appliance

    (pkgs.python3.withPackages (ps: [
      # qemu-eos/magiclantern/ml_qemu/run.py imports PIL at module load time;
      # without it every run_qemu.py / run_tests.py invocation dies on import.
      ps.pillow
      # ml/tools/card-flags/edit_card_flags.py — only needed if the SD card's
      # EOS_DEVELOP/BOOTDISK flags ever have to be rewritten (in-camera format).
      ps.numpy
    ]))
  ];

  shellHook = ''
    echo "6D2 ML dev shell"
    echo "  arm-none-eabi-gcc : $(arm-none-eabi-gcc -dumpversion 2>/dev/null || echo MISSING)"
    echo "  cc (for qemu)     : $(cc -dumpversion 2>/dev/null || echo MISSING)"
    echo "  python PIL        : $(python3 -c 'import PIL; print(PIL.__version__)' 2>/dev/null || echo MISSING)"
    echo
    echo "Build qemu-eos:"
    echo "  mkdir -p qemu-eos-build && cd qemu-eos-build"
    echo "  ../qemu-eos/configure --target-list=arm-softmmu --enable-plugins \\"
    echo "      --disable-docs --enable-vnc --enable-gtk --disable-vte"
    echo "  make -j\$(nproc) && make plugins"
    echo "  cp tests/plugin/libmagiclantern.so arm-softmmu/plugins/"
  '';
}
