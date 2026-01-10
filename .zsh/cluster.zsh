# ~/.zsh/cluster.zsh
# HPC cluster-specific configuration (swan)

# ============================================================
# Module System Initialization
# ============================================================
# Source module init if not already available
if ! command -v module &>/dev/null; then
  [[ -f /etc/profile.d/modules.sh ]] && source /etc/profile.d/modules.sh
  [[ -f /util/opt/lmod/lmod/init/zsh ]] && source /util/opt/lmod/lmod/init/zsh
fi

# ============================================================
# Module Loads
# ============================================================
if command -v module &>/dev/null; then
  module load git 2>/dev/null
  module load anaconda 2>/dev/null
  module load nvim 2>/dev/null
  module load "starship/1.20" 2>/dev/null
fi

# ============================================================
# Cluster-specific PATH
# ============================================================
export PATH="$HOME/.local/bin:$PATH"
export PATH="/util/src/OLD-CRANE/git/git-2.7.4:$PATH"
export PATH="$PATH:/work/yesselmanlab/jyesselm/Rosetta/main/source/build/src/release/linux/4.18/64/x86/gcc/11.2/default/"
export PATH="$PATH:/work/yesselmanlab/jyesselm/installs/TrimGalore-0.6.6"
export PATH="$PATH:/work/yesselmanlab/jyesselm/installs/bowtie2-2.2.9"
export PATH="$PATH:/work/yesselmanlab/jyesselm/installs/novocraft"
export PATH="$PATH:/work/yesselmanlab/jyesselm/installs/bs"
export PATH="$PATH:/work/yesselmanlab/jyesselm/projects/nextflow"
export PATH="$PATH:/work/yesselmanlab/jyesselm/installs"

# ============================================================
# Environment Variables
# ============================================================
export NRDSTORSHARED=/mnt/nrdstor/yesselmanlab/shared/sequencing_data
export SEQPATH=/work/yesselmanlab/jyesselm/sequences_and_oligos
export RNAMAKE=/work/yesselmanlab/jyesselm/RNAMake/
export X3DNA=/work/yesselmanlab/jyesselm/installs/x3dna/x3dna-v2.4

# ============================================================
# Conda (Cluster installation)
# ============================================================
__conda_setup="$('/util/opt/anaconda/4.12.0/bin/conda' 'shell.zsh' 'hook' 2> /dev/null)"
if [ $? -eq 0 ]; then
    eval "$__conda_setup"
else
    if [ -f "/util/opt/anaconda/4.12.0/etc/profile.d/conda.sh" ]; then
        . "/util/opt/anaconda/4.12.0/etc/profile.d/conda.sh"
    else
        export PATH="/util/opt/anaconda/4.12.0/bin:$PATH"
    fi
fi
unset __conda_setup

# ============================================================
# SLURM Utilities
# ============================================================
cancel_slurm_jobs() {
    if [ $# -ne 2 ]; then
        echo "Usage: cancel_slurm_jobs <start_job_id> <end_job_id>"
        return 1
    fi

    start_job_id=$1
    end_job_id=$2

    if [[ ! "$start_job_id" =~ ^[0-9]+$ ]] || [[ ! "$end_job_id" =~ ^[0-9]+$ ]]; then
        echo "Both start and end job IDs must be numbers."
        return 1
    fi

    if [ $start_job_id -gt $end_job_id ]; then
        echo "Start job ID must be less than or equal to end job ID."
        return 1
    fi

    for job_id in $(seq $start_job_id $end_job_id); do
        scancel $job_id
        if [ $? -eq 0 ]; then
            echo "Cancelled job $job_id"
        else
            echo "Failed to cancel job $job_id"
        fi
    done
}

alias cancel_jobs="cancel_slurm_jobs"
alias showq='squeue -o "%.18i %.9P %.8j %.8u %.8T %.10M %.9l %.6D %R"'
