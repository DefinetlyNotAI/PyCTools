cmake_minimum_required(VERSION 4.0)
project(pyCTools C)

set(CMAKE_C_STANDARD 11)

add_library(PyCTools SHARED
        src/hRng.c
        src/processInspect.c)
# Unused really, but kept for reference
