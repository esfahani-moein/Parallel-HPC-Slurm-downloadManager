#!/bin/bash
#SBATCH -N 1
#SBATCH -n 1
#SBATCH -c 10
#SBATCH -p qcluster
#SBATCH -J downloadJob1
#SBATCH -o /data/Parallel-HPC-Slurm-downloadManager/out_download_info_ver5_%x_%a_4.out
#SBATCH -A cluster_name
#SBATCH -t 5-00:00:00
#SBATCH --mem=100g
#SBATCH --oversubscribe

export MODULEPAT=/apps/Compilers/modules-3.2.10/Debug-Build/Modules/3.2.10/modulefiles
NODE=$(hostname)


echo "Job started on $(date)"
echo "Running on node: $NODE"

# Force Python to use unbuffered output
export PYTHONUNBUFFERED=1


source activate mydev1

echo "--- Checking Python version ---"
which python
python --version
echo "-----------------------------"

python Parallel-HPC-Slurm-downloadManager/hpc_downloader.py

echo "Job finished on $(date)"