# ~/.zsh/paths.zsh

# Homebrew & local bins
export PATH="/opt/homebrew/bin:$HOME/.local/bin:$PATH"

# Java (OpenJDK)
export PATH="/opt/homebrew/opt/openjdk/bin:$PATH"

# Bio / tools (use $HOME, not hard-coded $USER)
export PATH="$PATH:$HOME/installs/bowtie2-2.4.5-macos-arm64"
export PATH="$PATH:$HOME/installs/novocraft"
export PATH="$PATH:$HOME/installs/TrimGalore-0.6.6"
export PATH="$PATH:$HOME/installs/FastQC"

# Rosetta & RNA tools
export ROSETTA="$HOME/projects/Rosetta"
export PATH="$PATH:$ROSETTA/tools/rna_tools/bin"
export PATH="$PATH:$ROSETTA/main/source/bin"

# SRA toolkit
export PATH="$PATH:$HOME/Downloads/sratoolkit.2.11.2-mac64/bin"

# SHAPEMapper
export PATH="$PATH:$HOME/Downloads/shapemapper-2.1.5"
export PATH="$PATH:$HOME/Downloads/shapemapper-2.1.5/internals/bin"

# ORCA / X3DNA / RNAMake / RNAstructure
export ORCA_PATH="$HOME/installs/orca_5_0_3_macosx_arm64_openmpi411"
export X3DNA="$HOME/installs/x3dna"
export RNAMAKE="$HOME/Dropbox/2_code/cpp/RNAMake"
export DATAPATH="$HOME/installs/RNAstructure/data_tables"

export PATH="$PATH:$RNAMAKE/cmake/build_clang"
export PATH="$PATH:$HOME/installs/RNAstructure/exe"
export PATH="$PATH:$X3DNA/bin"

# Nextflow
export PATH="$PATH:$HOME/projects/nextflow"

# TeX (if still using this install)
export PATH="$PATH:/usr/local/texlive/2022basic/bin/universal-darwin"
