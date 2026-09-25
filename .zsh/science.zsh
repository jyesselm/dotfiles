# Scientific tools. Override any root variable in ~/.zsh/local.zsh.
# Example: export BOWTIE2_ROOT="$HOME/local/installs/bowtie2"
# Roots provide fallback paths; activate Conda or edit PATH to select a command.
# check-tools reports discovery; check-tools --scan [directory] searches more broadly.
export SEQPATH="${SEQPATH:-$HOME/cloud/gdrive/sequences_and_oligos}"
export BASESPACE="${BASESPACE:-$HOME/BaseSpace}"
typeset -gA _science_found _science_source _science_auto

# Validate installations without executing their binaries.
_science_valid() {
  local key=$1 root=$2
  case $key in
    RNAMAKE) [[ -d $root/resources && -d $root/cmake && ( -d $root/src || -f $root/CMakeLists.txt ) ]] ;;
    ROSETTA) [[ -d $root/main/source && -d $root/tools ]] ;;
    RNASTRUCTURE) [[ -d $root/data_tables && ( -d $root/exe || -d $root/RNA_class ) ]] ;;
    VARNA_JAR) [[ -f $root && $root == *.jar ]] ;;
    *) [[ -x $root/$_science_command || -x $root/bin/$_science_command ]] ;;
  esac
}

# Fast discovery: explicit setting, PATH, then a small list of known locations.
_science_detect() {
  local key=$1 _science_command=$2 pattern=$3 bins=$4
  local candidate chosen='' origin='' explicit=${(P)key} executable base directory
  local -a candidates roots
  roots=("$HOME/projects" "$HOME/local/installs" "$HOME/installs" "$HOME/Dropbox/2_code/cpp" "$HOME/Downloads")
  # Values exported by our last run are discoveries, not user overrides.
  [[ $explicit == ${_science_auto[$key]-} ]] && explicit=''
  if [[ -n $explicit ]]; then
    chosen=$explicit
    origin=override
    if ! _science_valid "$key" "$chosen"; then
      _science_found[$key]=$chosen
      _science_source[$key]='invalid override'
      return
    fi
  else
    if [[ $_science_command != - ]]; then
      executable=$(whence -p "$_science_command" 2>/dev/null)
      if [[ -n $executable ]]; then
        executable=${executable:A}
        for candidate in "${executable:h}" "${executable:h:h}" "${executable:h:h:h}"; do
          if _science_valid "$key" "$candidate"; then chosen=$candidate; origin=PATH; break; fi
        done
      fi
    fi
    if [[ -z $chosen ]]; then
      for base in "${roots[@]}"; do
        candidates+=("$base"/${~pattern}(N/))
      done
      for candidate in "${candidates[@]}"; do
        [[ $key == VARNA_JAR ]] && candidate+='/VARNA.jar'
        if _science_valid "$key" "$candidate"; then chosen=$candidate; origin=known; break; fi
      done
    fi
  fi
  _science_found[$key]=$chosen
  _science_source[$key]=${origin:-missing}
  [[ -n $chosen ]] || return 0
  export "$key=$chosen"
  [[ $origin != override ]] && _science_auto[$key]=$chosen
  # Never change command precedence for a tool already supplied by PATH.
  [[ $origin == PATH ]] && return 0
  for directory in ${(s:,:)bins}; do
    [[ $directory == - ]] && continue
    [[ -d $chosen/$directory ]] && path+=("${${:-$chosen/$directory}:a}")
  done
}

