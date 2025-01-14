#!/bin/bash

#fastapi run main.py --port 8080
uvicorn main:app --host 0.0.0.0 --port 8080