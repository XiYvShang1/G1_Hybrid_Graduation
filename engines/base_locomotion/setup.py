"""Installation script for the G1 23DoF training engine."""

from setuptools import setup, find_packages

# Minimum dependencies required prior to installation
INSTALL_REQUIRES = [
    "mjlab==1.2.0",
    "mujoco-warp==3.5.0",
]

# Installation operation
setup(
    name="g1_23dof_training_engine",
    packages=["src"],
    version="0.0.1",
    install_requires=INSTALL_REQUIRES,
)