_science_discover() {
  typeset -gU path
  # RNAMake discovery is intentionally deferred.
  _science_detect ROSETTA rna_denovo Rosetta 'tools/rna_tools/bin,main/source/bin'
  _science_detect RNASTRUCTURE Fold RNAstructure 'exe'
  _science_detect VARNA_JAR - VARNA '-'
  _science_detect X3DNA find_pair x3dna 'bin'
  _science_detect ORCA_PATH orca 'orca*' '.,bin'
  _science_detect BOWTIE2_ROOT bowtie2 'bowtie2*' '.,bin'
  _science_detect NOVOALIGN_ROOT novoalign novocraft '.,bin'
  _science_detect TRIMGALORE_ROOT trim_galore 'TrimGalore*' '.,bin'
  _science_detect FASTQC_ROOT fastqc 'FastQC*' '.,bin'
  _science_detect SRA_ROOT fasterq-dump 'sratoolkit*' 'bin'
  _science_detect SHAPEMAPPER_ROOT shapemapper 'shapemapper*' '.,internals/bin'
  _science_detect NEXTFLOW_ROOT nextflow nextflow '.,bin'
  # RNAstructure data must match the active installation, not an unrelated checkout.
  local fold_binary=$(whence -p Fold 2>/dev/null)
  local rna_root=${_science_found[RNASTRUCTURE]}
  if [[ -n $rna_root && ${_science_source[RNASTRUCTURE]} != 'invalid override' && ${fold_binary:A} == ${rna_root:A}/* ]]; then
    if [[ -z $DATAPATH || $DATAPATH == ${_science_auto[DATAPATH]-} ]]; then
      export DATAPATH="$rna_root/data_tables"
      _science_auto[DATAPATH]=$DATAPATH
    fi
  elif [[ -n ${_science_auto[DATAPATH]-} && $DATAPATH == ${_science_auto[DATAPATH]} ]]; then
    unset DATAPATH
    _science_auto[DATAPATH]=''
  fi
}

check-tools() {
  if [[ $# -gt 0 && $1 != --scan ]] || [[ $# -gt 2 ]]; then
    print 'Usage: check-tools [--scan [directory]]'
    return 2
  fi
  _science_discover
  local key location
  printf '%-18s %-18s %s\n' TOOL SOURCE LOCATION
  for key in ROSETTA RNASTRUCTURE VARNA_JAR X3DNA ORCA_PATH BOWTIE2_ROOT NOVOALIGN_ROOT TRIMGALORE_ROOT FASTQC_ROOT SRA_ROOT SHAPEMAPPER_ROOT NEXTFLOW_ROOT; do
    location=${_science_found[$key]:-—}
    [[ $location == "$HOME"/* ]] && location="~/${location#$HOME/}"
    printf '%-18s %-18s %s\n' "$key" "${_science_source[$key]}" "$location"
  done
  print '\nActive commands (existing PATH order is preserved):'
  local tool executable resolved provider alternative
  local -a matches seen
  for tool in bowtie2 trim_galore novoalign fastqc fasterq-dump shapemapper nextflow orca Fold find_pair; do
    matches=("${(@f)$(whence -pa "$tool" 2>/dev/null)}")
    matches=("${(@)matches:#}")
    if (( ! ${#matches} )); then
      printf '  %-16s %s\n' "$tool" 'missing'
      continue
    fi
    executable=$matches[1]
    resolved=${executable:A}
    provider=other
    if [[ -n $CONDA_PREFIX && ( $executable == "$CONDA_PREFIX"/* || $resolved == "$CONDA_PREFIX"/* ) ]]; then
      provider="Conda (${CONDA_PREFIX:t})"
    elif [[ $resolved == /opt/homebrew/* || $resolved == /usr/local/Cellar/* || $resolved == /home/linuxbrew/.linuxbrew/* ]]; then
      provider=Homebrew
    fi
    printf '  %-16s %s [%s]\n' "$tool" "$executable" "$provider"
    seen=("$resolved")
    for alternative in "${matches[@]:1}"; do
      resolved=${alternative:A}
      (( ${seen[(Ie)$resolved]} )) && continue
      seen+=("$resolved")
      printf '    also on PATH: %s\n' "$alternative"
    done
    if (( $+aliases[$tool] || $+functions[$tool] )); then
      printf '    shell alias/function overrides executable lookup: %s\n' "$tool"
    fi
  done
  print '\nRoot settings locate files; they do not override an existing PATH command.'
  print 'Found roots may contain source code rather than built binaries.'
  if [[ $1 == --scan ]]; then
    local scan_root=${2:-$HOME}
    [[ -d $scan_root ]] || { print -u2 "No such directory: $scan_root"; return 2; }
    print '\nPossible installations (not selected automatically):'
    command find "${scan_root:A}" \( -type d \( -name .git -o -name Library -o -name node_modules -o -name .cache \) -prune \) -o \( -type d \( -iname '*rnamake*' -o -iname 'Rosetta*' -o -iname 'RNAstructure*' -o -iname 'VARNA*' -o -iname 'x3dna*' -o -iname 'orca*' -o -iname 'bowtie2*' -o -iname 'novocraft*' -o -iname 'TrimGalore*' -o -iname 'FastQC*' -o -iname 'sratoolkit*' -o -iname 'shapemapper*' -o -iname 'nextflow*' \) -print -prune \) 2>/dev/null
  fi
  return 0
}

_science_discover
if command -v rnafold &>/dev/null; then
  alias rnafoldp='rnafold -p --noLP -d2'
fi

# Open VARNA using the discovered JAR or a VARNA_JAR override.
varna() {
  if [[ ! -f $VARNA_JAR ]]; then
    print -u2 'VARNA not found. Run check-tools or set VARNA_JAR in ~/.zsh/local.zsh.'
    return 1
  fi
  java -jar "$VARNA_JAR" >/dev/null 2>&1 &!
}

# Upload sequences & oligos to Swan
upload_seqs_and_oligos() {
  if [[ -z "$SEQPATH" ]]; then
    echo "Error: SEQPATH not set"
    return 1
  fi

  local current_dir=$PWD
  local parent_dir=$(dirname "$SEQPATH")
  local dir_name=$(basename "$SEQPATH")
  local archive_name="${dir_name}.tar.gz"

  if ! cd "$parent_dir" 2>/dev/null; then
    echo "Error: Cannot access $parent_dir"
    return 1
  fi

  echo "Creating tar.gz archive..."
  rm -f "$archive_name"
  if ! tar -czf "$archive_name" "$dir_name"; then
    echo "Error: Failed to create tar.gz archive"
    cd "$current_dir" || true
    return 1
  fi

  echo "Uploading to swan.unl.edu..."
  if scp "$archive_name" jyesselm@swan.unl.edu:/work/yesselmanlab/jyesselm/ && \
     ssh jyesselm@swan.unl.edu "cd /work/yesselmanlab/jyesselm/ && tar -xzf $archive_name && rm $archive_name"; then
    echo "✓ Upload successful"
    rm -f "$archive_name"
  else
    echo "✗ Upload failed"
  fi

  cd "$current_dir" || return 1
}
