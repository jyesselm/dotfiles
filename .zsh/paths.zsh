# ~/.zsh/paths.zsh
# PATH and environment variable configuration

# ============================================================
# Core Paths (highest priority)
# ============================================================
# Homebrew (macOS Apple Silicon)
if [[ -d "/opt/homebrew/bin" ]]; then
  export PATH="/opt/homebrew/bin:/opt/homebrew/sbin:$PATH"
fi

# Homebrew (macOS Intel or Linux)
if [[ -d "/usr/local/bin" ]] && [[ "$PATH" != *"/usr/local/bin"* ]]; then
  export PATH="/usr/local/bin:/usr/local/sbin:$PATH"
fi

# Local user binaries
export PATH="$HOME/.local/bin:$PATH"

# ============================================================
# Language Runtimes
# ============================================================
# Java (OpenJDK via Homebrew)
if [[ -d "/opt/homebrew/opt/openjdk/bin" ]]; then
  export PATH="/opt/homebrew/opt/openjdk/bin:$PATH"
  export JAVA_HOME="/opt/homebrew/opt/openjdk"
fi

# ============================================================
# Bioinformatics Tools (conditional - only if directories exist)
# ============================================================
# Bowtie2
[[ -d "$HOME/installs/bowtie2-2.4.5-macos-arm64" ]] && \
  export PATH="$PATH:$HOME/installs/bowtie2-2.4.5-macos-arm64"

# NovoAlign
[[ -d "$HOME/installs/novocraft" ]] && \
  export PATH="$PATH:$HOME/installs/novocraft"

# TrimGalore
[[ -d "$HOME/installs/TrimGalore-0.6.6" ]] && \
  export PATH="$PATH:$HOME/installs/TrimGalore-0.6.6"

# FastQC
[[ -d "$HOME/installs/FastQC" ]] && \
  export PATH="$PATH:$HOME/installs/FastQC"

# ============================================================
# Rosetta & RNA Tools
# ============================================================
if [[ -d "$HOME/projects/Rosetta" ]]; then
  export ROSETTA="$HOME/projects/Rosetta"
  [[ -d "$ROSETTA/tools/rna_tools/bin" ]] && \
    export PATH="$PATH:$ROSETTA/tools/rna_tools/bin"
  [[ -d "$ROSETTA/main/source/bin" ]] && \
    export PATH="$PATH:$ROSETTA/main/source/bin"
fi

# ============================================================
# SRA Toolkit
# ============================================================
# Find latest version dynamically
for sra_dir in "$HOME/Downloads"/sratoolkit.*-mac64/bin; do
  if [[ -d "$sra_dir" ]]; then
    export PATH="$PATH:$sra_dir"
    break
  fi
done

# ============================================================
# SHAPEMapper
# ============================================================
if [[ -d "$HOME/Downloads/shapemapper-2.1.5" ]]; then
  export PATH="$PATH:$HOME/Downloads/shapemapper-2.1.5"
  [[ -d "$HOME/Downloads/shapemapper-2.1.5/internals/bin" ]] && \
    export PATH="$PATH:$HOME/Downloads/shapemapper-2.1.5/internals/bin"
fi

# ============================================================
# Computational Chemistry Tools
# ============================================================
# ORCA
if [[ -d "$HOME/installs/orca_5_0_3_macosx_arm64_openmpi411" ]]; then
  export ORCA_PATH="$HOME/installs/orca_5_0_3_macosx_arm64_openmpi411"
  export PATH="$PATH:$ORCA_PATH"
fi

# X3DNA
if [[ -d "$HOME/installs/x3dna" ]]; then
  export X3DNA="$HOME/installs/x3dna"
  [[ -d "$X3DNA/bin" ]] && \
    export PATH="$PATH:$X3DNA/bin"
fi

# RNAMake
if [[ -d "$HOME/Dropbox/2_code/cpp/RNAMake" ]]; then
  export RNAMAKE="$HOME/Dropbox/2_code/cpp/RNAMake"
  [[ -d "$RNAMAKE/cmake/build_clang" ]] && \
    export PATH="$PATH:$RNAMAKE/cmake/build_clang"
fi

# RNAstructure
if [[ -d "$HOME/installs/RNAstructure" ]]; then
  [[ -d "$HOME/installs/RNAstructure/exe" ]] && \
    export PATH="$PATH:$HOME/installs/RNAstructure/exe"
  [[ -d "$HOME/installs/RNAstructure/data_tables" ]] && \
    export DATAPATH="$HOME/installs/RNAstructure/data_tables"
fi

# ============================================================
# Workflow Tools
# ============================================================
# Nextflow
[[ -d "$HOME/projects/nextflow" ]] && \
  export PATH="$PATH:$HOME/projects/nextflow"

# ============================================================
# TeX/LaTeX
# ============================================================
# TeX Live (check for latest version)
for tex_path in /usr/local/texlive/*/bin/universal-darwin; do
  if [[ -d "$tex_path" ]]; then
    export PATH="$PATH:$tex_path"
    break
  fi
done

# ============================================================
# Clean up PATH (remove duplicates)
# ============================================================
# Remove duplicate entries from PATH
export PATH=$(echo "$PATH" | awk -v RS=':' -v ORS=':' '!a[$1]++' | sed 's/:$//')
