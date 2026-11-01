<a href="https://cthecosmos.com">
  <img src="assets/cosmos.svg" alt="Animated solar system: each planet is one of my repositories" width="100%">
</a>

### Embedded software engineer building onboard diagnostics for autonomous trucks.

Currently at **Torc Robotics**, working on the layer between a modern service-oriented diagnostic API and the ECUs underneath it:

- **SOVD -> UDS translation** - mapping ASAM SOVD (REST-based diagnostics, Eclipse OpenSOVD) onto ISO 14229 UDS services
- **DoIP stacks** - ISO 13400 diagnostics over IP, routing activation, entity/gateway behavior
- **Diagnostic configuration** - CDD-driven DID/DTC/routine definitions

Before that: safety-critical railway software at Cyient (EN 50128, 100% MC/DC with VectorCAST), and automotive tooling at Vector India.

```text
lang      C, C++, Python, CUDA, Assembly
auto      UDS, DoIP, SOVD, AUTOSAR Classic/Adaptive, CAN / CAN-FD
os        Linux (kernel + userspace), QNX, ROS2
hw        Nvidia Orin AGX, Jetson Orin Nano, Infineon Aurix TC375, RISC-V (QEMU)
quality   ISO 26262, MISRA C, VectorCAST, GDB
```

### Things I've built

| Project | What it is |
|---|---|
| [C-Programming-Questions](https://github.com/T-Yashwanth-Naidu/C-Programming-Questions) | Topic-wise C problem set used by 100+ people learning embedded C |
| [Socket_Manager](https://github.com/T-Yashwanth-Naidu/Socket_Manager) | Socket management in C |
| [LinkedIn-Highlighter](https://github.com/T-Yashwanth-Naidu/LinkedIn-Highlighter) | Chrome extension that highlights keywords in job posts |
| GPU KNN | CUDA-parallel K-nearest neighbors, benchmarked against a single-threaded CPU baseline |
| AEB system | Radar + LiDAR + camera fusion for emergency braking (MATLAB/Simulink) |

### Writing and research

- **CAN Bus Attack Vectors** - IEEE Wavelength, 2024
- **Automated Data Acquisition for Photogrammetry** - IEEE ICRA
- **LiDAR 3D Point Cloud Performance Analysis** - IEEE, 2024
- **Semi-Automated Workflow for 3D Model Reconstruction** - MS thesis, Oakland University

More at [cthecosmos.com](https://cthecosmos.com) | [LinkedIn](https://www.linkedin.com/in/t-yashwanth-naidu/)

<sub>The header regenerates daily via GitHub Actions: planets are repos (size = stars, inner orbit = most recently pushed), background stars are days I committed. Source in <code>scripts/generate_cosmos.py</code>.</sub>
