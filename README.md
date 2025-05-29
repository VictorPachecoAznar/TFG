# TFG
This repository hosts the code for my Bachelors' thesis in Geoinfomation and Geomatics Engineering.
The project has been tutored by Port de Barcelona and Universitat Politècnica de Catalunya.

# About this package
The goal of APB_spatial_computer_vision is to provide a framework to perform computer vision tasks on geospatial imagery.
Its focus is semantic segmentation, mainly though SAM. The logic can be accessed in several points: 
-Through text, to perform image to bbox tasks via Grounding DINO.
-Through bounding box, to perform SAM and achieve segmentation.
-Throgh a lower resolution vector dataset coming from another model, in an attempt to improve segmentation.

# Instructions
The entry points of the system are the following environment variables:
TEXT_PROMPT: a string with the prompt to look for via Grounding DINO
VECTOR_DATASET: a vector dataset
DATA_DIR: location of the data
BASE_DIR: where this package is located, acessible for deployments
NAME_ORTOFOTO: basename for the image to be processed
