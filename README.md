# Coffee ring SDL
[![badge](https://img.shields.io/badge/ChemRxiv-10.26434/chemrxiv.15000670/v1-blue)](https://doi.org/10.26434/chemrxiv.15000670/v1)

This repository contains the code for [Bridging decision-making engines and workflow design in
self-driving laboratories: A NIMO–IvoryOS integration study](https://doi.org/10.26434/chemrxiv.15000670/v1).

https://github.com/user-attachments/assets/59473e3e-9ef5-4655-9085-d7f3969cc532

## Prerequisites
- [NIMO](https://github.com/NIMS-DA/nimo) (tested with v2.1.2)
- [IvoryOS](https://gitlab.com/heingroup/ivoryos) (tested with v1.5.16)
- [PyLabRobot](https://github.com/PyLabRobot/pylabrobot)
- [FastSAM](https://github.com/CASIA-LMC-Lab/FastSAM)
- [PyVISA](https://github.com/pyvisa/pyvisa)
- [xArm-Python-SDK](https://github.com/xArm-Developer/xArm-Python-SDK)

## Usage
1. Run the following command to start the IvoryOS interface.
```
python main.py
```

2. Open a web browser and access `http://127.0.0.1:8888/`.

## Citation

If you find this repository useful, please consider citing it as follows.
```
@article{yoshikawa2026bridging,
  author = {Naruki Yoshikawa and Taiga Ozawa and Wenyu Zhang and Jason E Hein and Ryo Tamura and Shoichi Matsuda},
  title = {Bridging decision-making engines and workflow design in self-driving laboratories: A NIMO–IvoryOS integration study},
  journal = {ChemRxiv},
  year = {2026},
  doi = {10.26434/chemrxiv.15000670/v1},
}
```