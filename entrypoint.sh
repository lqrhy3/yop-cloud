#!/bin/bash

#fastapi run main.py --port 80
uvicorn main:app --host 0.0.0.0 --port 80